import asyncio
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import sys
import traceback
from functools import wraps
import logging

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path for imports
# In Docker, src is copied to /app/src, and app.py is at /app/app.py
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from Notes2Notion.notes_builder import NotesCreator, DraftEnhancer
from Notes2Notion.tooling import ImageTextExtractor, McpNotionConnector
from Notes2Notion.mock_components import (MockImageTextExtractor, MockDraftEnhancer,
                                          MockNotesCreator)

# Import OAuth and database modules
from oauth import require_oauth, handle_oauth_callback
from models import run_migrations, update_user_notion_page, validate_license_key

# Configure logging
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

# Initialize database and run migrations
run_migrations()

# Configuration
UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Notes2Notion Backend',
        'version': '2.0.0-pwa-oauth'
    })


@app.route('/api/license/validate', methods=['POST'])
def validate_license():
    """
    Validate a license key without activating it.

    This endpoint checks if a license key is valid and available for use.

    Expects JSON body with:
    - license_key: License key to validate

    Returns:
    - valid: Boolean (true only if key is valid AND available)
    - message: User-friendly message in French
    """
    try:
        data = request.get_json()
        license_key = data.get('license_key')

        if not license_key:
            return jsonify({'valid': False, 'message': 'Clé de licence requise'}), 400

        result = validate_license_key(license_key)

        # Accept both unused keys and keys that are already in use
        # The OAuth callback will verify if the user owns this key
        if result['valid']:
            message = 'Clé de licence valide' if not result['is_used'] else 'Reconnexion avec votre clé'
            return jsonify({
                'valid': True,
                'message': message,
                'is_used': result['is_used']
            }), 200
        else:
            return jsonify({'valid': False, 'message': result['message']}), 200

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"\n❌ License validation error:")
        logger.error(error_trace)
        return jsonify({'valid': False, 'message': 'Erreur de validation'}), 500


@app.route('/api/oauth/callback', methods=['POST'])
def oauth_callback():
    """
    Handle Notion OAuth callback.

    Expects JSON body with:
    - code: Authorization code from Notion
    - license_key: (Optional) License key to activate for the user

    Returns:
    - session_token: JWT token for subsequent requests
    - workspace_name: User's Notion workspace
    - needs_page_setup: Whether user needs to configure default page
    """
    try:
        data = request.get_json()
        code = data.get('code')
        license_key = data.get('license_key')  # NEW: Get license key from request

        if not code:
            return jsonify({'error': 'Missing authorization code'}), 400

        # Handle OAuth flow: exchange code for token, store user, create session
        # Pass license_key to activate it for the new/existing user
        result = handle_oauth_callback(code, license_key)

        return jsonify(result), 200

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"\n❌ OAuth callback error:")
        logger.error(error_trace)
        return jsonify({
            'error': 'OAuth authentication failed',
            'message': str(e)
        }), 500


@app.route('/api/user/page-id', methods=['POST'])
@require_oauth
def set_page_id(current_user):
    """
    Set the default Notion page ID for the authenticated user.

    This is where the user's handwritten notes will be created.

    Expects JSON body with:
    - page_id: Notion page ID

    Returns:
    - success: Boolean indicating if update succeeded
    """
    try:
        data = request.get_json()
        page_id = data.get('page_id')

        if not page_id:
            return jsonify({'error': 'Missing page_id'}), 400

        # Update user's default page ID
        update_user_notion_page(current_user.bot_id, page_id)

        return jsonify({
            'success': True,
            'message': 'Default page ID updated successfully'
        }), 200

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"❌ Error updating page ID for {current_user.bot_id}:")
        logger.error(error_trace)
        return jsonify({
            'error': 'Failed to update page ID',
            'message': str(e)
        }), 500


