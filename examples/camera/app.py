import argparse
import mrzscanner
import sys
import numpy as np

from mrz.checker.td1 import TD1CodeChecker
from mrz.checker.td2 import TD2CodeChecker
from mrz.checker.td3 import TD3CodeChecker
from mrz.checker.mrva import MRVACodeChecker
from mrz.checker.mrvb import MRVBCodeChecker

from multiprocessing.pool import ThreadPool
from collections import deque

import cv2

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

def process_frame(frame):
    results = None
    try:
        results = scanner.decodeMat(frame)
    except Exception as err:
        print(err)
    
    return results
        
parser = argparse.ArgumentParser(description='Scan MRZ info from a given image')
parser.add_argument('-l', '--license', default='', type=str, help='Set a valid license key')
args = parser.parse_args()
try:
    license = args.license
    
    # set license
    if  license == '':
        mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")
    else:
        mrzscanner.initLicense(license)
        
    # initialize mrz scanner
    scanner = mrzscanner.createInstance()

    # load MRZ model
    scanner.loadModel(mrzscanner.load_settings())
    
    # open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Cannot open camera")
        exit(1)

    threadn = 1 # cv2.getNumberOfCPUs()
    pool = ThreadPool(processes = threadn)
    mrzTasks = deque()
    
    while True:
        ret, frame = cap.read()
        while len(mrzTasks) > 0 and mrzTasks[0].ready():
            results = mrzTasks.popleft().get()
            if results != None:
                s = ''
                for result in results:
                    s += result.text + '\n'
                    x1 = result.x1
                    y1 = result.y1
                    x2 = result.x2
                    y2 = result.y2
                    x3 = result.x3
                    y3 = result.y3
                    x4 = result.x4
                    y4 = result.y4
                    
                    cv2.drawContours(frame, [np.int0([(x1, y1), (x2, y2), (x3, y3), (x4, y4)])], 0, (0, 255, 0), 2)
                
                print(check(s[:-1]))
                
        if len(mrzTasks) < threadn:
            task = pool.apply_async(process_frame, (frame.copy(), ))
            mrzTasks.append(task)

        cv2.imshow('MRZ Scanner', frame)
        ch = cv2.waitKey(1)
        if ch == 27:
            break

    print('Done')
        
except Exception as err:
    print(err)
    sys.exit(1)

