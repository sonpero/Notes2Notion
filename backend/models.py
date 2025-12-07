"""
Database models for Notes2Notion OAuth integration.

This module defines the SQLAlchemy models for storing user OAuth tokens
and workspace information for Notion integration.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from typing import Dict, Any, List
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

Base = declarative_base()


class User(Base):
    """
    User model for storing Notion OAuth credentials and workspace information.

    Each user represents a unique Notion workspace connection authenticated via OAuth.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Notion OAuth identifiers
    bot_id = Column(String(255), unique=True, nullable=False, index=True)
    workspace_id = Column(String(255), nullable=False)
    workspace_name = Column(String(500))

    # OAuth tokens
    access_token = Column(String(1000), nullable=False)
    refresh_token = Column(String(1000))

    # User's preferred Notion page for notes
    # This is where the user's handwritten notes will be created
    notion_page_id = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # License relationship
    license_key = relationship("LicenseKey", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(bot_id='{self.bot_id}', workspace_name='{self.workspace_name}')>"


class LicenseKey(Base):
    """
    License key model for gating access to Notes2Notion during beta testing.

    Format: BETA-XXXX-XXXX-XXXX (unique, no expiration)
    Each license can only be used by one user.
    """
    __tablename__ = 'license_keys'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # License key (unique, indexed for fast lookup)
    # Format: BETA-XXXX-XXXX-XXXX
    key = Column(String(50), unique=True, nullable=False, index=True)

    # Activation status
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    used_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)  # Set when first used
    revoked_at = Column(DateTime, nullable=True)    # Set if revoked

    # Metadata
    created_by = Column(String(255), nullable=True)  # Admin who created it
    notes = Column(String(1000), nullable=True)      # Admin notes

    # Relationship
    user = relationship("User", back_populates="license_key")

    def __repr__(self):
        return f"<LicenseKey(key='{self.key}', is_active={self.is_active}, used={self.used_by_user_id is not None})>"


# Database setup
def get_database_url():
    """
    Get database URL from environment variable.

    Returns:
        str: Database connection URL

    Raises:
        ValueError: If DATABASE_URL is not set
    """
    url = os.getenv('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


def init_db():
    """
    Initialize the database by creating all tables.

    This function should be called when the application starts.
    Includes connection pooling configuration for MySQL production use.
    """
    engine = create_engine(
        get_database_url(),
        echo=False,
        pool_pre_ping=True,      # Verify connections before using
        pool_recycle=3600,       # Recycle connections after 1 hour
        pool_size=5,             # Connection pool size
        max_overflow=10          # Maximum overflow connections
    )
    Base.metadata.create_all(engine)
    return engine


def run_migrations():
    """
    Run Alembic migrations automatically on application startup.

    This ensures the database schema is always up-to-date without manual intervention.
    """
    from alembic.config import Config
    from alembic import command

    # Get path to alembic.ini (same directory as this file)
    alembic_cfg_path = os.path.join(os.path.dirname(__file__), 'alembic.ini')

    # Create Alembic config
    alembic_cfg = Config(alembic_cfg_path)

    # Override sqlalchemy.url with environment variable
    alembic_cfg.set_main_option('sqlalchemy.url', get_database_url())

    logger.info("🔄 Running database migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations completed successfully")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


def get_session():
    """
    Create and return a new database session.

    Returns:
        Session: SQLAlchemy session object
    """
    engine = create_engine(
        get_database_url(),
        echo=False,
        pool_pre_ping=True,      # Verify connections before using
        pool_recycle=3600,       # Recycle connections after 1 hour
        pool_size=5,             # Connection pool size
        max_overflow=10          # Maximum overflow connections
    )
    Session = sessionmaker(bind=engine)
    return Session()


def get_user_by_bot_id(bot_id: str):
    """
    Retrieve a user by their Notion bot_id.

    Args:
        bot_id: Notion bot identifier from OAuth response

    Returns:
        User: User object if found, None otherwise
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(bot_id=bot_id).first()
        return user
    finally:
        session.close()


def create_or_update_user(
    bot_id: str,
    workspace_id: str,
    access_token: str,
    workspace_name: str = None,
    refresh_token: str = None,
    notion_page_id: str = None
):
    """
    Create a new user or update existing user with OAuth tokens.

    Args:
        bot_id: Notion bot identifier (unique per integration per workspace)
        workspace_id: Notion workspace identifier
        access_token: OAuth access token
        workspace_name: Human-readable workspace name (optional)
        refresh_token: OAuth refresh token (optional)
        notion_page_id: Default page ID for creating notes (optional)

    Returns:
        User: Created or updated user object
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(bot_id=bot_id).first()

        if user:
            # Update existing user
            user.access_token = access_token
            user.workspace_id = workspace_id
            if workspace_name:
                user.workspace_name = workspace_name
            if refresh_token:
                user.refresh_token = refresh_token
            if notion_page_id:
                user.notion_page_id = notion_page_id
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                bot_id=bot_id,
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                access_token=access_token,
                refresh_token=refresh_token,
                notion_page_id=notion_page_id
            )
            session.add(user)

        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_user_notion_page(bot_id: str, notion_page_id: str):
    """
    Update the default Notion page ID for a user.

    Args:
        bot_id: User's bot identifier
        notion_page_id: New Notion page ID for creating notes

    Returns:
        User: Updated user object, or None if user not found
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(bot_id=bot_id).first()
        if user:
            user.notion_page_id = notion_page_id
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def clear_user_notion_page(bot_id: str):
    """
    Clear the Notion page ID for a user (set to None).
    This is typically called when the configured page is no longer valid.

    Args:
        bot_id: User's bot identifier

    Returns:
        User: Updated user object, or None if user not found
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(bot_id=bot_id).first()
        if user:
            user.notion_page_id = None
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            logger.info(f"✅ Cleared notion_page_id for user {bot_id}")
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# License Key Management Functions

