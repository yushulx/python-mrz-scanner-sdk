/**
 * Frontend logic for the MRZ Scanner KYC web UI.
 * Handles drag-and-drop upload, preview, API calls, and result rendering.
 */

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const previewWrapper = document.getElementById('previewWrapper');
const imagePreview = document.getElementById('imagePreview');
const btnRemove = document.getElementById('btnRemove');
const btnScan = document.getElementById('btnScan');
const btnLoadSample = document.getElementById('btnLoadSample');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const statusText = document.getElementById('statusText');
const resultsCard = document.getElementById('resultsCard');
const resultsEmpty = document.getElementById('resultsEmpty');
const resultsBody = document.getElementById('resultsBody');
const metaZones = document.getElementById('metaZones');
const metaFilename = document.getElementById('metaFilename');

let currentFile = null;

const sampleImages = [
    '/test_images/passport_eriksson.png',
    '/test_images/id_card_smith.png',
    '/test_images/mrz_strip_taylor.png'
];

// ---------------------------------------------------------------------------
// Upload handlers
// ---------------------------------------------------------------------------

function loadFile(file) {
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        uploadPlaceholder.classList.add('hidden');
        previewWrapper.classList.remove('hidden');
        btnScan.disabled = false;
        statusText.textContent = 'Image ready. Click “Scan MRZ” to extract data.';
        statusText.className = 'status info';
    };
    reader.readAsDataURL(file);
}

function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        showStatus('Please upload a valid image file (PNG, JPG, BMP, TIFF, WEBP).', 'error');
        return;
    }

    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
        showStatus('File is too large. Maximum size is 16 MB.', 'error');
        return;
    }

    currentFile = file;
    loadFile(file);
}

function removeFile() {
    currentFile = null;
    fileInput.value = '';
    imagePreview.src = '';
    uploadPlaceholder.classList.remove('hidden');
    previewWrapper.classList.add('hidden');
    btnScan.disabled = true;
    resultsCard.classList.add('hidden');
    showStatus('', '');
}

function showStatus(message, type) {
    statusText.textContent = message;
    statusText.className = 'status' + (type ? ' ' + type : '');
}

function setProgress(percent) {
    progressFill.style.width = percent + '%';
    if (percent > 0 && percent < 100) {
        progressBar.classList.remove('hidden');
    } else if (percent === 100) {
        setTimeout(() => progressBar.classList.add('hidden'), 400);
    } else {
        progressBar.classList.add('hidden');
    }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
    }
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFile(e.dataTransfer.files[0]);
    }
});

btnRemove.addEventListener('click', (e) => {
    e.stopPropagation();
    removeFile();
});

btnLoadSample.addEventListener('click', async () => {
    const samplePath = sampleImages[Math.floor(Math.random() * sampleImages.length)];
    try {
        const response = await fetch(samplePath);
        if (!response.ok) throw new Error('Could not load sample image');
        const blob = await response.blob();
        const filename = samplePath.split('/').pop();
        const file = new File([blob], filename, { type: blob.type });
        handleFile(file);
    } catch (err) {
        showStatus('Error loading sample: ' + err.message, 'error');
    }
});

btnScan.addEventListener('click', async () => {
    if (!currentFile) {
        showStatus('Please upload an image first.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('image', currentFile);

    setProgress(40);
    showStatus('Scanning MRZ data...', 'info');
    btnScan.disabled = true;

    try {
        const response = await fetch('/api/scan-mrz', {
            method: 'POST',
            body: formData,
        });

        setProgress(80);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Server returned ${response.status}`);
        }

        const data = await response.json();
        setProgress(100);
        renderResults(data);
        showStatus('MRZ scan complete.', 'success');
    } catch (err) {
        showStatus('Scan failed: ' + err.message, 'error');
        setProgress(0);
    } finally {
        btnScan.disabled = false;
    }
});

// ---------------------------------------------------------------------------
// Result rendering
// ---------------------------------------------------------------------------

function setField(elementId, value, validated) {
    const el = document.getElementById(elementId);
    const card = el.closest('.field-card');
    el.textContent = value || '—';

    card.classList.remove('unverified', 'missing');
    if (!value) {
        card.classList.add('missing');
    } else if (validated === false) {
        card.classList.add('unverified');
    }
}

function renderResults(data) {
    resultsCard.classList.remove('hidden');
    metaFilename.textContent = data.filename || '';

    const results = data.results || [];
    metaZones.textContent = `MRZ zones found: ${results.length}`;

    if (results.length === 0) {
        resultsEmpty.classList.remove('hidden');
        resultsBody.classList.add('hidden');
        return;
    }

    resultsEmpty.classList.add('hidden');
    resultsBody.classList.remove('hidden');

    const item = results[0];
    const rawLines = item.raw_mrz_lines || [];

    setField('fDocType', item.document_type);
    setField('fDocNumber', item.document_number, rawLines.length > 1 ? rawLines[1].validated : true);
    setField('fSurname', item.surname);
    setField('fGivenName', item.given_name);
    setField('fNationality', item.nationality);
    setField('fIssuer', item.issuing_country);
    setField('fGender', item.gender);
    setField('fDob', item.date_of_birth, rawLines.length > 1 ? rawLines[1].validated : true);
    setField('fExpiry', item.date_of_expiry, rawLines.length > 1 ? rawLines[1].validated : true);

    renderRawLine('rawLine1', rawLines[0]);
    renderRawLine('rawLine2', rawLines[1]);
    renderRawLine('rawLine3', rawLines[2]);
}

function renderRawLine(elementId, lineData) {
    const el = document.getElementById(elementId);
    if (!lineData) {
        el.classList.add('hidden');
        return;
    }
    el.classList.remove('hidden');
    el.textContent = lineData.text || '';
    el.classList.remove('valid', 'invalid');
    el.classList.add(lineData.validated ? 'valid' : 'invalid');
}
