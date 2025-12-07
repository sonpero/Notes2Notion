#!/usr/bin/env python3
"""
License Key Management Tool for Notes2Notion

Usage:
    python license_manager.py generate [--count N] [--notes "..."]
    python license_manager.py list [--active-only]
    python license_manager.py revoke <LICENSE_KEY>
    python license_manager.py check <LICENSE_KEY>
    python license_manager.py stats
"""

import sys
import secrets
import string
from datetime import datetime
from pathlib import Path
import argparse
from tabulate import tabulate

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from models import (
    create_license_key,
    revoke_license_key,
    list_all_license_keys,
    validate_license_key,
    get_session,
    LicenseKey
)
from dotenv import load_dotenv

# Load .env (try .env.local first for local development, then fall back to project .env)
env_local_path = Path(__file__).parent / '.env.local'
env_path = Path(__file__).parent.parent / '.env'

if env_local_path.exists():
    load_dotenv(env_local_path, override=True)
else:
    load_dotenv(env_path, override=True)


def generate_license_key() -> str:
    """Generate random license key: BETA-XXXX-XXXX-XXXX"""
    # Exclude confusing characters
    chars = string.ascii_uppercase.replace('O', '').replace('I', '') + \
            string.digits.replace('0', '').replace('1', '')

    segments = []
    for _ in range(3):
        segment = ''.join(secrets.choice(chars) for _ in range(4))
        segments.append(segment)

    return f"BETA-{'-'.join(segments)}"


def cmd_generate(args):
    """Generate new license key(s)"""
    count = args.count
    notes = args.notes
    created_by = args.created_by or "admin-cli"

    print(f"\n🔑 Generating {count} license key(s)...\n")

    generated_keys = []

    for i in range(count):
        try:
            max_attempts = 10
            for attempt in range(max_attempts):
                key = generate_license_key()
                try:
                    license_obj = create_license_key(
                        key=key,
                        created_by=created_by,
                        notes=notes
                    )
                    generated_keys.append(license_obj.key)
                    print(f"✅ {license_obj.key}")
                    break
                except ValueError:
                    if attempt == max_attempts - 1:
                        print(f"❌ Failed after {max_attempts} attempts")
                        continue
        except Exception as e:
            print(f"❌ Error: {e}")

    if generated_keys:
        print(f"\n✅ Successfully generated {len(generated_keys)} key(s)")

        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                f.write(f"# Generated: {datetime.utcnow().isoformat()}\n")
                f.write(f"# Notes: {notes or 'N/A'}\n\n")
                for key in generated_keys:
                    f.write(f"{key}\n")
            print(f"📁 Saved to: {output_path}")


def cmd_list(args):
    """List all license keys"""
    keys = list_all_license_keys(active_only=args.active_only)

    if not keys:
        print("\n📭 No license keys found\n")
        return

    table_data = []
    for key in keys:
        status = "🟢 Active" if key['is_active'] else "🔴 Revoked"
        usage = "✓ Used" if key['is_used'] else "○ Available"
        user_info = key['user']['workspace_name'] if key['user'] else ""

        table_data.append([
            key['key'],
            status,
            usage,
            user_info,
            key['created_at'][:10],
            key['notes'] or ""
        ])

    print(f"\n📋 License Keys ({len(keys)} total)\n")
    print(tabulate(
        table_data,
        headers=['License Key', 'Status', 'Usage', 'User', 'Created', 'Notes'],
        tablefmt='grid'
    ))
    print()


def cmd_revoke(args):
    """Revoke a license key"""
    print(f"\n🔒 Revoking: {args.license_key}...")

    try:
        success = revoke_license_key(args.license_key)
        if success:
            print(f"✅ Revoked successfully\n")
        else:
            print(f"❌ License key not found\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")


def cmd_check(args):
    """Check license key status"""
    print(f"\n🔍 Checking: {args.license_key}...\n")

    try:
        result = validate_license_key(args.license_key)
        print(f"Valid: {result['valid']}")
        print(f"Used: {result['is_used']}")
        print(f"Message: {result['message']}")
        if result['user_id']:
            print(f"User ID: {result['user_id']}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}\n")


def cmd_stats(args):
    """Show statistics"""
    all_keys = list_all_license_keys(active_only=False)

    total = len(all_keys)
    active = sum(1 for k in all_keys if k['is_active'])
    revoked = total - active
    used = sum(1 for k in all_keys if k['is_used'])
    available = sum(1 for k in all_keys if k['is_active'] and not k['is_used'])

    print("\n📊 License Key Statistics\n")
    print(f"Total:      {total}")
    print(f"Active:     {active}")
    print(f"Revoked:    {revoked}")
    print(f"Used:       {used}")
    print(f"Available:  {available}")
    print()


def main():
    parser = argparse.ArgumentParser(description='License Key Management Tool')
    subparsers = parser.add_subparsers(dest='command')

    # Generate
    gen = subparsers.add_parser('generate', help='Generate new license keys')
    gen.add_argument('--count', type=int, default=1, help='Number of keys to generate')
    gen.add_argument('--notes', type=str, help='Notes about this batch')
    gen.add_argument('--created-by', type=str, default='admin-cli', help='Admin username')
    gen.add_argument('--output', type=str, help='Output file path')

    # List
    lst = subparsers.add_parser('list', help='List all license keys')
    lst.add_argument('--active-only', action='store_true', help='Show only active keys')

    # Revoke
    rev = subparsers.add_parser('revoke', help='Revoke a license key')
    rev.add_argument('license_key', help='License key to revoke')

    # Check
    chk = subparsers.add_parser('check', help='Check license key status')
    chk.add_argument('license_key', help='License key to check')

    # Stats
    subparsers.add_parser('stats', help='Show statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'generate': cmd_generate,
        'list': cmd_list,
        'revoke': cmd_revoke,
        'check': cmd_check,
        'stats': cmd_stats
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
