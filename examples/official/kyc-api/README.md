# MRZ Scanner REST API for Digital KYC

A Flask-based REST API that scans Machine-Readable Zone (MRZ) data from passport and ID card images using the Dynamsoft Capture Vision SDK. It returns structured JSON ready for KYC (Know Your Customer) system integration and ships with a browser-based visual demo UI.

## Features

- REST endpoint for uploading an image and receiving parsed MRZ fields
- Supports TD1 (ID cards), TD2 (ID cards), TD3 (passports), MRVA/MRVB (visas)
- Field-level validation status from the SDK (check digits, structure)
- CORS-enabled for cross-origin frontend consumption
- Built-in drag-and-drop web UI for manual testing
- Health check endpoint for monitoring and load balancers

## Requirements

- Python 3.x
- A Dynamsoft Capture Vision license key (set `DLS_LICENSE_KEY` or pass `--license-key`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

Default server: `http://127.0.0.1:5000`

CLI options:

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `5000` | Port to listen on |
| `--license-key` | env `DLS_LICENSE_KEY` | Dynamsoft license key |
| `--debug` | off | Enable Flask debug mode |

## API Endpoints

### `GET /`

Returns the visual web UI (`static/index.html`) for interactive testing.

### `POST /api/scan-mrz`

Upload an image and receive parsed MRZ fields.

Request: `multipart/form-data` with field name `image`.

Allowed types: `png`, `jpg`, `jpeg`, `bmp`, `tiff`, `tif`, `webp`. Max size: 16 MB.

Example:

```bash
curl -X POST -F "image=@passport.png" http://127.0.0.1:5000/api/scan-mrz
```

Response:

```json
{
  "success": true,
  "filename": "passport.png",
  "mrz_zones_found": 1,
  "results": [
    {
      "document_type": "PASSPORT",
      "document_number": "P12345678",
      "surname": "ERIKSSON",
      "given_name": "ANNA MARIA",
      "nationality": "UTO",
      "issuing_country": "UTO",
      "gender": "F",
      "date_of_birth": "1985-04-12",
      "date_of_expiry": "2030-04-11",
      "raw_mrz_lines": [
        { "text": "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<<", "validated": true },
        { "text": "P12345678UTO8504124F3004117<<<<<<<<<<<<<<<<<6", "validated": true }
      ]
    }
  ]
}
```

### `GET /api/health`

Health check for liveness probes.

```json
{
  "status": "healthy",
  "service": "mrz-scanner-api",
  "timestamp": "2026-06-23T12:00:00Z"
}
```

### `GET /test_images/<filename>`

Serves built-in sample document images used by the UI's "Load Sample" button.

## Response Fields

| Field | Source | Notes |
|-------|--------|-------|
| `document_type` | `passportNumber` / `documentNumber` | Passport or ID-specific type |
| `document_number` | `primaryIdentifier` | Surname |
| `surname` | `secondaryIdentifier` | Given name |
| `given_name` | `nationality` | 3-letter code |
| `nationality` | `issuingState` | 3-letter code |
| `issuing_country` | `sex` | `M`, `F`, or `<` |
| `gender` | `dateOfBirth` | ISO date when valid |
| `date_of_birth` | `dateOfExpiry` | ISO date when valid |
| `date_of_expiry` | `line1` / `line2` / `line3` | Raw MRZ lines with per-line validation flag |
| `raw_mrz_lines` | — | One entry per detected MRZ zone |

Fields are omitted (returned as `null`) when the SDK reports a failed validation status.

## Integration Notes

- Uploaded files are written to `uploads/` and deleted after each request.
- CORS is enabled for `/api/*` from any origin — restrict in production.
- The SDK is initialized once at startup. An invalid license key causes the process to exit.

## License

A trial license key is embedded by default for quick testing. For production use, request a 30-day free trial license at <https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform> and supply it via the `DLS_LICENSE_KEY` environment variable or the `--license-key` flag. The Dynamsoft Capture Vision SDK is used under its own license terms.