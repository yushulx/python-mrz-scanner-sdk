import os
import cv2
from time import sleep
import mrzscanner
from mrzscanner import *

# set license
print('Version : ', mrzscanner.__version__)
license_key = os.environ.get('DYNAMSOFT_LICENSE_KEY', '')
if license_key == '':
    license_key = "DLS2eyJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSJ9"
error_code, error_message = mrzscanner.initLicense(license_key)
if not mrzscanner.isLicenseValid(error_code):
    print("License initialization failed:", error_code, error_message)
    print("Set DYNAMSOFT_LICENSE_KEY to a valid Dynamsoft license key.")
    raise SystemExit(1)

# initialize mrz scanner
scanner = mrzscanner.createInstance()

# decodeFile()
print('')
print('Test decodeFile()')
results = scanner.decodeFile("images/1.png")
for result in results:
    print(f"Document Type: {result.doc_type}")
    print(f"Document ID: {result.doc_id}")
    print(f"Name: {result.given_name} {result.surname}")
    print(f"Nationality: {result.nationality}")
    print(f"Date of Birth: {result.date_of_birth}")
    print(f"Expiry Date: {result.date_of_expiry}")
    print("-" * 40)
print('')

# decodeMat()
print('')
print('Test decodeMat()')
image = cv2.imread("images/2.png")
results = scanner.decodeMat(image)
for result in results:
    print(result.to_string())

print('')

# decodeBytes()
print('')
print('Test decodeBytes()')
image = cv2.imread("images/2.png")
results = scanner.decodeBytes(image.tobytes(), image.shape[1], image.shape[0], image.shape[2] * image.shape[1], EnumImagePixelFormat.IPF_BGR_888)
for result in results:
    print(result.to_string())

# decodeMatAsync()
print('')
print('Test decodeMatAsync()')

def callback(results):
    for result in results:
        print(result.to_string())

    print('')


image = cv2.imread("images/3.jpg")
scanner.addAsyncListener(callback)
for i in range(3):
    print('decodeMatAsync: {}'.format(i))
    scanner.decodeMatAsync(image)

    sleep(1)

scanner.clearAsyncListener()