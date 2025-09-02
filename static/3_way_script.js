//  Updated data structures to store files as bytes
let masterDocument = null; // Single document with bytes
let additionalDocuments = []; // Array of documents with bytes

// File size limit (20MB)
const MAX_FILE_SIZE = 20 * 1024 * 1024;

// Initialize drag and drop functionality
function initializeDragAndDrop() {
    const masterUploadArea = document.getElementById('masterUploadArea');
    const additionalUploadArea = document.getElementById('additionalUploadArea');
    const masterFileInput = document.getElementById('masterFileInput');
    const additionalFileInput = document.getElementById('additionalFileInput');

    // Master document drag and drop
    setupDragAndDrop(masterUploadArea, masterFileInput, 'master');

    // Additional documents drag and drop
    setupDragAndDrop(additionalUploadArea, additionalFileInput, 'additional');

    // ✅ NEW: click anywhere in the upload area to trigger file picker
    masterUploadArea.addEventListener('click', () => {
        masterFileInput.click();
    });

    additionalUploadArea.addEventListener('click', () => {
        additionalFileInput.click();
    });

    // File input change events
    masterFileInput.addEventListener('change', (e) => handleFileSelect(e, 'master'));
    additionalFileInput.addEventListener('change', (e) => handleFileSelect(e, 'additional'));
}

function setupDragAndDrop(uploadArea, fileInput, type) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
    });

    uploadArea.addEventListener('drop', (e) => handleDrop(e, type), false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e, type) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files, type);
}

function handleFileSelect(e, type) {
    const files = e.target.files;
    handleFiles(files, type);
}

//  Updated to handle file conversion to bytes
async function handleFiles(files, type) {
    for (let file of files) {
        if (validateFile(file)) {
            try {
                const bytes = await fileToBytes(file);
                const fileData = {
                    name: file.name,
                    size: file.size,
                    type: file.type,
                    bytes: bytes
                };

                if (type === 'master') {
                    masterDocument = fileData;
                    //console.log(masterDocument)
                    break; // Only one master document allowed
                } else {
                    additionalDocuments.push(fileData);
                    //console.log(additionalDocuments)
                }
            } catch (error) {
                console.error('Error converting file to bytes:', error);
                showStatus('Error processing file: ' + file.name, 'error');
            }
        }
    }
    updateFileDisplay();
    updateProcessButton();
}

//  Added function to convert file to bytes
function fileToBytes(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsArrayBuffer(file);
    });
}

function validateFile(file) {
    const allowedTypes = [
        'application/pdf',
        'image/gif',
        'image/tiff',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/bmp',
        'image/webp'
    ];

    if (!allowedTypes.includes(file.type)) {
        showStatus('Invalid file type. Please upload supported formats only.', 'error');
        return false;
    }

    if (file.size > MAX_FILE_SIZE) {
        showStatus('File size exceeds 20MB limit.', 'error');
        return false;
    }

    return true;
}

//  Updated file display functions
function updateFileDisplay() {
    displayMasterFile();
    displayAdditionalFiles();
}

function displayMasterFile() {
    const container = document.getElementById('masterFiles');
    container.innerHTML = '';

    if (masterDocument) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
                    <div class="file-info">
                        <svg class="file-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <div class="file-details">
                            <div class="file-name">${masterDocument.name}</div>
                            <div class="file-size">${formatFileSize(masterDocument.size)}</div>
                        </div>
                    </div>
                    <button class="remove-file" onclick="removeMasterFile()" title="Remove file">×</button>
                `;
        container.appendChild(fileItem);
    }
}

function displayAdditionalFiles() {
    const container = document.getElementById('additionalFiles');
    container.innerHTML = '';

    additionalDocuments.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
                    <div class="file-info">
                        <svg class="file-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <div class="file-details">
                            <div class="file-name">${file.name}</div>
                            <div class="file-size">${formatFileSize(file.size)}</div>
                        </div>
                    </div>
                    <button class="remove-file" onclick="removeAdditionalFile(${index})" title="Remove file">×</button>
                `;
        container.appendChild(fileItem);
    });
}

//  Updated remove functions
function removeMasterFile() {
    masterDocument = null;
    updateFileDisplay();
    updateProcessButton();
}

function removeAdditionalFile(index) {
    additionalDocuments.splice(index, 1);
    updateFileDisplay();
    updateProcessButton();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateProcessButton() {
    const processBtn = document.getElementById('processBtn');
    const hasFiles = masterDocument !== null || additionalDocuments.length > 0;
    processBtn.disabled = !hasFiles;
}

function showStatus(message, type) {
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }
}

//  Updated process function to work with bytes data
async function processDocuments() {
    const processBtn = document.getElementById('processBtn');
    const originalText = processBtn.innerHTML;

    // Show loading state
    processBtn.innerHTML = '<span class="loading"></span>Processing...';
    processBtn.disabled = true;

    try {
        // Prepare data with bytes
        const documentData = {
            masterDocument: masterDocument,
            additionalDocuments: additionalDocuments,
            timestamp: new Date().toISOString()
        };

        console.log('Documents ready for processing:', {
            masterDocument: masterDocument ? {
                name: masterDocument.name,
                size: masterDocument.size,
                type: masterDocument.type,
                bytesLength: masterDocument.bytes.byteLength
            } : null,
            additionalDocuments: additionalDocuments.map(doc => ({
                name: doc.name,
                size: doc.size,
                type: doc.type,
                bytesLength: doc.bytes.byteLength
            }))
        });

        // Convert bytes to base64 for transmission (if needed)
        const processData = {
            masterDocument: masterDocument ? {
                ...masterDocument,
                bytes: arrayBufferToBase64(masterDocument.bytes)
            } : null,
            additionalDocuments: additionalDocuments.map(doc => ({
                ...doc,
                bytes: arrayBufferToBase64(doc.bytes)
            }))
        };

        // Send to backend (replace with your actual endpoint)
        const response = await fetch('/api/process-documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(processData)
        });

        if (response.ok) {
            const result = await response.json();
            showStatus('Documents processed successfully!', 'success');
            console.log('Processing result:', result);

            if (result.html) {
                // Find Additional Documents container
                const additionalSection = document.getElementById('additionalFiles');
                let outputDiv = document.getElementById('analysisResults');

                if (!outputDiv) {
                    outputDiv = document.createElement('div');
                    outputDiv.id = 'analysisResults';
                    outputDiv.style.marginTop = '20px';
                    outputDiv.style.padding = '10px';
                    outputDiv.style.paddingLeft = '25px';
                    outputDiv.style.border = '1px solid #3b82f6';
                    outputDiv.style.backgroundColor = '#fafafa';
                    // Insert after the additional files section
                    additionalSection.parentNode.insertBefore(outputDiv, additionalSection.nextSibling);
                }

                outputDiv.innerHTML = result.html;
            }
        } else {
            throw new Error('Failed to process documents');
        }
    } catch (error) {
        console.error('Error processing documents:', error);
        showStatus('Error processing documents. Please try again.', 'error');
    } finally {
        // Reset button
        processBtn.innerHTML = originalText;
        processBtn.disabled = masterDocument === null && additionalDocuments.length === 0;
    }
}

//  Added helper function to convert ArrayBuffer to base64
function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}

// Initialize the application
document.addEventListener('DOMContentLoaded', initializeDragAndDrop);