import argparse
import mrzscanner
import sys
import numpy as np
import cv2
import docscanner
import time

def detect_mrz(image, scanner):
    s = ""
    results = scanner.decodeMat(image)
    for result in results:
        # print(result.text)
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
        cv2.putText(image, result.text, (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 2)
        
    cv2.imshow("MRZ Detection", image)

def detect_doc(image, scanner):
    results = scanner.detectMat(image)
    if results is None or len(results) == 0:
        return image
    
    rectified_document = None
    result = results[0]
    x1 = result.x1
    y1 = result.y1
    x2 = result.x2
    y2 = result.y2
    x3 = result.x3
    y3 = result.y3
    x4 = result.x4
    y4 = result.y4
    
    copy = image.copy()
    cv2.drawContours(copy, [np.int0([(x1, y1), (x2, y2), (x3, y3), (x4, y4)])], 0, (255, 0, 0), 2)
    cv2.imshow("Document Detection", copy)
    
    rectified_document = scanner.normalizeBuffer(image, x1, y1, x2, y2, x3, y3, x4, y4)
    # if rectified_document is not None:
    #     rectified_document.save(str(time.time()) + '.png')
    #     print('Image saved')
    #     rectified_document.recycle()
    mat = docscanner.convertNormalizedImage2Mat(rectified_document)
    return mat
        
        # cv2.imshow("Normalized Image", mat)
    
        # cv2.drawContours(image, [np.int0([(x1, y1), (x2, y2), (x3, y3), (x4, y4)])], 0, (0, 255, 0), 2)
    
    return image
    # cv2.putText(image, 'Press "ESC" to exit', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    # cv2.imshow('Document Image', image)
    
    # if rectified_document is not None:
    #     rectified_document.save(str(time.time()) + '.png')
    #     print('Image saved')
    #     rectified_document.recycle()
    # else:
    #     print('No document found')
        
def scanmrz():
    parser = argparse.ArgumentParser(description='Scan MRZ info from a given image')
    parser.add_argument('filename')
    parser.add_argument('-l', '--license', default='', type=str, help='Set a valid license key')
    args = parser.parse_args()
    try:
        filename = args.filename
        license = args.license
        
        # set license
        if  license == '':
            defaultLicense = "DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ=="
            mrzscanner.initLicense(defaultLicense)
            docscanner.initLicense(defaultLicense)
        else:
            mrzscanner.initLicense(license)
            docscanner.initLicense(license)
            
        mrz_scanner = mrzscanner.createInstance()
        doc_scanner = docscanner.createInstance()
        doc_scanner.setParameters(docscanner.Templates.color)

        # load MRZ model
        mrz_scanner.loadModel(mrzscanner.load_settings())
        
        image = cv2.imread(filename)
        
        while True:
            copy = image.copy()
            
            copy = detect_doc(copy, doc_scanner)
            detect_mrz(copy, mrz_scanner)
            
            key = cv2.waitKey(100) & 0xFF

            if key == 27:  # ESC key to exit
                break
            elif key == 100:  # D key to rotate clockwise
                transposed = cv2.transpose(image)
                image = cv2.flip(transposed, flipCode=1)
            elif key == 97:  # A key to rotate counter-clockwise
                transposed = cv2.transpose(image)
                image = cv2.flip(transposed, flipCode=0)
                
            cv2.imshow("Original", image)
            
    except Exception as err:
        print(err)
        sys.exit(1)

if __name__ == "__main__":
    scanmrz()
    # image0 = cv2.imread('0.png')
    # image90 = cv2.imread('90.png')
    # image180 = cv2.imread('180.png')
    # image270 = cv2.imread('270.png')
    
    # cv2.imshow('0', image0)
    # cv2.imshow('90', image90)
    # cv2.imshow('180', image180)
    # cv2.imshow('270', image270)
    
    cv2.waitKey(0)