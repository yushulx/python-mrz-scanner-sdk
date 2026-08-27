"""
Minimal MRZ detection demo using the Dynamsoft Capture Vision Python bundle.

Usage:
    python app.py passport.jpg
"""

import argparse
import sys

import cv2
import numpy as np
from dynamsoft_capture_vision_bundle import *

LICENSE_KEY = "LICENSE-KEY"


def convertMat2ImageData(mat):
    """Convert an OpenCV matrix (BGR or gray) to a Dynamsoft ImageData object."""
    height, width = mat.shape[:2]
    if len(mat.shape) == 3:
        channels = 3
        pixel_format = EnumImagePixelFormat.IPF_RGB_888
        data = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB).tobytes()
    else:
        channels = 1
        pixel_format = EnumImagePixelFormat.IPF_GRAYSCALED
        data = mat.tobytes()
    return ImageData(data, width, height, width * channels, pixel_format)


def print_parsed_result(parsed_result):
    for item in parsed_result.get_items():
        print("Document Type:", item.get_code_type())
        for i in range(1, 4):
            line = item.get_field_value("line{}".format(i))
            if line is not None:
                status = item.get_field_validation_status("line{}".format(i))
                tag = " [Validation Failed]" if status == EnumValidationStatus.VS_FAILED else ""
                print("  Line {}: {}{}".format(i, line, tag))
        for field in ("passportNumber", "documentNumber", "primaryIdentifier",
                      "secondaryIdentifier", "nationality", "issuingState",
                      "sex", "dateOfBirth", "dateOfExpiry"):
            value = item.get_field_value(field)
            if value is not None:
                print("  {}: {}".format(field, value))


def detect_mrz(cvr, image):
    result = cvr.capture(convertMat2ImageData(image), "ReadPassportAndId")
    if result is None or result.get_error_code() != EnumErrorCode.EC_OK:
        print("Capture failed:", result.get_error_string() if result else "no result")
        return False

    parsed_result = result.get_parsed_result()
    if parsed_result is None or len(parsed_result.get_items()) == 0:
        print("No MRZ detected.")
        return False

    print_parsed_result(parsed_result)

    # Draw detected MRZ text-line locations
    line_result = result.get_recognized_text_lines_result()
    if line_result is not None:
        for item in line_result.get_items():
            location = item.get_location()
            pts = [(p.x, p.y) for p in location.points]
            del location
            cv2.drawContours(image, [np.intp(pts)], 0, (0, 255, 0), 2)

    return True


def main():
    parser = argparse.ArgumentParser(description="Scan MRZ info from a given image")
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

    if detect_mrz(cvr, image):
        cv2.imshow("MRZ Detection", image)
        cv2.waitKey(0)


if __name__ == "__main__":
    main()
