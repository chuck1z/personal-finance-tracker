import os
from datetime import datetime, timedelta
import json
import requests
from sqlalchemy.exc import IntegrityError

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import pandas as pd

from src.models import db, User, BankStatement, Transaction, ProcessingLog, Bank, TransactionCategory
from src.auth import create_hashed_password, verify_password, authenticate_user
from src.ocr_processor import BankStatementOCR

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://finanalyze_user:finanalyze_password@localhost:5432/finanalyze')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-very-strong-jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

db.init_app(app)

ocr_processor = BankStatementOCR()

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
RESULTS_FOLDER = os.environ.get('RESULTS_FOLDER', 'results')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': 'Missing username, email, or password'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User with that email already exists'}), 409

    hashed_password = create_hashed_password(password)
    new_user = User(username=username, email=email, password_hash=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Database error during registration'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Missing email or password'}), 400

    user = User.query.filter_by(email=email).first()
    access_token = authenticate_user(user, password)

    if access_token:
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return jsonify(logged_in_as=current_user_id), 200

@app.route('/ocr/process', methods=['POST'])
@jwt_required()
def ocr_process_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: pdf, png, jpg, jpeg'}), 400

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)

        ocr_result = ocr_processor.process_statement(filepath, output_format='dict')

        return jsonify({
            'success': True,
            'filename': unique_filename,
            'account_info': ocr_result.get('account_info', {}),
            'transactions': ocr_result.get('transactions', []),
            'raw_text_preview': ocr_result.get('raw_text', '')[:500]
        }), 200

    except Exception as e:
        app.logger.error(f"OCR Processing error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

