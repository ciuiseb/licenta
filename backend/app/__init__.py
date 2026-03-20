from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import logging
from app.api.route import math_bp
from app.utils.error_handler import register_error_handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    app.config['JSON_SORT_KEYS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://localhost:5174"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Cache-Control"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": False,
            "max_age": 3600
        }
    })
    
    socketio.init_app(app, cors_allowed_origins="*")
    
    register_error_handlers(app)

    app.register_blueprint(math_bp, url_prefix='/api/math')

    @app.route('/', methods=['GET', 'OPTIONS'])
    def root():
        """Root route for CORS preflight"""
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({
            "message": "Flask app is running",
            "version": "1.0.0",
            "status": "healthy"
        })

    logger.info("Application initialized successfully")
    return app
