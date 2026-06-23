"""
MRZ Scanner REST API for Digital KYC Systems

A Flask-based REST API that scans Machine-Readable Zone (MRZ) data from
passport and ID card images using Dynamsoft Capture Vision SDK.
Returns structured JSON ready for KYC (Know Your Customer) system integration
and serves a browser-based visual demo UI.

Usage:
    python app.py [--port PORT] [--host HOST]

Endpoints:
    GET  /                 - Visual web UI
    POST /api/scan-mrz     - Upload an image file and receive parsed MRZ data
    GET  /api/health       - Health check endpoint
"""

import argparse
import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from dynamsoft_capture_vision_bundle import (
    LicenseManager,
    CaptureVisionRouter,
    EnumErrorCode,
    EnumValidationStatus,
    ParsedResultItem,
    FileImageTag,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}
LICENSE_KEY = os.environ.get(
    "DLS_LICENSE_KEY",
    "DLS2eyJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSJ9",
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TEST_IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")
os.makedirs(TEST_IMAGE_FOLDER, exist_ok=True)

STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path="/static")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------------------------------------------------------------------
# SDK initialization
# ---------------------------------------------------------------------------
router = None


def init_sdk(license_key: str) -> CaptureVisionRouter:
    """Initialize the Dynamsoft Capture Vision SDK and return a router instance."""
    error_code, error_msg = LicenseManager.init_license(license_key)
    if error_code != EnumErrorCode.EC_OK and error_code != EnumErrorCode.EC_LICENSE_WARNING:
        raise RuntimeError(f"License initialization failed: {error_msg}")

    router_instance = CaptureVisionRouter()
    return router_instance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_mrz_result(item: ParsedResultItem) -> dict:
    """Extract structured MRZ data from a ParsedResultItem into a dict."""
    doc_type = item.get_code_type() or ""

    def field_value(name: str) -> str | None:
        """Safely get a validated field value."""
        val = item.get_field_value(name)
        if val is not None:
            status = item.get_field_validation_status(name)
            if status != EnumValidationStatus.VS_FAILED:
                return val
        return None

    raw_lines = []
    for line_key in ("line1", "line2", "line3"):
        line = item.get_field_value(line_key)
        if line:
            status = item.get_field_validation_status(line_key)
            raw_lines.append(
                {
                    "text": line,
                    "validated": status != EnumValidationStatus.VS_FAILED,
                }
            )

    doc_id = field_value("passportNumber") or field_value("documentNumber")

    return {
        "document_type": doc_type,
        "document_number": doc_id,
        "surname": field_value("primaryIdentifier"),
        "given_name": field_value("secondaryIdentifier"),
        "nationality": field_value("nationality"),
        "issuing_country": field_value("issuingState"),
        "gender": field_value("sex"),
        "date_of_birth": field_value("dateOfBirth"),
        "date_of_expiry": field_value("dateOfExpiry"),
        "raw_mrz_lines": raw_lines,
    }


def scan_image(file_path: str) -> list[dict]:
    """Scan an image file for MRZ data and return parsed results."""
    result = router.capture(file_path, "ReadPassportAndId")

    if result.get_error_code() != EnumErrorCode.EC_OK:
        raise RuntimeError(f"Capture failed: {result.get_error_string()}")

    parsed_result = result.get_parsed_result()
    if parsed_result is None or len(parsed_result.get_items()) == 0:
        return []

    items = parsed_result.get_items()
    parsed = []
    for item in items:
        parsed.append(parse_mrz_result(item))

    return parsed


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    """Serve the visual web UI."""
    return send_from_directory(STATIC_FOLDER, "index.html")


@app.route("/test_images/<path:filename>", methods=["GET"])
def serve_test_image(filename):
    """Serve built-in sample document images used by the UI demo."""
    return send_from_directory(TEST_IMAGE_FOLDER, filename)


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return jsonify(
        {
            "status": "healthy",
            "service": "mrz-scanner-api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )


@app.route("/api/scan-mrz", methods=["POST"])
def scan_mrz():
    """
    Scan MRZ from an uploaded image.

    Request: multipart/form-data with field 'image'
    Response: JSON with parsed MRZ fields suitable for KYC integration
    """
    # Validate file presence
    if "image" not in request.files:
        return jsonify({"error": "No 'image' file provided"}), 400

    file = request.files["image"]
    if file.filename == "" or file.filename is None:
        return jsonify({"error": "Empty file name"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {
                "error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            }
        ), 400

    # Save uploaded file
    filename = secure_filename(file.filename or "upload.jpg")
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    try:
        mrz_data = scan_image(file_path)
        return jsonify(
            {
                "success": True,
                "filename": filename,
                "mrz_zones_found": len(mrz_data),
                "results": mrz_data,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MRZ Scanner REST API for Digital KYC Systems"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to listen on (default: 5000)"
    )
    parser.add_argument(
        "--license-key",
        default=LICENSE_KEY,
        help="Dynamsoft license key (or set DLS_LICENSE_KEY env var)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable Flask debug mode"
    )
    args = parser.parse_args()

    print(f"MRZ Scanner REST API v1.0")
    print(f"Initializing Dynamsoft Capture Vision SDK ...")
    try:
        router = init_sdk(args.license_key)
        print("SDK initialized successfully.")
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Endpoints:")
    print(f"  GET  /              - Visual web UI")
    print(f"  POST /api/scan-mrz  - Upload image for MRZ scanning")
    print(f"  GET  /api/health    - Health check")
    app.run(host=args.host, port=args.port, debug=args.debug)
