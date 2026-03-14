from flask import jsonify
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base API Error"""
    status_code = 500
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['success'] = False
        rv['error'] = {
            'message': self.message,
            'type': self.__class__.__name__
        }
        return rv

class ValidationError(APIError):
    """Validation Error - 400"""
    status_code = 400

class NotFoundError(APIError):
    """Not Found Error - 404"""
    status_code = 404

class ServerError(APIError):
    """Internal Server Error - 500"""
    status_code = 500

class TimeoutError(APIError):
    """Request Timeout - 408"""
    status_code = 408

def handle_errors(f):
    """Decorator for consistent error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            logger.error(f"API Error: {e.message}", exc_info=True)
            return jsonify(e.to_dict()), e.status_code
        except ValueError as e:
            logger.error(f"Validation Error: {str(e)}", exc_info=True)
            error = ValidationError(str(e))
            return jsonify(error.to_dict()), error.status_code
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}", exc_info=True)
            error = ServerError("An unexpected error occurred")
            return jsonify(error.to_dict()), error.status_code
    return decorated_function

def register_error_handlers(app):
    """Register global error handlers for Flask app"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'success': False,
            'error': {
                'message': 'Resource not found',
                'type': 'NotFoundError'
            }
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"Internal Server Error: {str(error)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'message': 'Internal server error',
                'type': 'ServerError'
            }
        }), 500
