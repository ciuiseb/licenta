import os
import logging
from functools import wraps
from flask import session, request, jsonify

logger = logging.getLogger(__name__)

MASTER_PASSCODE = os.getenv('MASTER_PASSCODE', 'demo1234')

def get_session_id():
    """Get the current session ID, or None if not authenticated."""
    return session.get('session_id')

def is_authenticated():
    """Check if the current session is authenticated."""
    return 'session_id' in session and session.get('authenticated', False)

def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 200
        if not is_authenticated():
            logger.warning(f"Unauthorized access attempt to {request.path}")
            return jsonify({
                "error": "Authentication required",
                "message": "Please authenticate with the passcode first"
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def validate_passcode(passcode):
    """Validate the provided passcode against the master passcode."""
    return passcode == MASTER_PASSCODE
