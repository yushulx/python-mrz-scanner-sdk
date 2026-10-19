import os
import sys
package_path = os.path.dirname(__file__) + '/../../'
sys.path.append(package_path)
import mrzscanner
import numpy as np

# set license
license_key = os.environ.get(
    'DYNAMSOFT_LICENSE_KEY',
    "DLS2eyJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSJ9",
)
error_code, error_message = mrzscanner.initLicense(license_key)
if not mrzscanner.isLicenseValid(error_code):
    print("License initialization failed:", error_code, error_message)
    print("Set DYNAMSOFT_LICENSE_KEY to a valid Dynamsoft license key.")
    sys.exit(1)

# initialize mrz scanner
scanner = mrzscanner.createInstance()

g_results = []

def callback(results):
    global g_results 
    g_results = results
    
import cv2
scanner.addAsyncListener(callback)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open camera 0")
    scanner.clearAsyncListener()
    sys.exit(1)
while True:
    ret, image = cap.read()
    if not ret or image is None:
        print("Error: Cannot read frame from camera")
        break
    scanner.decodeMatAsync(image)
    
    if g_results != None:
        for result in g_results:
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
        
    cv2.imshow('MRZ Scanner', image)
    ch = cv2.waitKey(1)
    if ch == 27:
        break


scanner.clearAsyncListener()
cap.release()
cv2.destroyAllWindows()
