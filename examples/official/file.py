import sys
from dynamsoft_capture_vision_bundle import *
import os
import cv2
import numpy as np
from utils import *

if __name__ == '__main__':

    print("**********************************************************")
    print("Welcome to Dynamsoft Capture Vision - MRZ Sample")
    print("**********************************************************")

    license_key = os.environ.get(
        'DYNAMSOFT_LICENSE_KEY',
        "DLS2eyJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSJ9",
    )
    error_code, error_message = LicenseManager.init_license(license_key)
    if error_code not in (EnumErrorCode.EC_OK, EnumErrorCode.EC_LICENSE_WARNING, EnumErrorCode.EC_LICENSE_CACHE_USED):
        print("License initialization failed: ErrorCode:",
              error_code, ", ErrorString:", error_message)
        print("Pass a valid key with -l/--license or set DYNAMSOFT_LICENSE_KEY.")
    else:
        cvr_instance = CaptureVisionRouter()
        while (True):
            image_path = input(
                ">> Input your image full path:\n"
                ">> 'Enter' for sample image or 'Q'/'q' to quit\n"
            ).strip('\'"')

            if image_path.lower() == "q":
                sys.exit(0)

            if image_path == "":
                image_path = "../../images/1.png"

            if not os.path.exists(image_path):
                print("The image path does not exist.")
                continue
            result = cvr_instance.capture(image_path, "ReadPassportAndId")
            if result.get_error_code() != EnumErrorCode.EC_OK:
                print("Error:", result.get_error_code(),
                      result.get_error_string())
            else:
                cv_image = cv2.imread(image_path)

                # Get the recognized text lines result
                line_result = result.get_recognized_text_lines_result()

                # Get the parsed result
                parsed_result = result.get_parsed_result()
                if parsed_result is None or len(parsed_result.get_items()) == 0:
                    print("No parsed results.")
                else:
                    print_results(parsed_result)

                if line_result is None:
                    continue

                items = line_result.get_items()
                for item in items:
                    location = item.get_location()
                    x1 = location.points[0].x
                    y1 = location.points[0].y
                    x2 = location.points[1].x
                    y2 = location.points[1].y
                    x3 = location.points[2].x
                    y3 = location.points[2].y
                    x4 = location.points[3].x
                    y4 = location.points[3].y
                    del location

                    contour = np.array([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], dtype=np.int32)
                    cv2.drawContours(cv_image, [contour], 0, (0, 255, 0), 2)

                cv2.imshow(
                    "Original Image with Detected MRZ Zone", cv_image)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

    input("Press Enter to quit...")