@app.route('/api/user/info', methods=['GET'])
@require_oauth
def get_user_info(current_user):
    """
    Get information about the authenticated user.

    Returns:
    - workspace_name: User's Notion workspace
    - has_page_id: Whether user has configured a default page
    - bot_id: User identifier
    """
    # Force a fresh query to avoid detached session issues
    from models import get_session, User
    session = get_session()
    try:
        fresh_user = session.query(User).filter_by(bot_id=current_user.bot_id).first()
        if fresh_user:
            result = {
                'workspace_name': fresh_user.workspace_name,
                'has_page_id': fresh_user.notion_page_id is not None,
                'bot_id': fresh_user.bot_id
            }
        else:
            # Fallback to current_user if fresh query fails
            result = {
                'workspace_name': current_user.workspace_name,
                'has_page_id': current_user.notion_page_id is not None,
                'bot_id': current_user.bot_id
            }
        return jsonify(result), 200
    finally:
        session.close()


@app.route('/api/notion/search', methods=['POST'])
@require_oauth
def search_notion_pages(current_user):
    """
    Search Notion pages accessible to the user.

    Expects JSON body with:
    - query: Search term (optional, returns all pages if empty)

    Returns:
    - pages: List of pages with id, title, and icon
    """
    try:
        import requests
        from oauth import refresh_notion_token

        data = request.get_json()
        query = data.get('query', '')

        # Prepare request body
        body = {
            'filter': {
                'property': 'object',
                'value': 'page'
            }
        }

        if query:
            body['query'] = query

        # Try with current token first
        access_token = current_user.access_token
        max_retries = 1

        for attempt in range(max_retries + 1):
            # Prepare request to Notion API
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }

            # Call Notion Search API
            response = requests.post(
                'https://api.notion.com/v1/search',
                headers=headers,
                json=body
            )

            # If successful, break the loop
            if response.ok:
                break

            # If 401 Unauthorized and we haven't retried yet, refresh token
            if response.status_code == 401 and attempt < max_retries:
                logger.warning(f"⚠️  Token expired for user {current_user.bot_id}, attempting refresh...")
                try:
                    token_data = refresh_notion_token(current_user)
                    access_token = token_data['access_token']
                    logger.info(f"✅ Token refreshed, retrying request...")
                    continue
                except Exception as refresh_error:
                    logger.error(f"❌ Token refresh failed: {refresh_error}")
                    return jsonify({
                        'error': 'Authentication failed',
                        'message': 'Votre session Notion a expiré et n\'a pas pu être renouvelée. Veuillez vous reconnecter.'
                    }), 401

            # If we get here, the request failed and we can't retry
            logger.error(f"❌ Notion API error: {response.status_code} - {response.text}")
            return jsonify({
                'error': 'Failed to search Notion pages',
                'message': response.text
            }), response.status_code

        results = response.json()

        # Helper function to normalize Notion IDs (remove dashes for comparison)
        def normalize_id(notion_id):
            if not notion_id:
                return None
            return notion_id.replace('-', '')

        # Format results to return only necessary information
        pages = []
        page_map = {}  # Map of page_id -> page data for parent lookup

        for result in results.get('results', []):
            if result.get('object') == 'page':
                # Extract page title
                title = 'Untitled'
                properties = result.get('properties', {})

                # Try to get title from various possible properties
                for prop_name, prop_value in properties.items():
                    if prop_value.get('type') == 'title':
                        title_array = prop_value.get('title', [])
                        if title_array and len(title_array) > 0:
                            title = title_array[0].get('plain_text', 'Untitled')
                            break

                # Extract icon if present
                icon = None
                if result.get('icon'):
                    if result['icon'].get('type') == 'emoji':
                        icon = result['icon'].get('emoji')
                    elif result['icon'].get('type') == 'external':
                        icon = result['icon'].get('external', {}).get('url')
                    elif result['icon'].get('type') == 'file':
                        icon = result['icon'].get('file', {}).get('url')

                # Extract parent information
                parent_info = result.get('parent', {})
                parent_type = parent_info.get('type')
                parent_id = None

                if parent_type == 'page_id':
                    parent_id = parent_info.get('page_id')
                elif parent_type == 'database_id':
                    parent_id = parent_info.get('database_id')

                page_data = {
                    'id': result.get('id'),
                    'title': title,
                    'icon': icon,
                    'parent_type': parent_type,
                    'parent_id': parent_id
                }

                pages.append(page_data)
                # Store in map with normalized ID for reliable lookup
                page_map[normalize_id(result.get('id'))] = page_data

        # Second pass: resolve parent titles for pages whose parent is in the results
        for page in pages:
            if page['parent_id']:
                # Try to find parent using normalized IDs
                normalized_parent_id = normalize_id(page['parent_id'])
                if normalized_parent_id in page_map:
                    page['parent_title'] = page_map[normalized_parent_id]['title']
                else:
                    page['parent_title'] = None
            else:
                page['parent_title'] = None

        return jsonify({
            'pages': pages,
            'has_more': results.get('has_more', False)
        }), 200

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"\n❌ Error searching Notion pages:")
        logger.error(error_trace)
        return jsonify({
            'error': 'Failed to search pages',
            'message': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
@require_oauth
def upload_file(current_user):
    """
    Upload and process an image to create a Notion page.

    Requires OAuth authentication.
    The authenticated user's Notion token will be used to create the page.

    Form data:
    - photo: The image file
    - test_mode: 'true' or 'false' (optional, default: false)
    """
    import requests
    from oauth import refresh_notion_token

    # Check if user has configured a default page ID
    if not current_user.notion_page_id:
        return jsonify({
            'error': 'No default page configured',
            'message': 'Please configure a default Notion page via /api/user/page-id'
        }), 400

    # Validate file presence
    if 'photo' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['photo']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Get test_mode parameter
    test_mode = request.form.get('test_mode', 'false').lower() == 'true'

    if file and allowed_file(file.filename):
        # Create user-specific upload folder to handle concurrency
        user_upload_folder = UPLOAD_FOLDER / current_user.bot_id
        user_upload_folder.mkdir(exist_ok=True)

        # Clean user's upload folder
        for old_file in user_upload_folder.glob('*'):
            if old_file.is_file():
                old_file.unlink()

        # Save new file
        filename = secure_filename(file.filename)
        filepath = user_upload_folder / filename
        file.save(filepath)

        # VALIDATE TOKEN BEFORE PROCESSING
        # Make a simple API call to verify the token is valid
        logger.info(f"\n🔐 Validating Notion token...")
        access_token = current_user.access_token

        validation_headers = {
            'Authorization': f'Bearer {access_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }

        # Simple validation call to Notion API (get user info)
        validation_response = requests.get(
            'https://api.notion.com/v1/users/me',
            headers=validation_headers
        )

        # If token is invalid, try to refresh it
        if validation_response.status_code == 401:
            logger.warning(f"⚠️  Token expired for user {current_user.bot_id}, attempting refresh...")
            try:
                token_data = refresh_notion_token(current_user)
                access_token = token_data['access_token']
                logger.info(f"✅ Token refreshed successfully")
            except Exception as refresh_error:
                logger.error(f"❌ Token refresh failed: {refresh_error}")
                return jsonify({
                    'success': False,
                    'error': 'Authentication failed',
                    'message': 'Votre session Notion a expiré et n\'a pas pu être renouvelée. Veuillez vous reconnecter.'
                }), 401
        elif not validation_response.ok:
            logger.error(f"❌ Token validation failed with status {validation_response.status_code}")
            return jsonify({
                'success': False,
                'error': 'Token validation failed',
                'message': f'Erreur de validation du token Notion: {validation_response.text}'
            }), 500

        logger.info(f"✅ Token is valid")

        # Process the image and upload to Notion
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"👤 User: {current_user.workspace_name} (bot_id: {current_user.bot_id})")
            logger.info(f"📸 Processing file: {filepath}")
            logger.info(f"🧪 Test mode: {test_mode}")
            logger.info(f"📄 Target page: {current_user.notion_page_id}")
            logger.info(f"{'='*60}\n")

            result = asyncio.run(
                process_and_upload(
                    str(user_upload_folder),
                    test_mode,
                    access_token,  # Use validated/refreshed token
                    current_user.notion_page_id
                )
            )

            logger.info(f"\n✅ Processing completed successfully!")

            return jsonify({
                'success': True,
                'message': 'Photo uploaded and processed successfully!',
                'details': result,
                'test_mode': test_mode
            })
        except ValueError as e:
            error_message = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"\n❌ ValueError during processing:")
            logger.error(error_trace)

            # Check if this is an "invalid page" error
            if "n'existe plus" in error_message or "plus accessible" in error_message:
                # Clear the invalid page_id from database
                from models import clear_user_notion_page
                clear_user_notion_page(current_user.bot_id)

                # Return 410 Gone to indicate the resource no longer exists
                return jsonify({
                    'success': False,
                    'error': 'page_deleted',
                    'message': error_message,
                    'needs_page_setup': True
                }), 410

            # Other ValueError - return 400
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"\n❌ ERROR during processing:")
            logger.error(error_trace)
            return jsonify({
                'success': False,
                'error': str(e),
                'trace': error_trace
            }), 500

    return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF'}), 400


