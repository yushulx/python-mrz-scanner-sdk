import argparse
import mrzscanner
import cv2
import sys
import numpy as np

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

def scanmrz():
    """
    Command-line script for recognize MRZ info from a given image
    """
    parser = argparse.ArgumentParser(description='Scan MRZ info from a given image')
    parser.add_argument('filename')
    parser.add_argument('-u', '--ui', default=False, type=bool, help='Whether to show the image')
    args = parser.parse_args()
    # print(args)
    try:
        filename = args.filename
        ui = args.ui
        
        # set license
        mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

        # initialize mrz scanner
        scanner = mrzscanner.createInstance()

        # load MRZ model
        scanner.loadModel(mrzscanner.get_model_path())
        
        image = cv2.imread(filename)
        
        s = ""
        if ui:
            results = scanner.decodeMat(image)
            for result in results:
                print(result.text)
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
                # cv2.putText(image, result.text, (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 2)
                
            cv2.imshow("image", image)
            cv2.waitKey(0)
        else:
            results = scanner.decodeFile(filename)
            for result in results:
                print(result.text)
                s += result.text + '\n'
                
        print(check(s[:-1]))
            
    except Exception as err:
        print(err)
        sys.exit(1)

