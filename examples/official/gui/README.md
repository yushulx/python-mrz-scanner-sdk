# MRZ Scanner GUI

A GUI application for MRZ (Machine Readable Zone) recognition and parsing with portrait detection and cropping, built with PySide6 and Dynamsoft Capture Vision SDK.


https://github.com/user-attachments/assets/1ad49b13-aaf2-44fe-815c-8717d3b60119


## Features

- **Multiple Input Sources**
  - Single image file 
  - Batch processing of image folders
  - Real-time camera capture
  - Drag-and-drop support
  - Clipboard paste support

- **MRZ Recognition & Parsing**
  - Reads MRZ from passports and ID cards (TD1, TD2, TD3 formats)
  - Parses document information:
    - Document type and ID
    - Surname and given name
    - Nationality and issuing country
    - Date of birth and expiry date
    - Gender
  - Displays raw MRZ text and parsed results

- **Portrait Detection**
  - Automatically detects portrait/face region on passports
  - Visual overlay of portrait zone on the image
  - Export processed passport image with document normalization

- **Visual Overlays**
  - Document boundary detection (blue)
  - MRZ location highlighting (green)
  - Portrait zone marking (orange)

## Prerequisites

- Python 3.9+
- Valid [Dynamsoft License](https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform)

## Installation

1. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2. Replace the license key in the code with your own:

    ```python
    error_code, error_message = LicenseManager.init_license(
        "YOUR_LICENSE_KEY_HERE"
    )
    ```

## Usage

Run the application:

```bash
python mrz_scanner_gui.py
```

![Python MRZ Scanner](https://www.dynamsoft.com/codepool/img/2026/02/python-passport-mrz-scanner.png)

### Input Methods

1. **Load File/Folder**: Click "Load File/Folder" button to select an image or folder
2. **Drag and Drop**: Drag image files directly onto the display area
3. **Clipboard Paste**: Copy an image and click "Paste from Clipboard"
4. **Camera**: Select "Camera" source and click "Start Camera" for real-time scanning

### Exporting Passport Image

After processing a passport image, click "Export Passport" to save the normalized document image (requires valid captured result).

## Blog
[How to Build a Python Passport Scanner with Portrait, MRZ and Document Detection](https://www.dynamsoft.com/codepool/python-desktop-mrz-scanner-portrait-detection.html)