async def process_and_upload(
    folder_path: str,
    test_mode: bool,
    user_notion_token: str,
    user_notion_page_id: str
):
    """
    Process the uploaded image and create Notion page.

    Args:
        folder_path: Path to the folder containing the image
        test_mode: If True, uses mock components (no LLM calls)
        user_notion_token: User's Notion OAuth access token
        user_notion_page_id: User's default Notion page ID for notes

    Returns:
        Success message string
    """
    notion_connector = McpNotionConnector()

    try:
        if test_mode:
            logger.info("🧪 TEST MODE - Using mock components (zero LLM calls)")
            image_text_extractor = MockImageTextExtractor(folder_path)
            draft_enhancer = MockDraftEnhancer()
            notes_creator = MockNotesCreator(
                notion_connector,
                draft_enhancer,
                image_text_extractor
            )
        else:
            logger.info("🚀 PRODUCTION MODE - Using real LLM components")
            image_text_extractor = ImageTextExtractor(folder_path)
            draft_enhancer = DraftEnhancer()
            notes_creator = NotesCreator(
                notion_connector,
                draft_enhancer,
                image_text_extractor
            )

        await notes_creator.notes_creation(
            user_notion_token=user_notion_token,
            user_notion_page_id=user_notion_page_id
        )

        mode_label = "TEST MODE" if test_mode else "PRODUCTION MODE"
        return f"Successfully created Notion page! ({mode_label})"

    finally:
        await notion_connector.cleanup()


