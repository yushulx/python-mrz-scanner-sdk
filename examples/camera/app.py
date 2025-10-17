import argparse
import numpy as np

import os
import sys
package_path = os.path.dirname(__file__) + '/../../'
sys.path.append(package_path)
import mrzscanner

from multiprocessing.pool import ThreadPool
from collections import deque

import cv2

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
                for result in results:
                    print(result.to_string())
                    x1 = result.x1
                    y1 = result.y1
                    x2 = result.x2
                    y2 = result.y2
                    x3 = result.x3
                    y3 = result.y3
                    x4 = result.x4
                    y4 = result.y4
                    
                    cv2.drawContours(frame, [np.array([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], dtype=np.int32)], 0, (0, 255, 0), 2)
                
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

