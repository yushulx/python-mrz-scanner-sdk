import argparse
import mrzscanner
import cv2
import sys
import numpy as np
def scanmrz():
    """
    Command-line script for recognize MRZ info from a given image
    """
    parser = argparse.ArgumentParser(description='Scan MRZ info from a given image')
    parser.add_argument('filename')
    args = parser.parse_args()

    try:
        filename = args.filename
        
        # set license
        mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

        # initialize mrz scanner
        scanner = mrzscanner.createInstance()

        image = cv2.imread(filename)
        results = scanner.decodeMat(image)
        for result in results:
            print(result.text)
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
            
    except Exception as err:
        print(err)
        sys.exit(1)

