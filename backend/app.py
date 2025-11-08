import asyncio
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import sys
import traceback
import requests
from functools import wraps

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path for imports
# In Docker, src is copied to /app/src, and app.py is at /app/app.py
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from Notes2Notion.notes_builder import NotesCreator, DraftEnhancer
from Notes2Notion.tooling import ImageTextExtractor, create_notion_connector
from Notes2Notion.mock_components import (MockImageTextExtractor, MockDraftEnhancer,
                                          MockNotesCreator)

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

# Configuration
UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def require_access_code(f):
    """
    Decorator to require access code authentication.

    Checks for 'Authorization: Bearer <access_code>' header.
    This will be compatible with future NextAuth migration where
    the Bearer token will be a session token instead of the static access code.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the configured access code from environment
        access_code = os.getenv('ACCESS_CODE')

        # If no access code is configured, allow the request (backward compatibility)
        if not access_code:
            print("⚠️  WARNING: No ACCESS_CODE configured. API is unprotected!")
            return f(*args, **kwargs)

        # Get the Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Missing Authorization header'
            }), 401

        # Check format: "Bearer <code>"
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid Authorization header format. Expected: Bearer <access_code>'
            }), 401

        # Extract the token
        provided_code = auth_header[7:]  # Remove "Bearer " prefix

        # Verify the access code
        if provided_code != access_code:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid access code'
            }), 401

        # Access code is valid, proceed with the request
        return f(*args, **kwargs)

    return decorated_function


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Notes2Notion Backend',
        'version': '2.0.0-pwa'
    })


@app.route('/api/upload', methods=['POST'])
@require_access_code
def upload_file():
    """
    Upload and process an image to create a Notion page.

    Form data:
    - photo: The image file
    - test_mode: 'true' or 'false' (optional, default: false)
    """
    # Validate file presence
    if 'photo' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['photo']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Get test_mode parameter
    test_mode = request.form.get('test_mode', 'false').lower() == 'true'

    #TODO: handle concurrency issues with multiple uploads from different users
    if file and allowed_file(file.filename):
        # Clean upload folder first
        for old_file in UPLOAD_FOLDER.glob('*'):
            if old_file.is_file():
                old_file.unlink()

        # Save new file
        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        file.save(filepath)

        # Process the image and upload to Notion
        try:
            print(f"\n{'='*60}")
            print(f"📸 Processing file: {filepath}")
            print(f"🧪 Test mode: {test_mode}")
            print(f"{'='*60}\n")

            result = asyncio.run(process_and_upload(str(UPLOAD_FOLDER), test_mode))

            print(f"\n✅ Processing completed successfully!")

            return jsonify({
                'success': True,
                'message': 'Photo uploaded and processed successfully!',
                'details': result,
                'test_mode': test_mode
            })
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"\n❌ ERROR during processing:")
            print(error_trace)
            return jsonify({
                'success': False,
                'error': str(e),
                'trace': error_trace
            }), 500

    return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF'}), 400


@app.route('/api/notion/oauth/exchange', methods=['POST'])
def notion_oauth_exchange():
    print('coucou from /api/notion/oauth/exchange')
    data = request.get_json()
    print(f"[DATA] {data}")
    code = data.get("code")
    print(f"[CODE] {code}")
    if not code:
        return jsonify({"error": "missing code"}), 400

    print(f"client_id {os.getenv("NOTION_MCP_CLIENT_ID")}")
    print(f"client_secret {os.getenv("NOTION_MCP_CLIENT_SECRET")}")
    print(f"redirect_uri {os.getenv("NOTION_MCP_REDIRECT_URI")}")
    res = requests.post(
        "https://mcp.notion.com/token",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": os.getenv("NOTION_MCP_CLIENT_ID"),
            "client_secret": os.getenv("NOTION_MCP_CLIENT_SECRET"),
            "redirect_uri": os.getenv("NOTION_MCP_REDIRECT_URI"),
        },
        headers={"Content-Type": "application/json"},
    )

    if res.status_code != 200:
        return jsonify({"error": "token_exchange_failed"}), 400

    token_data = res.json()
    print("Token response:", token_data)

    # TODO: store securely. Temporary dev storage:
    with open("/app/notion_token.json", "w") as f:
        f.write(res.text)

    return jsonify({"ok": True})


async def process_and_upload(folder_path: str, test_mode: bool = False):
    """
    Process the uploaded image and create Notion page.

    Args:
        folder_path: Path to the folder containing the image
        test_mode: If True, uses mock components (no LLM calls)

    Returns:
        Success message string
    """
    notion_connector = create_notion_connector

    if test_mode:
        print("🧪 TEST MODE - Using mock components (zero LLM calls)")
        image_text_extractor = MockImageTextExtractor(folder_path)
        draft_enhancer = MockDraftEnhancer()
        notes_creator = MockNotesCreator(
            notion_connector,
            draft_enhancer,
            image_text_extractor
        )
    else:
        print("🚀 PRODUCTION MODE - Using real LLM components")
        image_text_extractor = ImageTextExtractor(folder_path)
        draft_enhancer = DraftEnhancer()
        notes_creator = NotesCreator(
            notion_connector,
            draft_enhancer,
            image_text_extractor
        )

    await notes_creator.notes_creation()

    mode_label = "TEST MODE" if test_mode else "PRODUCTION MODE"
    return f"Successfully created Notion page! ({mode_label})"


if __name__ == '__main__':
    # Verify environment variables

    # Check OpenAI configuration
    has_openai = os.getenv('OPENAI_API_KEY')

    if not has_openai:
        print("\n❌ ERROR: No OpenAI configuration found")
        print("Please set OPENAI_API_KEY")
        sys.exit(1)

    port = int(os.getenv('BACKEND_PORT', 5001))

    print(f"\n{'='*60}")
    print(f"  Notes2Notion Backend API")
    print(f"{'='*60}")
    print(f"\nAPI Endpoints:")
    print(f"  - GET  http://localhost:{port}/api/health")
    print(f"  - POST http://localhost:{port}/api/upload")
    print(f"\nEnvironment:")
    print(f"  - Notion: ✅ Configured")
    print(f"  - Upload folder: {UPLOAD_FOLDER}")
    print(f"\n{'='*60}\n")

    app.run(host='0.0.0.0', port=port, debug=True)
