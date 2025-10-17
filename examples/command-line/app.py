import argparse
import numpy as np
import os
import sys
package_path = os.path.dirname(__file__) + '/../../'
sys.path.append(package_path)
import mrzscanner

def scanmrz():
    """
    Command-line script for recognize MRZ info from a given image
    """
    parser = argparse.ArgumentParser(description='Scan MRZ info from a given image')
    parser.add_argument('filename')
    parser.add_argument('-u', '--ui', default=False, type=bool, help='Whether to show the image')
    parser.add_argument('-l', '--license', default='', type=str, help='Set a valid license key')
    args = parser.parse_args()
    # print(args)
    try:
        filename = args.filename
        license = args.license
        ui = args.ui
        
        # set license
        if  license == '':
            mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")
        else:
            mrzscanner.initLicense(license)
            
        # initialize mrz scanner
        scanner = mrzscanner.createInstance()
        
        if ui:
            import cv2
            image = cv2.imread(filename)
            results = scanner.decodeMat(image)
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
                
                cv2.drawContours(image, [np.array([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], dtype=np.int32)], 0, (0, 255, 0), 2)
            
            cv2.imshow("image", image)
            cv2.waitKey(0)
        else:
            results = scanner.decodeFile(filename)
            for result in results:
                print(result.to_string())
                
            
    except Exception as err:
        print(err)
        sys.exit(1)



if __name__ == "__main__":
    scanmrz()