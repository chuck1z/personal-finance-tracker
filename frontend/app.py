
import os
from flask import Flask, render_template, request, jsonify, send_from_directory, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import tempfile
import shutil
import pandas as pd
import requests # Import requests for making HTTP calls to the backend

# Assuming BankStatementOCR is now handled by the backend, remove its import
# from ocr_processor import BankStatementOCR

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# The frontend should not manage UPLOAD_FOLDER and RESULTS_FOLDER locally anymore.
# These are now managed by the backend. However, if the frontend still needs to serve static results,
# we might need a way to fetch them from the backend or a shared volume, which is beyond the current scope.
# For now, we will assume results are returned directly or the frontend doesn't need local result storage.
# app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
# app.config['RESULTS_FOLDER'] = os.environ.get('RESULTS_FOLDER', 'results')

# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Remove ocr_processor initialization as it's now in the backend
# ocr_processor = BankStatementOCR()

# Define backend API URL - this should come from an environment variable in production
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:5001') # Default to local backend

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('src/index.html')

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

        # Prepare file for sending to backend
        files = {'file': (file.filename, file.stream, file.content_type)}

        # In a real application, you would pass an authentication token here
        # For now, assuming the backend /ocr/process endpoint will eventually require JWT_REQUIRED
        # headers = {'Authorization': f'Bearer {your_jwt_token}'}
        
        # Send file to backend OCR endpoint
        backend_response = requests.post(f"{BACKEND_API_URL}/ocr/process", files=files)
        backend_response.raise_for_status() # Raise an exception for HTTP errors

        ocr_result = backend_response.json()

        # The backend now handles saving results and provides a structured response
        # The frontend will just display what it receives.

        response_data = {
            'success': True,
            'filename': ocr_result.get('filename'),
            'account_info': ocr_result.get('account_info', {}),
            'transactions': ocr_result.get('transactions', []),
            'transaction_count': len(ocr_result.get('transactions', [])),
            'raw_text_preview': ocr_result.get('raw_text_preview', '')
        }

        # frontend no longer saves result files locally for OCR processing
        # result_filename = f"{timestamp}_result.json"
        # result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        # with open(result_path, 'w') as f:
        #     json.dump(response_data, f, indent=2)
        # response_data['result_file'] = result_filename
        
        return jsonify(response_data)
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error communicating with backend: {e}'}), backend_response.status_code if 'backend_response' in locals() else 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/<format>', methods=['POST'])
def export_data(format):
    try:
        # The export functionality in the frontend might need to be re-evaluated.
        # If the backend is now the source of truth for processed data, 
        # the frontend might request export directly from the backend or receive the data to export.
        # For simplicity, assuming the frontend can still construct the export from the received transactions.
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
    # Frontend no longer has local upload/results folders to clean up.
    # This cleanup functionality should likely be moved to the backend.
    # For now, it will return success but perform no action.
    # In the future, this endpoint could trigger a backend cleanup endpoint.
    # try:
    #     for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULTS_FOLDER']]:
    #         for filename in os.listdir(folder):
    #             file_path = os.path.join(folder, filename)
    #             if os.path.getctime(file_path) < (datetime.now().timestamp() - 3600):
    #                 os.remove(file_path)
    #     return jsonify({'success': True, 'message': 'Cleanup completed'})
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500
    return jsonify({'success': True, 'message': 'Cleanup handled by backend.'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000) # Changed port to 5000 to match k8s frontend service