def validate_license_key(license_key: str) -> Dict[str, Any]:
    """
    Validate a license key and return its status.

    Args:
        license_key: License key to validate

    Returns:
        dict: {'valid': bool, 'is_used': bool, 'user_id': int|None, 'message': str}
    """
    session = get_session()
    try:
        normalized_key = license_key.strip().upper()

        license_obj = session.query(LicenseKey).filter_by(key=normalized_key).first()

        if not license_obj:
            return {'valid': False, 'is_used': False, 'user_id': None,
                    'message': 'Clé de licence invalide'}

        if not license_obj.is_active:
            return {'valid': False, 'is_used': license_obj.used_by_user_id is not None,
                    'user_id': license_obj.used_by_user_id, 'message': 'Cette clé a été révoquée'}

        if license_obj.used_by_user_id is not None:
            return {'valid': True, 'is_used': True, 'user_id': license_obj.used_by_user_id,
                    'message': 'Clé déjà utilisée'}

        return {'valid': True, 'is_used': False, 'user_id': None, 'message': 'Clé valide'}
    finally:
        session.close()


def activate_license_key(license_key: str, user_id: int) -> bool:
    """
    Activate a license key by linking it to a user.

    Args:
        license_key: License key to activate
        user_id: User ID to link the license to

    Returns:
        bool: True if activation succeeded

    Raises:
        ValueError: If key is invalid or already used
    """
    session = get_session()
    try:
        normalized_key = license_key.strip().upper()

        license_obj = session.query(LicenseKey).filter_by(key=normalized_key).first()

        if not license_obj or not license_obj.is_active:
            raise ValueError("Invalid or revoked license key")

        if license_obj.used_by_user_id is not None:
            raise ValueError("License key already in use")

        license_obj.used_by_user_id = user_id
        license_obj.activated_at = datetime.utcnow()

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def create_license_key(key: str, created_by: str = "admin", notes: str = None) -> LicenseKey:
    """
    Create a new license key.

    Args:
        key: License key string (will be normalized to uppercase)
        created_by: Admin username who created the key
        notes: Optional notes about this license

    Returns:
        LicenseKey: Created license key object

    Raises:
        ValueError: If key already exists
    """
    session = get_session()
    try:
        normalized_key = key.strip().upper()

        existing = session.query(LicenseKey).filter_by(key=normalized_key).first()
        if existing:
            raise ValueError(f"License key already exists: {normalized_key}")

        license_obj = LicenseKey(
            key=normalized_key,
            is_active=True,
            created_by=created_by,
            notes=notes
        )

        session.add(license_obj)
        session.commit()
        session.refresh(license_obj)
        return license_obj
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def revoke_license_key(license_key: str) -> bool:
    """
    Revoke a license key.

    Args:
        license_key: License key to revoke

    Returns:
        bool: True if revoked successfully, False if not found
    """
    session = get_session()
    try:
        normalized_key = license_key.strip().upper()
        license_obj = session.query(LicenseKey).filter_by(key=normalized_key).first()

        if not license_obj:
            return False

        license_obj.is_active = False
        license_obj.revoked_at = datetime.utcnow()
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def list_all_license_keys(active_only: bool = False) -> List[Dict]:
    """
    List all license keys with their status.

    Args:
        active_only: If True, only return active (non-revoked) keys

    Returns:
        List[Dict]: List of license key information dictionaries
    """
    session = get_session()
    try:
        query = session.query(LicenseKey)
        if active_only:
            query = query.filter_by(is_active=True)

        keys = query.all()
        result = []

        for key_obj in keys:
            user_info = None
            if key_obj.used_by_user_id:
                user = session.query(User).filter_by(id=key_obj.used_by_user_id).first()
                if user:
                    user_info = {'workspace_name': user.workspace_name, 'bot_id': user.bot_id}

            result.append({
                'id': key_obj.id,
                'key': key_obj.key,
                'is_active': key_obj.is_active,
                'is_used': key_obj.used_by_user_id is not None,
                'user': user_info,
                'created_at': key_obj.created_at.isoformat(),
                'activated_at': key_obj.activated_at.isoformat() if key_obj.activated_at else None,
                'revoked_at': key_obj.revoked_at.isoformat() if key_obj.revoked_at else None,
                'created_by': key_obj.created_by,
                'notes': key_obj.notes
            })

        return result
    finally:
        session.close()
