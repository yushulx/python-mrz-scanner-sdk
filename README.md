# Python Extension: MRZ Scanner SDK 
The project is Python-C++ bindings of [Dynamsoft Label Recognizer](https://www.dynamsoft.com/label-recognition/overview/). It aims to help developers build **Python MRZ scanner** apps on Windows and Linux.

## License Key
Get a [30-day FREE trial license](https://www.dynamsoft.com/customer/license/trialLicense/?product=dlr) to activate the SDK.


## Supported Python Edition
* Python 3.x


## How to Build the Python MRZ Scanner Extension
- Create a source distribution:
    
    ```bash
    python setup.py sdist
    ```

- setuptools:
    
    ```bash
    python setup_setuptools.py build
    python setup_setuptools.py develop 
    ```

- scikit-build:
    
    ```bash
    python setup.py build
    python setup.py develop 
    ```
- Build wheel:
    
    ```bash
    pip wheel . --verbose
    # Or
    python setup_setuptools.py bdist_wheel
    # Or
    python setup.py bdist_wheel
    ```


## Quick Start
- Console App
    1. Install dependencies:
        ```bash
        pip install mrz opencv-python
        ```
    2. Run the script:
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
- `decodeFile(filename)` # recognize MRZ from an image file

    ```python
    results = scanner.decodeFile(<image-file>)
    for result in results:
            print(result.text)
    ```
- `decodeMat(Mat image)` # recognize MRZ from OpenCV Mat
    ```python
    import cv2
    image = cv2.imread(<image-file>)
    results = scanner.decodeMat(image)
    for result in results:
        print(result.text)
    ```