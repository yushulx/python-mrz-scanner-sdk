from time import sleep
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

# # load MRZ model
scanner.loadModel(mrzscanner.get_model_path())

# decodeFile()
print('')
print('Test decodeFile()')
s = ""
results = scanner.decodeFile("images/1.png")
for result in results:
    print(result.text)
    s += result.text + '\n'
print('')
print(check(s[:-1]))

# decodeMat()
print('')
print('Test decodeMat()')
s = ""
import cv2
image = cv2.imread("images/2.png")
results = scanner.decodeMat(image)
for result in results:
    print(result.text)
    s += result.text + '\n'

print('')
print(check(s[:-1]))

# decodeMatAsync()
print('')
print('Test decodeMatAsync()')
def callback(results):
    s = ""
    for result in results:
        print(result.text)
        s += result.text + '\n'
    
    print('')
    print(check(s[:-1]))
    
import cv2
image = cv2.imread("images/3.jpg")
scanner.addAsyncListener(callback)
scanner.decodeMatAsync(image)
sleep(1)
    



