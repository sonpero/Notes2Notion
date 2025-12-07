"""
OAuth utilities for Notion integration.

This module handles OAuth token exchange, validation, and session management
for the Notes2Notion application.
"""

import os
import base64
import requests
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from typing import Optional, Dict, Any
import logging

from models import get_user_by_bot_id, create_or_update_user

# Configure logging
logger = logging.getLogger(__name__)


# Notion OAuth configuration
NOTION_OAUTH_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")

# JWT configuration for session tokens
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 1 week


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for Notion access token.

    This function implements the OAuth 2.0 authorization code flow with Notion.
    It sends a POST request to Notion's token endpoint with the authorization code
    and receives access_token, refresh_token, and workspace information.

    Args:
        code: Authorization code received from Notion OAuth callback

    Returns:
        dict: Token response containing:
            - access_token: Notion API access token
            - refresh_token: Token for refreshing access
            - bot_id: Unique bot identifier
            - workspace_id: Notion workspace ID
            - workspace_name: Human-readable workspace name
            - owner: Workspace owner information

    Raises:
        Exception: If token exchange fails or Notion API returns an error
    """
    # Validate configuration
    if not NOTION_CLIENT_ID or not NOTION_CLIENT_SECRET:
        raise ValueError("NOTION_CLIENT_ID and NOTION_CLIENT_SECRET must be set")

    # Prepare Basic Authentication header
    credentials = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": NOTION_REDIRECT_URI
    }

    # Make request to Notion OAuth endpoint
    response = requests.post(
        NOTION_OAUTH_TOKEN_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        error_data = response.json()
        raise Exception(f"Notion OAuth error: {error_data.get('error', 'Unknown error')}")

    return response.json()


def create_session_token(bot_id: str) -> str:
    """
    Create a JWT session token for authenticated users.

    This token is returned to the frontend and used for subsequent API requests.
    It contains the user's bot_id and expiration timestamp.

    Args:
        bot_id: Notion bot identifier (unique per workspace integration)

    Returns:
        str: Encoded JWT token
    """
    payload = {
        "bot_id": bot_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_session_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT session token.

    Args:
        token: JWT token string

    Returns:
        str: bot_id if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("bot_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_from_token(token: str):
    """
    Get user object from session token.

    Args:
        token: JWT session token

    Returns:
        User: User object if token is valid and user exists, None otherwise
    """
    bot_id = verify_session_token(token)
    if not bot_id:
        return None

    return get_user_by_bot_id(bot_id)


def require_oauth(f):
    """
    Decorator to protect Flask routes with OAuth + License authentication.

    This decorator validates:
    1. JWT session token from the Authorization header
    2. User exists in database
    3. User has a valid, active license key

    Usage:
        @app.route('/api/protected')
        @require_oauth
        def protected_route(current_user):
            # current_user is automatically injected
            return jsonify({'user': current_user.workspace_name})

    The decorated function receives a 'current_user' parameter containing
    the User object from the database.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Verify token and get user
        current_user = get_current_user_from_token(token)

        if not current_user:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # NEW: Check user has valid license
        from models import get_session, LicenseKey
        session = get_session()
        try:
            license_obj = session.query(LicenseKey).filter_by(
                used_by_user_id=current_user.id,
                is_active=True
            ).first()

            if not license_obj:
                return jsonify({
                    'error': 'No valid license',
                    'message': 'Votre licence est invalide ou a été révoquée'
                }), 403  # 403 Forbidden (authenticated but not authorized)
        finally:
            session.close()

        # Inject current_user into the route function
        kwargs['current_user'] = current_user
        return f(*args, **kwargs)

    return decorated_function


