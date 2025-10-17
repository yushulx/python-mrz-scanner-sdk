# Python MRZ Scanner SDK

A Python wrapper for **Machine Readable Zone (MRZ)** detection and parsing using the Dynamsoft Capture Vision SDK. Supports multiple document types including passports, ID cards, visas, and travel documents across **Windows**, **Linux**, and **macOS** platforms.

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/yushulx/python-mrz-scanner-sdk)

> **Note**: This is an unofficial, community-maintained wrapper. For the most reliable and fully-supported solution, consider the [official Dynamsoft Capture Vision Bundle](https://pypi.org/project/dynamsoft-capture-vision-bundle/).

## 🚀 Quick Links

- 📖 [Official Dynamsoft Documentation](https://www.dynamsoft.com/capture-vision/docs/server/programming/python/)
- 🔑 [Get 30-day FREE trial license](https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform)
- 📦 [Official Python Package](https://pypi.org/project/dynamsoft-capture-vision-bundle/)

## 📊 Feature Comparison

| Feature | Community Wrapper | Official Dynamsoft SDK |
|---------|------------------|------------------------|
| **Support** | Community-driven | ✅ Official Dynamsoft support |
| **Documentation** | Enhanced README with examples | ✅ Comprehensive online documentation |
| **API Coverage** | Core MRZ features | ✅ Full API coverage |
| **Updates** | May lag behind | ✅ Latest features first |
| **Testing** | Limited environments | ✅ Thoroughly tested |
| **Ease of Use** | ✅ Simple, intuitive API | More verbose API |
| **Cross-platform** | ✅ Windows, Linux, macOS | ✅ Windows, Linux, macOS |

## 🎯 Supported MRZ Types

- **TD1**: ID cards (3 lines, 30 characters each)
- **TD2**: ID cards (2 lines, 36 characters each) 
- **TD3**: Passports (2 lines, 44 characters each)
- **MRVA/MRVB**: Visas (2 lines, 44/36 characters)

## 🔧 Installation

### Requirements
- **Python 3.x**
- **OpenCV** (for UI display)

    ```bash
    pip install opencv-python
    ```
- Dynamsoft Capture Vision Bundle SDK
  
    ```bash
    pip install dynamsoft-capture-vision-bundle
    ```

### Build from Source

```bash
# Source distribution
python setup.py sdist

# Build wheel
python setup.py bdist_wheel
```

## 🏃‍♂️ Quick Start

### Basic Usage

```python
import mrzscanner

# 1. Initialize license (required)
error_code, error_msg = mrzscanner.initLicense("YOUR_LICENSE_KEY")
if error_code != 0:
    print(f"License error: {error_msg}")
    exit(1)

# 2. Create scanner instance
scanner = mrzscanner.createInstance()

# 3. Detect MRZ from image
results = scanner.decodeFile("passport.jpg")

# 4. Process results
for mrz in results:
    print(f"Document Type: {mrz.doc_type}")
    print(f"Document ID: {mrz.doc_id}")
    print(f"Name: {mrz.given_name} {mrz.surname}")
    print(f"Nationality: {mrz.nationality}")
    print(f"Date of Birth: {mrz.date_of_birth}")
    print(f"Expiry Date: {mrz.date_of_expiry}")
    print("-" * 40)
```

### Real-time Camera Processing

```python
import cv2
import mrzscanner

# Initialize
mrzscanner.initLicense("YOUR_LICENSE_KEY")
scanner = mrzscanner.createInstance()

def on_mrz_detected(mrzs):
    """Callback for real-time MRZ detection"""
    for mrz in mrzs:
        print(f"🔍 Found: {mrz.doc_type} - {mrz.doc_id}")

# Set up async processing
scanner.addAsyncListener(on_mrz_detected)

# Camera stream
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if ret:
        # Queue frame for async processing
        scanner.decodeMatAsync(frame)
        
        cv2.imshow('MRZ Scanner', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
scanner.clearAsyncListener()
```

## 📋 Command Line Usage

![python mrz scanner](https://www.dynamsoft.com/codepool/img/2022/08/python-mrz-scanner.png)

The package includes a command-line tool for quick MRZ scanning:

```bash
# Scan from image file
scanmrz <file-name> -l <license-key>

# Scan with UI display
scanmrz <file-name> -u 1 -l <license-key>
```

## 📚 API Reference

### Core Classes

#### `MrzScanner`

The main class for MRZ detection operations.

```python
scanner = mrzscanner.createInstance()
```

**Synchronous Methods:**

- `decodeFile(file_path: str) -> List[MrzResult]` - Detect MRZ from image file
- `decodeMat(mat: np.ndarray) -> List[MrzResult]` - Detect MRZ from OpenCV matrix
- `decodeBytes(bytes, width, height, stride, pixel_format) -> List[MrzResult]` - Detect MRZ from raw bytes

**Asynchronous Methods:**

- `addAsyncListener(callback: Callable) -> None` - Start async processing with callback
- `decodeMatAsync(mat: np.ndarray) -> None` - Queue OpenCV matrix for async processing
- `decodeBytesAsync(bytes, width, height, stride, pixel_format) -> None` - Queue raw bytes for async processing
- `clearAsyncListener() -> None` - Stop async processing

#### `MrzResult`

Container for detected MRZ information and location.

**Attributes:**
- `doc_type: str` - Document type (e.g., "MRTD_TD3_PASSPORT")
- `doc_id: str` - Document number/ID
- `surname: str` - Primary identifier (surname)
- `given_name: str` - Secondary identifier (given names)
- `nationality: str` - Nationality code (3-letter)
- `issuer: str` - Issuing country/organization
- `gender: str` - Gender ("M", "F", or "<")
- `date_of_birth: str` - Date of birth (YYMMDD)
- `date_of_expiry: str` - Expiry date (YYMMDD)
- `raw_text: List[str]` - Raw MRZ text lines
- `x1, y1, x2, y2, x3, y3, x4, y4: float` - Corner coordinates

**Methods:**
- `to_string() -> str` - Human-readable string representation

### Utility Functions

```python
# License management
error_code, error_msg = mrzscanner.initLicense("LICENSE_KEY")

# Scanner creation
scanner = mrzscanner.createInstance()

# Format conversion
image_data = mrzscanner.convertMat2ImageData(opencv_mat)
image_data = mrzscanner.wrapImageData(width, height, stride, pixel_format, bytes)
```






