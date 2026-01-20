from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import uuid
from dotenv import load_dotenv
load_dotenv()
from custom_processor import process_document_sample
from Claude_analysis import get_claude_analysis
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_v1 import Document
import boto3
from io import BytesIO
import time

app = Flask(__name__)

# API configuration
API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')

# --- Config ---
BEDROCK_LLM_MODEL_ID = os.getenv("BEDROCK_LLM_MODEL_ID")
GENERATION_LENGTH = 1024  # Max length of generated response
TEMPERATURE = 0.2
TOP_P = 0.95
PDF_BYTES = None  # Placeholder for PDF bytes, if needed
PDF_IMAGES = []  # Placeholder retained but not used; image conversion disabled

bedrock = boto3.client(
    "bedrock-runtime",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
print("Bedrock client created ✅")

with open("message-history.json", "w") as f:
    json.dump({"history":[]}, f, indent=4)

print("Initialized message history file ✅")

sys_prompt = """You are a helpful question-answering chatbot. Use the provided contents of an invoice to answer user queries. 

- If the context does not contain information relevant to the user's query, inform them that you are unable to answer.
- Respond with short answers unless the user explicitly asks for more detail. Only answer questions using the provided context — do not attempt to answer from general knowledge.
- Format all responses using HTML tags (<p>, <b>, <ul>, <li>, etc.). Do NOT use Markdown formatting."""

def get_message_history():
    """Load conversation history from JSON, ensuring correct structure."""
    try:
        with open("message-history.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"history": []}
        write_message_history(data)
    # Normalize structure
    if not isinstance(data, dict):
        data = {"history": []}
    if "history" not in data or not isinstance(data["history"], list):
        data["history"] = []
    return data

def write_message_history(messages):
    with open("message-history.json", "w") as f:
        json.dump(messages, f, indent=4)

def get_text(file_path):
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")
    mime_type = "application/pdf"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        "./g-ocr-creds.json"
    )

    client = documentai.DocumentProcessorServiceClient()
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    raw_document = documentai.RawDocument(content=file_path, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    document: Document = result.document

    ocr_text = """"""

    print("\n=== Started Document OCR PROCESSOR ===")
    for page_index, page in enumerate(document.pages):
        print(f"\nProcessing page {page_index + 1} of {len(document.pages)}")
        for id_, token in enumerate(page.tokens):
            text_anchor = token.layout.text_anchor.text_segments[0]
            start_index = text_anchor.start_index
            end_index = text_anchor.end_index

            text = document.text[start_index:end_index]

            # ocr_text.append(ttext)
            # ocr_conf.append(cconf)
            # ocr_bbox.append(bbbox)
            ocr_text += text

    return ocr_text

# In-memory store for uploaded job data
job_data_store = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/threeway')
def threeway_index():
    return render_template('3_way_index.html')

@app.route('/converse')
def converse_index():
    return render_template('converse.html')

@app.route('/addpdf', methods=['POST'])
def add_pdf():
    global PDF_BYTES, PDF_IMAGES
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or len(uploaded_files) == 0:
        return jsonify({"error": "No files provided"}), 400
    
    try:
        file = uploaded_files[0]  # Assuming only one file is uploaded
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        if file.filename.lower().endswith('.pdf'):
            print("Processing PDF: ", file.filename)
            stream = BytesIO(file.read())
            PDF_BYTES = stream.getvalue()
            # Image conversion disabled; using OCR text only
            # PDF_IMAGES = convert_from_bytes(PDF_BYTES, dpi=200)
        else:
            return jsonify({"error": "Unsupported file-type"}), 400
        # Reset conversation history when a new document is uploaded
        write_message_history({"history": []})
        # Success response
        return jsonify({"message": "Document uploaded successfully", "filename": file.filename}), 200
    except Exception as e:
        print(f"Error processing document: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/fetchreponse', methods=['POST'])
def fetch_response():
    global PDF_BYTES, PDF_IMAGES
    data = request.json
    query = data.get('query', None)
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    if not isinstance(query, str):
        return jsonify({"error": "Query must be a string"}), 400
    
    query = query.strip()

    print("Received query: ", query)

    # Check if initialization completed
    if bedrock is None:
        return jsonify({"error": "System not fully initialized. Please try again."}), 503
    
    history_data = get_message_history()
    history_list = history_data.get("history", [])
    # If this is the first interaction and no PDF loaded, require upload
    if not PDF_BYTES:
        return jsonify({"error": "Please upload a PDF before asking a question."}), 400

    # Build messages for the model: prior history + new user query
    messages = []
    for item in history_list:
        role = item.get("role")
        text = item.get("content", "")
        if role in ("user", "assistant") and isinstance(text, str):
            messages.append({"role": role, "content": [{"text": text}]})

    # First user prompt after upload includes invoice context
    user_parts = []
    used_context_text = None
    if len(history_list) == 0 and PDF_BYTES:
        used_context_text = "### Invoice content:\n" + get_text(PDF_BYTES)
        user_parts.append({"text": used_context_text})
    user_parts.append({"text": query})
    messages.append({"role": "user", "content": user_parts})

    print("Starting generation...")
    g_st = time.time()
    model_response = bedrock.converse(
        modelId=BEDROCK_LLM_MODEL_ID,
        messages=messages,
        system=[{"text": sys_prompt}],
        inferenceConfig={
            'maxTokens': GENERATION_LENGTH,
            'temperature': TEMPERATURE,
            'topP': TOP_P,
        },
    )
    response = model_response["output"]["message"]["content"][0]["text"]
    g_time = time.time() - g_st

    print("Response created, took "+str(g_time)+" seconds.")
    
    print("\n\nModel reponse:\n",response)

    # Append to and persist history
    # If this is the first interaction after a PDF upload, also persist the
    # extracted invoice text as a separate message so future queries retain context.
    updated_entries = []
    if used_context_text is not None:
        updated_entries.append({"role": "user", "content": used_context_text})
    updated_entries.extend([
        {"role": "user", "content": query},
        {"role": "assistant", "content": response}
    ])
    updated_history = history_list + updated_entries
    write_message_history({"history": updated_history})

    return jsonify({"message": response}), 200

@app.post("/api/process-documents")
def process_documents():
    # Ensure JSON parsing and content type correctness
    try:
        data = request.get_json(force=False, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400

    if data is None:
        return (
            jsonify(
                {
                    "error": "Request body must be JSON with Content-Type: application/json."
                }
            ),
            400,
        )

    # Validate top-level structure
    if "masterDocument" not in data or "additionalDocuments" not in data:
        return (
            jsonify(
                {
                    "error": "Payload must include 'masterDocument' and 'additionalDocuments'."
                }
            ),
            400,
        )

    master = data["masterDocument"]
    additional = data["additionalDocuments"]

    if master is not None and not isinstance(master, dict):
        return jsonify({"error": "'masterDocument' must be an object or null."}), 400
    if not isinstance(additional, list):
        return jsonify({"error": "'additionalDocuments' must be an array."}), 400

    # Calling GCP custom processor for fetcing the json
    master_file = master["bytes"]
    master_json = {}
    # master_json[master["name"]] = process_document_sample(pdf_bytes=master_file)
    master_json[master["name"]] = get_text(file_path=master_file)

    doc_json = {}
    futures = {}
    max_workers = min(8, max(1, len(additional)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for doc in additional:
            name = doc["name"]
            doc_bytes = doc["bytes"]
            # fut = executor.submit(process_document_sample, pdf_bytes=doc_bytes)
            fut = executor.submit(get_text, file_path=doc_bytes)
            futures[fut] = name

            # json_for_doc = process_document_sample(pdf_bytes=doc_bytes)
            json_for_doc = get_text(file_path=doc_bytes)
            doc_json[name] = json_for_doc

        for fut in as_completed(futures):
            name = futures[fut]
            try:
                result = fut.result()
                doc_json[name] = result
            except Exception as e:
                # Decide policy: fail whole request or mark this one as error
                doc_json[name] = {"error": str(e)}

    # GET CLAUDE ANALYSIS
    markdown_text = get_claude_analysis(masterJSON=master_json, docJSON=doc_json)
    # html_text = markdown.markdown(markdown_text)
    html_text = markdown_text

    return (
        jsonify(
            {
                "status": "ok",
                "html": html_text,
                "markdown": markdown_text,
            }
        ),
        200,
    )

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
        'payload': payload,
        'job_id': job_id
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
            for idx in range(len(result_data.get('data', []))):
                json_str = result_data['data'][idx].get('json_response')
                if not json_str:
                    continue
                json_obj = simplify_value_conf(json.loads(json_str))
                # Provide simplified JSON string back to client
                result_data['data'][idx]['json_response'] = json.dumps(json_obj, ensure_ascii=False)
        except Exception:
            # If simplifying fails for any reason, return the original payload
            pass

        return jsonify(result_data)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch results: {str(e)}'}), 500

@app.route('/clear', methods=['POST'])
def clear():
    global PDF_BYTES, PDF_IMAGES
    PDF_BYTES = None
    PDF_IMAGES = []
    
    print("Cleared all stored data.")
    # Also clear server-side message history
    write_message_history({"history": []})

    return jsonify({"message": "All data cleared successfully"}), 200

# Backwards compatibility: If a client still calls /reset_history,
# treat it the same as a full clear to avoid divergent behavior.
@app.route('/reset_history', methods=['POST'])
def reset_history():
    return clear()

if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True, port=8000)
