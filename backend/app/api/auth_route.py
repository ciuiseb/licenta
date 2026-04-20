from flask import Blueprint, request, jsonify, session
import logging
import uuid
from app.middleware.auth import validate_passcode, is_authenticated, get_session_id
from app.utils.error_handler import handle_errors, ValidationError

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@handle_errors
def login():
    """Authenticate user with master passcode."""
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    if not data or 'passcode' not in data:
        raise ValidationError("Passcode is required")
    
    passcode = data.get('passcode')
    
    if not validate_passcode(passcode):
        logger.warning(f"Failed login attempt from {request.remote_addr}")
        return jsonify({
            "success": False,
            "error": "Invalid passcode"
        }), 401
    
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session['authenticated'] = True
    session.permanent = True
    
    logger.info(f"Successful login - Session ID: {session_id}")
    
    return jsonify({
        "success": True,
        "session_id": session_id,
        "message": "Authentication successful"
    })

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
def logout():
    """Logout and clear session."""
    if request.method == 'OPTIONS':
        return '', 200
    
    session_id = get_session_id()
    session.clear()
    
    logger.info(f"User logged out - Session ID: {session_id}")
    
    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    })

@auth_bp.route('/status', methods=['GET', 'OPTIONS'])
def status():
    """Check authentication status."""
    if request.method == 'OPTIONS':
        return '', 200
    
    authenticated = is_authenticated()
    session_id = get_session_id() if authenticated else None
    
    return jsonify({
        "authenticated": authenticated,
        "session_id": session_id
    })
