"""
Vercel serverless function entrypoint for Flask app
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import dashboard
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Set working directory for Vercel
os.chdir(parent_dir)

from dashboard import app

# Export the app for Vercel (Vercel looks for 'app' variable)
# This is the Flask WSGI application
application = app

# Also export as 'app' for compatibility
__all__ = ['app', 'application']