if __name__ == '__main__':
    # Verify OAuth configuration
    required_oauth_vars = ['NOTION_CLIENT_ID', 'NOTION_CLIENT_SECRET']
    missing_oauth_vars = [var for var in required_oauth_vars if not os.getenv(var)]

    if missing_oauth_vars:
        logger.error(f"\n❌ ERROR: Missing OAuth environment variables: {', '.join(missing_oauth_vars)}")
        logger.error("Please check your .env file and configure Notion OAuth credentials")
        sys.exit(1)

    # Check OpenAI configuration
    has_openai = os.getenv('OPENAI_API_KEY')
    has_azure = os.getenv('AZURE_OPENAI_API_KEY') and os.getenv('AZURE_OPENAI_ENDPOINT')

    if not has_openai and not has_azure:
        logger.error("\n❌ ERROR: No OpenAI configuration found")
        logger.error("Please set either OPENAI_API_KEY or (AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT)")
        sys.exit(1)

    port = int(os.getenv('BACKEND_PORT', 5001))

    print(f"\n{'='*60}")
    print(f"  Notes2Notion Backend API (OAuth)")
    print(f"{'='*60}")
    print(f"\nAPI Endpoints:")
    print(f"  - GET  http://localhost:{port}/api/health")
    print(f"  - POST http://localhost:{port}/api/oauth/callback")
    print(f"  - GET  http://localhost:{port}/api/user/info")
    print(f"  - POST http://localhost:{port}/api/user/page-id")
    print(f"  - POST http://localhost:{port}/api/notion/search")
    print(f"  - POST http://localhost:{port}/api/upload")
    print(f"\nAuthentication:")
    print(f"  - Method: OAuth 2.0 (Notion)")
    print(f"  - Client ID: {os.getenv('NOTION_CLIENT_ID')}")
    print(f"\nEnvironment:")
    print(f"  - OpenAI: {'✅ Azure' if has_azure else '✅ OpenAI'}")
    print(f"  - Database: ✅ Initialized")
    print(f"  - Upload folder: {UPLOAD_FOLDER}")
    print(f"\n{'='*60}\n")

    app.run(host='0.0.0.0', port=port, debug=False)
