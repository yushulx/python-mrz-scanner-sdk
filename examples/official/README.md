# Dynamsoft Capture Vision SDK for MRZ Detection
This repository contains example code for using the Dynamsoft Capture Vision SDK to detect **Machine Readable Zone (MRZ)** in passport, ID card and Visa images.

https://github.com/user-attachments/assets/2bebd2d3-d01b-467d-b395-f5925c75f7f2


## Prerequisites
- [Dynamsoft Capture Vision Trial License](https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform)
    
    ```python
    errorCode, errorMsg = LicenseManager.init_license(
        "LICENSE-KEY")
    ```
    
- SDK Installation
 
    ```bash
    pip install -r requirements.txt
    ```

## Supported Platforms
- Windows
- Linux
- macOS
    
  
## Examples
- [camera.py](./camera.py): Detect MRZ from a camera video stream.
- [file.py](./file.py): Detect MRZ from an image file and display the results in a window.
