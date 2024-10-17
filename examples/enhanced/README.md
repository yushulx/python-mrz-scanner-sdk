## MRZ Detection by Orientation Correction
The sample demonstrates how to enhance MRZ detection by correcting the orientation of the input image. 

## Installation

```bash
pip install mrz-scanner-sdk document-scanner-sdk dlib mediapipe retina-face opencv-python
```

## Usage
1. Request a free trial license from [here](https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform).

2. Set the license key:

    ```python
    defaultLicense = "LICENSE-KEY"
    ```
3. Run the script:

    ```bash
    python app.py passport.jpg # without face detection
    python combine.py passport_180.jpg # with face detection
    ```

    ![passport-mrz-detection-any-orientation](https://github.com/yushulx/python-mrz-scanner-sdk/assets/2202306/d9e8e185-01a5-4123-92c7-8f83e8d51bc3)
