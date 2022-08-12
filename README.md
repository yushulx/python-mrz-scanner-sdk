# Python Extension: MRZ Scanner SDK 
The project is a Python-C++ binding of [Dynamsoft Label Recognizer](https://www.dynamsoft.com/label-recognition/overview/). It aims to help developers build **Python MRZ scanner** apps on Windows and Linux.

## License Key
Get a [30-day FREE trial license](https://www.dynamsoft.com/customer/license/trialLicense/?product=dlr) to activate the SDK.


## Supported Python Edition
* Python 3.x

## Install Dependencies
```bash 
pip install mrz opencv-python
```

## Command-line Usage
```bash 
$ scanmrz <file-name> -l <license-key>

# Show the image with OpenCV
$ scanmrz <file-name> -u 1 -l <license-key>
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
mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

# initialize mrz scanner
scanner = mrzscanner.createInstance()

# load MRZ model
scanner.loadModel(mrzscanner.get_model_path())

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

## Methods
- `mrzscanner.initLicense('YOUR-LICENSE-KEY')` # set the license globally
    
    ```python
    mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")
    ```

- `mrzscanner.createInstance()` # create a MRZ scanner instance
    
    ```python
    scanner = mrzscanner.createInstance()
    ```
- `scanner.loadModel(<model configuration file>)` # load MRZ model
    
    ```python
    scanner.loadModel(mrzscanner.get_model_path())
    ```
- `decodeFile(<image file>)` # recognize MRZ from an image file

    ```python
    results = scanner.decodeFile(<image-file>)
    for result in results:
        print(result.text)
    ```
- `decodeMat(<opencv mat data>)` # recognize MRZ from OpenCV Mat
    ```python
    import cv2
    image = cv2.imread(<image-file>)
    results = scanner.decodeMat(image)
    for result in results:
        print(result.text)
    ```
- `addAsyncListener(callback function)` # start a native thread and register a Python function for receiving the MRZ recognition results
- `decodeMatAsync(<opencv mat data>)` # recognize MRZ from OpenCV Mat asynchronously
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


