from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_session import Session
import logging
import os
from datetime import timedelta
from app.api.route import math_bp
from app.api.auth_route import auth_bp
from app.utils.error_handler import register_error_handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    app.config['JSON_SORT_KEYS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    
    Session(app)

    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://localhost:5174"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Cache-Control"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    register_error_handlers(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
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
