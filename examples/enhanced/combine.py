"""
Enhanced MRZ detection: document edge detection + perspective transformation
(Dynamsoft Capture Vision) followed by face-orientation correction (RetinaFace).

Usage:
    python combine.py passport_180.jpg
"""

import argparse
import sys

import cv2
import numpy as np
from dynamsoft_capture_vision_bundle import *

import face_retina
from app import convertMat2ImageData, print_parsed_result

LICENSE_KEY = "LICENSE-KEY"


def convertImageData2Mat(image_data):
    """Convert a Dynamsoft ImageData object to an OpenCV matrix (BGR)."""
    width = image_data.get_width()
    height = image_data.get_height()
    pixel_format = image_data.get_image_pixel_format()
    data = bytearray(image_data.get_bytes())
    if pixel_format == EnumImagePixelFormat.IPF_RGB_888:
        mat = np.array(data, dtype=np.uint8).reshape(height, width, 3)
        mat = cv2.cvtColor(mat, cv2.COLOR_RGB2BGR)
    elif pixel_format == EnumImagePixelFormat.IPF_BGR_888:
        mat = np.array(data, dtype=np.uint8).reshape(height, width, 3)
    else:  # gray / binary
        mat = np.array(data, dtype=np.uint8).reshape(height, width)
    return mat


def detect_and_normalize_doc(cvr, image):
    """Detect the document quad and return the perspective-corrected image."""
    result = cvr.capture(convertMat2ImageData(image),
                         EnumPresetTemplate.PT_DETECT_AND_NORMALIZE_DOCUMENT.value)
    if result is None or result.get_error_code() != EnumErrorCode.EC_OK:
        return image

    processed_document_result = result.get_processed_document_result()
    if processed_document_result is None:
        return image

    enhanced_items = processed_document_result.get_enhanced_image_result_items()
    if len(enhanced_items) == 0:
        return image

    # Draw the detected document quad on a copy for visualization
    quad_items = processed_document_result.get_detected_quad_result_items()
    if len(quad_items) > 0:
        copy = image.copy()
        location = quad_items[0].get_location()
        pts = [(p.x, p.y) for p in location.points]
        del location
        cv2.drawContours(copy, [np.intp(pts)], 0, (255, 0, 0), 2)
        cv2.imshow("Document Detection", copy)

    return convertImageData2Mat(enhanced_items[0].get_image_data())


def detect_mrz(cvr, image):
    result = cvr.capture(convertMat2ImageData(image), "ReadPassportAndId")
    if result is None or result.get_error_code() != EnumErrorCode.EC_OK:
        print("Capture failed:", result.get_error_string() if result else "no result")
        return None

    parsed_result = result.get_parsed_result()
    if parsed_result is None or len(parsed_result.get_items()) == 0:
        return None

    print_parsed_result(parsed_result)

    line_result = result.get_recognized_text_lines_result()
    if line_result is not None:
        for item in line_result.get_items():
            location = item.get_location()
            pts = [(p.x, p.y) for p in location.points]
            del location
            cv2.drawContours(image, [np.intp(pts)], 0, (0, 255, 0), 2)

    return parsed_result


def main():
    parser = argparse.ArgumentParser(description="Scan MRZ info from a rotated image")
    parser.add_argument("filename")
    parser.add_argument("-l", "--license", default=LICENSE_KEY, type=str,
                        help="Set a valid license key")
    args = parser.parse_args()

    error_code, error_message = LicenseManager.init_license(args.license)
    if error_code != EnumErrorCode.EC_OK and error_code != EnumErrorCode.EC_LICENSE_WARNING:
        print("License initialization failed:", error_code, error_message)
        sys.exit(1)

    cvr = CaptureVisionRouter()

    image = cv2.imread(args.filename)
    if image is None:
        print("Failed to read image:", args.filename)
        sys.exit(1)

    # 1. Edge detection + perspective transformation
    rectified = detect_and_normalize_doc(cvr, image)
    # 2. Rotate the rectified image based on facial orientation (RetinaFace)
    upright = face_retina.detect(rectified)
    # 3. MRZ detection on the orientation-corrected image
    mrz_image = upright.copy()
    parsed = detect_mrz(cvr, mrz_image)
    if parsed is None:
        print("No MRZ detected.")

    cv2.imshow("Original", image)
    cv2.imshow("MRZ Detection", mrz_image)
    cv2.waitKey(0)


if __name__ == "__main__":
    main()