def handle_oauth_callback(code: str, license_key: str = None) -> Dict[str, Any]:
    """
    Complete OAuth flow: exchange code, store user, activate license, return session token.

    This is the main function called by the OAuth callback endpoint.
    It orchestrates the entire OAuth flow:
    1. Exchange authorization code for Notion tokens
    2. Store/update user in database
    3. Activate license key if provided
    4. Create session token for frontend

    Args:
        code: Authorization code from Notion OAuth redirect
        license_key: (Optional) License key to activate for this user

    Returns:
        dict: Response containing:
            - session_token: JWT for subsequent API requests
            - workspace_name: User's Notion workspace name
            - bot_id: User identifier
            - needs_page_setup: Whether user needs to configure page ID

    Raises:
        Exception: If OAuth exchange or database operations fail
    """
    # Exchange code for Notion tokens
    oauth_response = exchange_code_for_token(code)

    # Extract data from Notion response
    access_token = oauth_response['access_token']
    refresh_token = oauth_response.get('refresh_token')
    bot_id = oauth_response['bot_id']
    workspace_id = oauth_response['workspace_id']
    workspace_name = oauth_response.get('workspace_name')

    # Store or update user in database
    user = create_or_update_user(
        bot_id=bot_id,
        workspace_id=workspace_id,
        access_token=access_token,
        workspace_name=workspace_name,
        refresh_token=refresh_token
    )

    # NEW: Activate license key if provided
    if license_key:
        try:
            # Import here to avoid circular dependency
            from models import activate_license_key, get_session, LicenseKey

            session = get_session()

            # Normalize the provided license key
            normalized_key = license_key.strip().upper()

            # Check if this specific license key is already used
            license_obj = session.query(LicenseKey).filter_by(key=normalized_key).first()

            if not license_obj:
                session.close()
                raise ValueError(f"License key not found: {normalized_key}")

            if not license_obj.is_active:
                session.close()
                raise ValueError("License key has been revoked")

            # Check if license is already used
            if license_obj.used_by_user_id is not None:
                # License is already used - verify it belongs to THIS user
                if license_obj.used_by_user_id == user.id:
                    logger.info(f"✅ User {user.id} reconnecting with their own license: {normalized_key}")
                    session.close()
                else:
                    # License belongs to a different user - REJECT
                    session.close()
                    raise ValueError("Cette clé de licence est déjà utilisée par un autre utilisateur")
            else:
                # License is available - activate it for this user
                session.close()
                activate_license_key(normalized_key, user.id)
                logger.info(f"✅ License key activated for new user {user.id}")

        except Exception as e:
            logger.warning(f"⚠️  License activation failed: {e}")
            raise  # Re-raise to return error to frontend

    # Create session token for frontend
    session_token = create_session_token(bot_id)

    return {
        'session_token': session_token,
        'workspace_name': workspace_name,
        'bot_id': bot_id,
        'needs_page_setup': user.notion_page_id is None
    }


def ensure_valid_token(user) -> str:
    """
    Ensure user has a valid Notion access token.

    This is a helper function that should be called before making Notion API requests.
    If the user's current token is invalid, it will attempt to refresh it.

    Note: This function does NOT validate the token against Notion API.
    It only refreshes the token if explicitly requested or after a 401 error.

    Args:
        user: User object with access_token and refresh_token

    Returns:
        str: Valid access token (either current or refreshed)

    Raises:
        Exception: If token refresh fails
    """
    # For now, just return the current token
    # Token refresh will be triggered by 401 errors from Notion API
    return user.access_token


def refresh_notion_token(user) -> Dict[str, str]:
    """
    Refresh a Notion access token using the refresh token.

    This function implements the OAuth 2.0 refresh token flow with Notion.
    It sends a POST request to Notion's token endpoint with the refresh_token
    and receives a new access_token.

    Args:
        user: User object with refresh_token

    Returns:
        dict: Token response containing:
            - access_token: New Notion API access token
            - refresh_token: New refresh token (may be the same or rotated)

    Raises:
        Exception: If token refresh fails or user has no refresh token
    """
    # Validate refresh token exists
    if not user.refresh_token:
        raise ValueError(f"User {user.bot_id} has no refresh token stored")

    # Validate configuration
    if not NOTION_CLIENT_ID or not NOTION_CLIENT_SECRET:
        raise ValueError("NOTION_CLIENT_ID and NOTION_CLIENT_SECRET must be set")

    # Prepare Basic Authentication header
    credentials = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": user.refresh_token
    }

    # Make request to Notion OAuth endpoint
    response = requests.post(
        NOTION_OAUTH_TOKEN_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        error_data = response.json()
        error_msg = error_data.get('error', 'Unknown error')
        raise Exception(f"Notion token refresh failed: {error_msg}")

    token_data = response.json()

    # Update user's tokens in database
    from models import get_session
    session = get_session()
    try:
        user.access_token = token_data['access_token']
        # Notion may rotate the refresh token, so update it if present
        if 'refresh_token' in token_data:
            user.refresh_token = token_data['refresh_token']
        user.updated_at = datetime.utcnow()

        session.add(user)
        session.commit()
        session.refresh(user)

        logger.info(f"✅ Successfully refreshed token for user {user.bot_id}")

        return {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token', user.refresh_token)
        }
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
