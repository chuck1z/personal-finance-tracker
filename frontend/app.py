import os
from flask import Flask, render_template, request, jsonify, send_from_directory, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import tempfile
import shutil
import pandas as pd
import requests
app = Flask(__name__,
            template_folder='src',
            static_folder='src/static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:5001')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PDF or image files'}), 400

        files = {'file': (file.filename, file.stream, file.content_type)}

        backend_response = requests.post(f"{BACKEND_API_URL}/ocr/process", files=files)
        backend_response.raise_for_status()

        ocr_result = backend_response.json()

        response_data = {
            'success': True,
            'filename': ocr_result.get('filename'),
            'account_info': ocr_result.get('account_info', {}),
            'transactions': ocr_result.get('transactions', []),
            'transaction_count': len(ocr_result.get('transactions', [])),
            'raw_text_preview': ocr_result.get('raw_text_preview', '')
        }

        return jsonify(response_data)
    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, 'status_code', 500)
        return jsonify({'error': f'Error communicating with backend: {e}'}), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/<format>', methods=['POST'])
def export_data(format):
    try:
        data = request.json
        transactions = data.get('transactions', [])
        
        if format == 'csv':
            df = pd.DataFrame(transactions)

            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            df.to_csv(temp_file.name, index=False)
            temp_file.close()
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mimetype='text/csv'
            )
        
        elif format == 'json':
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(data, temp_file, indent=2)
            temp_file.close()
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'statement_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        
        else:
            return jsonify({'error': 'Invalid export format'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    return jsonify({'success': True, 'message': 'Cleanup handled by backend.'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
