"""
WSGI entry point for Passenger (Siteground)
"""
import sys
import os

# Add the application directory to the path
INTERP = os.path.expanduser("~/ginger_universe/venv/bin/python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Set up paths
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from app import app as application
