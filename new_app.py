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
API_URL = "https://invoice-10-invoice-ai.adamastech.org/v1"
API_KEY = "I1ZLeiV1ZdXvsp9pzDVA2iOnsfdTrjG9wcR5dP4f"

# In-memory store for uploaded job data
job_data_store = {}

@app.route('/')
def index():
    return render_template('new_index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
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
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to get presigned URLs: {str(e)}'}), 500

    response_data = response.json()
    if response_data["statusCode"] != 200:
        return jsonify({
        'success': False,
        'msg': response_data["error"]
    })
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

def compact_inner_dicts(obj):
    import re
    raw = json.dumps(obj, indent=2)

    # Regex to collapse inner dictionaries of format:
    # {
    #   "value": "...",
    #   "conf": ...
    # }
    # into: { "value": "...", "conf": ... }
    compacted = re.sub(r'\{\n\s+"value": (.*?),\n\s+"conf": (.*?)\n\s+\}', r'{ "value": \1, "conf": \2 }', raw)

    return compacted

import json

def simplify_value_conf(obj):
    if isinstance(obj, dict):
        # If it's a simple {"value": ..., "conf": ...}, return just the value
        if set(obj.keys()) == {"value", "conf"}:
            return obj["value"]
        else:
            return {k: simplify_value_conf(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [simplify_value_conf(item) for item in obj]
    else:
        return obj



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
        print("="*10)
        print(result_data)
        try:
            for idx in range(len(result_data['data'])):
                json_str = result_data['data'][idx]['json_response']
                json_obj = simplify_value_conf(json.loads(json_str))
                compact_json = compact_inner_dicts(json_obj)
                result_data['data'][idx]['json_response'] = json_str
        except:pass

        return jsonify(result_data)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch results: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
