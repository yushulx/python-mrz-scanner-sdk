# Python MRZ Scanner SDK
This project provides a Python-C++ binding for the [Dynamsoft Label Recognizer v2.x](https://www.dynamsoft.com/label-recognition/overview/), allowing developers to **build MRZ (Machine Readable Zone)** scanner applications on both **Windows** and **Linux** platforms using Python.

## License Key
To activate the SDK, obtain a [30-day FREE trial license](https://www.dynamsoft.com/customer/license/trialLicense/?product=dlr).


## Supported Python Versions
* Python 3.x

## Installation
Install the required dependencies:
```bash 
pip install mrz opencv-python
```

## Command-line Usage
- Scan MRZ from an image file:
    ```bash 
    scanmrz <file-name> -l <license-key>
    ```
- Scan MRZ from a webcam:
    ```bash 
    scanmrz <file-name> -u 1 -l <license-key>
    ```

    ![python mrz scanner](https://www.dynamsoft.com/codepool/img/2022/08/python-mrz-scanner.png)

## Quick Start
```python
import mrzscanner
from mrz.checker.td1 import TD1CodeChecker
from mrz.checker.td2 import TD2CodeChecker
from mrz.checker.td3 import TD3CodeChecker
from mrz.checker.mrva import MRVACodeChecker
from mrz.checker.mrvb import MRVBCodeChecker

def check(lines):
    try:
        td1_check = TD1CodeChecker(lines)
        if bool(td1_check):
            return "TD1", td1_check.fields()
    except Exception as err:
        pass
    
    try:
        td2_check = TD2CodeChecker(lines)
        if bool(td2_check):
            return "TD2", td2_check.fields()
    except Exception as err:
        pass
    
    try:
        td3_check = TD3CodeChecker(lines)
        if bool(td3_check):
            return "TD3", td3_check.fields()
    except Exception as err:
        pass
    
    try:
        mrva_check = MRVACodeChecker(lines)
        if bool(mrva_check):
            return "MRVA", mrva_check.fields()
    except Exception as err:
        pass
    
    try:
        mrvb_check = MRVBCodeChecker(lines)
        if bool(mrvb_check):
            return "MRVB", mrvb_check.fields()
    except Exception as err:
        pass
    
    return 'No valid MRZ information found'

# set license
mrzscanner.initLicense("LICENSE-KEY")

# initialize mrz scanner
scanner = mrzscanner.createInstance()

# load MRZ model
scanner.loadModel(mrzscanner.load_settings())

print('')
# decodeFile()
s = ""
results = scanner.decodeFile("images/1.png")
for result in results:
    print(result.text)
    s += result.text + '\n'
print('')
print(check(s[:-1]))
print('')
```

## API Reference
- `mrzscanner.initLicense('YOUR-LICENSE-KEY')`: Initialize the SDK with your license key.
    
    ```python
    mrzscanner.initLicense("LICENSE-KEY")
    ```

- `mrzscanner.createInstance()`: Create an instance of the MRZ scanner.
    
    ```python
    scanner = mrzscanner.createInstance()
    ```
- `scanner.loadModel(<model configuration file>)`: Load the MRZ model configuration.
    
    ```python
    scanner.loadModel(mrzscanner.load_settings())
    ```
- `decodeFile(<image file>)`: Recognize MRZ from an image file.

    ```python
    results = scanner.decodeFile(<image-file>)
    for result in results:
        print(result.text)
    ```
- `decodeMat(<opencv mat data>)`: Recognize MRZ from an OpenCV Mat.
    ```python
    import cv2
    image = cv2.imread(<image-file>)
    results = scanner.decodeMat(image)
    for result in results:
        print(result.text)
    ```
- `addAsyncListener(callback function)`: Register a callback function to receive MRZ recognition results asynchronously.
- `decodeMatAsync(<opencv mat data>)`: Recognize MRZ from OpenCV Mat asynchronously.
    ```python
    def callback(results):
        s = ""
        for result in results:
            print(result.text)
            s += result.text + '\n'
    
        print('')
        print(check(s[:-1]))
    
    import cv2
    image = cv2.imread(<image-file>)
    scanner.addAsyncListener(callback)
    for i in range (2):
        scanner.decodeMatAsync(image)
        sleep(1)
    ```

## How to Build the Python MRZ Scanner Extension
- Create a source distribution:
    
    ```bash
    python setup.py sdist
    ```

- setuptools:
    
    ```bash
    python setup.py build
    python setup.py develop 
    ```
- Build wheel:
    
    ```bash
    pip wheel . --verbose
    # Or
    python setup.py bdist_wheel
    ```


