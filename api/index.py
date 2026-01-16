"""
Vercel serverless function entrypoint for Flask app
"""
import sys
import os
from pathlib import Path

try:
    # Add parent directory to path to import dashboard
    parent_dir = Path(__file__).parent.parent.absolute()
    sys.path.insert(0, str(parent_dir))
    
    # Set working directory for Vercel
    try:
        os.chdir(parent_dir)
    except:
        pass  # If we can't change directory, continue anyway
    
    # Import dashboard app with error handling
    try:
        from dashboard import app
        
        # Export the app for Vercel (Vercel looks for 'app' variable)
        # This is the Flask WSGI application
        application = app
        
        # Also export as 'app' for compatibility
        __all__ = ['app', 'application']
        
    except ImportError as e:
        # If import fails, create a minimal error app
        from flask import Flask
        error_app = Flask(__name__)
        
        @error_app.route('/')
        @error_app.route('/<path:path>')
        def error_handler(path=''):
            import traceback
            error_details = traceback.format_exc()
            return f"Error importing dashboard: {str(e)}\n\nTraceback:\n{error_details}", 500
        
        application = error_app
        app = error_app
        
except Exception as e:
    # Fallback: create minimal Flask app
    from flask import Flask
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    @fallback_app.route('/<path:path>')
    def fallback_handler(path=''):
        import traceback
        error_details = traceback.format_exc()
        return f"Serverless function error: {str(e)}\n\nTraceback:\n{error_details}", 500
    
    application = fallback_app
    app = fallback_app
