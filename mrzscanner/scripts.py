"""
Command-line interface for MRZ Scanner SDK.

This module provides a command-line tool for scanning MRZ information from
image files or camera streams. It includes validation using external MRZ
checker libraries and optional UI display functionality.

Usage:
    scanmrz image.jpg -l LICENSE_KEY
    scanmrz image.jpg -u 1 -l LICENSE_KEY  # Show UI
"""

import argparse
import mrzscanner
import sys
import numpy as np

def scanmrz():
    """
    Command-line script for recognizing MRZ info from a given image.
    
    This function provides a command-line interface for the MRZ Scanner SDK,
    supporting both file input and optional UI display for visualization.
    It can validate results using external MRZ checker libraries if available.
    
    Command-line Arguments:
        filename: Path to the image file to process
        -u, --ui: Whether to display the image with detected MRZ regions highlighted
        -l, --license: Dynamsoft license key (uses trial key if not provided)
    
    Examples:
        scanmrz passport.jpg
        scanmrz id_card.png -u 1 -l YOUR_LICENSE_KEY
    """
    parser = argparse.ArgumentParser(
        description='Scan MRZ information from image files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scanmrz passport.jpg                    # Basic MRZ detection
  scanmrz document.png -u 1              # Show image with detected regions  
  scanmrz image.jpg -l YOUR_LICENSE_KEY  # Use custom license key
        """
    )
    
    parser.add_argument('filename', help='Path to the image file')
    parser.add_argument('-u', '--ui', action='store_true', help='Display image with detected MRZ regions')
    parser.add_argument('-l', '--license', default='', help='Dynamsoft license key')
    
    args = parser.parse_args()
    
    try:
        filename = args.filename
        license_key = args.license
        show_ui = args.ui
        
        # Initialize license
        if license_key == '':
            # Use trial license if no key provided
            trial_key = "DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ=="
            error_code, error_msg = mrzscanner.initLicense(trial_key)
        else:
            error_code, error_msg = mrzscanner.initLicense(license_key)
            
        if error_code != 0:
            print(f"License initialization failed: {error_msg} (Code: {error_code})")
            sys.exit(1)
            
        # Initialize MRZ scanner
        scanner = mrzscanner.createInstance()
        
        # Collect raw MRZ text for validation
        raw_text_lines = []
        
        if show_ui:
            try:
                import cv2
            except ImportError:
                print("Error: OpenCV is required for UI display. Install with: pip install opencv-python")
                sys.exit(1)
                
            image = cv2.imread(filename)
            if image is None:
                print(f"Error: Could not load image from {filename}")
                sys.exit(1)
                
            results = scanner.decodeMat(image)
            
            for result in results:
                print(result.to_string())
                
                
                # Draw bounding box on image
                points = np.array([
                    (int(result.x1), int(result.y1)),
                    (int(result.x2), int(result.y2)), 
                    (int(result.x3), int(result.y3)),
                    (int(result.x4), int(result.y4))
                ], np.int32)
                
                cv2.polylines(image, [points], True, (0, 255, 0), 2)
                cv2.putText(image, f"{result.raw_text[0]}", (int(result.x1), int(result.y1 - 40)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                cv2.putText(image, f"{result.raw_text[1]}", (int(result.x1), int(result.y1 - 15)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            
            print("\nPress any key to close the image window...")
            cv2.imshow("MRZ Detection Results", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        else:
            # File processing without UI
            results = scanner.decodeFile(filename)
            
            if not results:
                print("No MRZ detected in the image")
            else:
                print(f"Found {len(results)} MRZ region(s):")
                
            for result in results:
                print(result.to_string())
            
                
    except FileNotFoundError:
        print(f"Error: File '{args.filename}' not found")
        sys.exit(1)
    except Exception as err:
        print(f"Error: {err}")
        sys.exit(1)

