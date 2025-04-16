from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import uuid
import secrets
import pdb

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# API configuration
API_URL = "https://invoice-7-invoice-ai.adamastech.org/v1"
API_KEY = "JXfbsb7euy8pqqQJJiIBg8DpS4AiaIek6A9u1RLE"

# In-memory store for uploaded job data
job_data_store = {}

@app.route('/')
def index():
    return render_template('new_index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    pdb.set_trace
    if 'files' not in request.files:
        return jsonify({'error': 'No files part in the request'}), 400

    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400

    job_id = str(uuid.uuid4())
    filenames = [file.filename for file in files]

    url = f"{API_URL}/upload-files"
    payload = json.dumps({"job_id": job_id, "filenames": filenames})
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to get presigned URLs: {str(e)}'}), 500

    response_data = response.json()
    print(json.dumps(response_data, indent=2))

    upload_results = []
    for file_info in response_data["presigned_urls"]:
        file_name = file_info["file_name"]
        presigned_url = file_info["presigned_url"]
        content_type = file_info["content_type"]

        try:
            file = next((f for f in files if f.filename == file_name), None)
            if file is None:
                upload_results.append({
                    'file_name': file_name,
                    'success': False,
                    'error': 'File not found in request'
                })
                continue

            upload_response = requests.put(
                presigned_url,
                data=file.read(),
                headers={"Content-Type": content_type}
            )

            if upload_response.status_code == 200:
                upload_results.append({
                    'file_name': file_name,
                    'success': True
                })
            else:
                upload_results.append({
                    'file_name': file_name,
                    'success': False,
                    'error': f'Status code: {upload_response.status_code}'
                })
        except Exception as e:
            upload_results.append({
                'file_name': file_name,
                'success': False,
                'error': str(e)
            })

    # Save job info to memory for polling
    job_data_store[job_id] = filenames

    return jsonify({
        'success': True,
        'payload': payload
    })

@app.route('/result', methods=['POST'])
def get_result():
    payload =  request.form.get("payload")
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    }

    try:
        result_response = requests.post(f"{API_URL}/show-result", headers=headers, data=payload)
        result_response.raise_for_status()
        result_data = result_response.json()
        print("result_data")
        print(result_data)  # Optional: see the full response
        print(result_data.get('data', []))
        print("Condition check....")
        print(all('json_response' in item for item in result_data.get('data', [])))
        
        # If all responses are ready
        if all('json_response' in item for item in result_data.get('data', [])):
            
            print('if triggered')
            return jsonify({
                "status_code": 200,
                "raw_result": result_data
            })
        else:
            print('else triggered')
            return jsonify({'status': 'processing'}), 202

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch results: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
