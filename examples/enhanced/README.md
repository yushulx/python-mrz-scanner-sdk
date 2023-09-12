## MRZ Detection by Orientation Correction
The sample demonstrates how to enhance MRZ detection by correcting the orientation of the input image. 

## Installation

```bash
pip install mrz-scanner-sdk document-scanner-sdk dlib mediapipe retina-face opencv-python
```

## Usage
1. Request a free trial license from [here](https://www.dynamsoft.com/customer/license/trialLicense?product=dlr&package=c_cpp).

2. Set the license key:

    ```python
    defaultLicense = "LICENSE-KEY"
    ```
3. Run the script:

    ```bash
    python app.py passport.jpg # without face detection
    python combine.py passport_180.jpg # with face detection
    ```