import mrzscanner

# set license
mrzscanner.initLicense("DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ==")

# initialize mrz scanner
scanner = mrzscanner.createInstance()

# decodeFile()
results = scanner.decodeFile("images/1.png")
for result in results:
    print(result.text)
    # print(result.confidence)
    # print(result.x1)
    # print(result.y1)
    # print(result.x2)
    # print(result.y2)
    # print(result.x3)
    # print(result.y3)
    # print(result.x4)
    # print(result.y4)

print('')

results = scanner.decodeFile("images/2.png")
for result in results:
    print(result.text)
    
print('')

# decodeMat()
import cv2
image = cv2.imread("images/3.jpg")
results = scanner.decodeMat(image)
for result in results:
    print(result.text)

