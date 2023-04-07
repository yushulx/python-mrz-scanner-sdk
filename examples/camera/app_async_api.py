import mrzscanner
from mrz.checker.td1 import TD1CodeChecker
from mrz.checker.td2 import TD2CodeChecker
from mrz.checker.td3 import TD3CodeChecker
from mrz.checker.mrva import MRVACodeChecker
from mrz.checker.mrvb import MRVBCodeChecker
import numpy as np

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
scanner.loadModel(mrzscanner.load_settings())

g_results = None

def callback(results):
    global g_results 
    g_results = results
    
import cv2
scanner.addAsyncListener(callback)

cap = cv2.VideoCapture(0)
while True:
    ret, image = cap.read()
    if image is not None:
        scanner.decodeMatAsync(image)
    
    if g_results != None:
        s = ''
        for result in g_results:
            s += result.text + '\n'
            x1 = result.x1
            y1 = result.y1
            x2 = result.x2
            y2 = result.y2
            x3 = result.x3
            y3 = result.y3
            x4 = result.x4
            y4 = result.y4
            
            cv2.drawContours(image, [np.int0([(x1, y1), (x2, y2), (x3, y3), (x4, y4)])], 0, (0, 255, 0), 2)
        
        print(check(s[:-1]))

    cv2.imshow('MRZ Scanner', image)
    ch = cv2.waitKey(1)
    if ch == 27:
        break



