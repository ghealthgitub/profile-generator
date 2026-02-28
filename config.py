"""
🫚 Ginger Universe — Configuration
All secrets loaded from environment variables (set in Render dashboard)
"""

import os

# ── Database ─────────────────────────────────────────────────
# Uses the same PostgreSQL database as ginger-website and ginger-admin
# On Render, use the Internal Database URL for faster connections
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# ── Google Sheets (LEGACY — fallback if DATABASE_URL not set) ─
GOOGLE_SHEETS_URL = os.environ.get('GOOGLE_SHEETS_URL',
    'https://docs.google.com/spreadsheets/d/1TxSlrIVvEKpCfTRiUpCw4uE1GHNOM-Yi-LXzB_YZCgU/edit?usp=sharing')

# ── Claude API ───────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ── Admin credentials ────────────────────────────────────────
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin@ginger.healthcare')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

# ── Application ──────────────────────────────────────────────
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
