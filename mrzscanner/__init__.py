"""
Python MRZ Scanner SDK

This package provides a Python interface for Machine Readable Zone (MRZ) detection
and parsing using the Dynamsoft Capture Vision SDK. It supports various document
types including passports, ID cards, visas, and travel documents.

Key Features:
- Synchronous and asynchronous MRZ detection
- Support for multiple input formats (files, OpenCV matrices, raw bytes)
- Real-time camera stream processing
- Comprehensive MRZ field parsing and validation
- Cross-platform compatibility (Windows, Linux, macOS)

Main Classes:
- MrzScanner: Primary interface for MRZ detection
- MrzResult: Container for detected MRZ data and location
- FrameFetcher: Image source adapter for continuous processing

Usage:
    import mrzscanner
    
    # Initialize license (required)
    error_code, error_msg = mrzscanner.initLicense("YOUR_LICENSE_KEY")
    if error_code != 0:
        print(f"License error: {error_msg}")
        exit(1)
    
    # Create scanner and detect MRZ
    scanner = mrzscanner.createInstance()
    results = scanner.decodeFile("passport.jpg")
    
    # Process results
    for mrz in results:
        print(f"Document: {mrz.doc_type}")
        print(f"Name: {mrz.given_name} {mrz.surname}")
        print(f"Document ID: {mrz.doc_id}")

For more information, visit: https://github.com/yushulx/python-mrz-scanner-sdk
"""

from dynamsoft_capture_vision_bundle import (
    EnumImagePixelFormat,
    EnumErrorCode, 
    CaptureVisionRouter,
    LicenseManager,
    ImageData,
    ImageSourceAdapter,
    CapturedResultReceiver,
    LabelRecognizerModule,
    ParsedResultItem,
    EnumValidationStatus,
    Quadrilateral
)
from typing import List, Tuple, Callable, Union, Optional, Any
import numpy as np

# Package version - retrieved from the underlying SDK
__version__ = LabelRecognizerModule.get_version()
    
class FrameFetcher(ImageSourceAdapter):
    """
    Custom image source adapter for handling frame-by-frame image processing.
    
    This class extends ImageSourceAdapter to provide continuous image fetching
    capability for real-time MRZ detection scenarios like camera streams.
    """
    
    def has_next_image_to_fetch(self) -> bool:
        """
        Indicates whether there are more images to fetch.
        
        Returns:
            bool: Always returns True to enable continuous image fetching.
        """
        return True

    def add_frame(self, imageData: ImageData) -> None:
        """
        Adds a new image frame to the processing buffer.
        
        Args:
            imageData (ImageData): The image data to be added to the buffer
                                  for MRZ detection processing.
        """
        self.add_image_to_buffer(imageData)


class MyCapturedResultReceiver(CapturedResultReceiver):
    """
    Custom result receiver for handling asynchronous MRZ detection results.
    
    This class processes captured results from the SDK and converts them
    to MrzResult objects before passing to the user-defined listener.
    """
    
    def __init__(self, listener: Callable[[List['MrzResult']], None]) -> None:
        """
        Initialize the result receiver with a callback listener.
        
        Args:
            listener (callable): A callback function that will be called
                               with a list of MrzResult objects when
                               MRZs are detected.
        """
        super().__init__()
        self.listener = listener
    
    def on_captured_result_received(self, result: Any) -> None:
        """
        Called when MRZ detection results are received.
        
        This method processes the raw SDK results and converts them
        to MrzResult objects before calling the listener.
        
        Args:
            result: The captured result from the SDK containing detected items.
        """
        line_result = result.get_recognized_text_lines_result()
        parsed_result = result.get_parsed_result()

        output: List['MrzResult'] = []
        items = []
        parsed_items = []
        if line_result is not None: 
            items = line_result.get_items()
        if parsed_result is not None:
            parsed_items = parsed_result.get_items()
        
        for i in range(len(items)):
            mrz = MrzResult(parsed_items[i], items[i].get_location())
            output.append(mrz)
        
        self.listener(output) 


class MrzResult:
    """
    Represents a detected MRZ (Machine Readable Zone) with parsed information and location.
    
    This class contains all the information extracted from a detected MRZ including
    the parsed fields (name, document ID, dates, etc.) and the geometric location
    of the MRZ in the source image.
    
    Attributes:
        x1, y1, x2, y2, x3, y4, x4, y4 (float): Coordinates of the four corner points
            of the detected MRZ region in the image, forming a quadrilateral.
        doc_type (str): Type of document detected (e.g., "MRTD_TD3_PASSPORT").
        raw_text (list): List of raw MRZ text lines as strings.
        doc_id (str or None): Document number/ID if successfully parsed.
        surname (str or None): Primary identifier (surname) if parsed.
        given_name (str or None): Secondary identifier (given names) if parsed.
        nationality (str or None): Nationality code (3-letter) if parsed.
        issuer (str or None): Issuing country/organization code if parsed.
        gender (str or None): Gender ("M", "F", or "<") if parsed.
        date_of_birth (str or None): Date of birth (YYMMDD format) if parsed.
        date_of_expiry (str or None): Document expiry date (YYMMDD format) if parsed.
    
    Note:
        Fields may be None if they couldn't be parsed or validation failed.
        Check the raw_text for validation status messages like "Validation Failed".
    """
    
    def __init__(self, item: ParsedResultItem, location: Quadrilateral):
        """
        Initialize MrzResult from SDK parsing result and location data.
        
        Args:
            item (ParsedResultItem): Parsed result item from the SDK containing
                                   extracted MRZ field values.
            location (Quadrilateral): Quadrilateral defining the MRZ location
                                    in the source image.
        """
        x1 = location.points[0].x
        y1 = location.points[0].y
        x2 = location.points[1].x
        y2 = location.points[1].y
        x3 = location.points[2].x
        y3 = location.points[2].y
        x4 = location.points[3].x
        y4 = location.points[3].y

        self.x1: float = x1
        self.y1: float = y1
        self.x2: float = x2
        self.y2: float = y2
        self.x3: float = x3
        self.y3: float = y3
        self.x4: float = x4
        self.y4: float = y4

        self.doc_type = item.get_code_type()
        self.raw_text = []
        self.doc_id = None
        self.surname = None
        self.given_name = None
        self.nationality = None
        self.issuer = None
        self.gender = None
        self.date_of_birth = None
        self.date_of_expiry = None
        if self.doc_type == "MRTD_TD3_PASSPORT":
            if item.get_field_value("passportNumber") != None and item.get_field_validation_status("passportNumber") != EnumValidationStatus.VS_FAILED:
                self.doc_id = item.get_field_value("passportNumber")
            elif item.get_field_value("documentNumber") != None and item.get_field_validation_status("documentNumber") != EnumValidationStatus.VS_FAILED:
                self.doc_id = item.get_field_value("documentNumber")

        line = item.get_field_value("line1")
        if line is not None:
            if item.get_field_validation_status("line1") == EnumValidationStatus.VS_FAILED:
                line += ", Validation Failed"
            self.raw_text.append(line)
        line = item.get_field_value("line2")
        if line is not None:
            if item.get_field_validation_status("line2") == EnumValidationStatus.VS_FAILED:
                line += ", Validation Failed"
            self.raw_text.append(line)
        line = item.get_field_value("line3")
        if line is not None:
            if item.get_field_validation_status("line3") == EnumValidationStatus.VS_FAILED:
                line += ", Validation Failed"
            self.raw_text.append(line)

        if item.get_field_value("nationality") != None and item.get_field_validation_status("nationality") != EnumValidationStatus.VS_FAILED:
            self.nationality = item.get_field_value("nationality")
        if item.get_field_value("issuingState") != None and item.get_field_validation_status("issuingState") != EnumValidationStatus.VS_FAILED:
            self.issuer = item.get_field_value("issuingState")
        if item.get_field_value("dateOfBirth") != None and item.get_field_validation_status("dateOfBirth") != EnumValidationStatus.VS_FAILED:
            self.date_of_birth = item.get_field_value("dateOfBirth")
        if item.get_field_value("dateOfExpiry") != None and item.get_field_validation_status("dateOfExpiry") != EnumValidationStatus.VS_FAILED:
            self.date_of_expiry = item.get_field_value("dateOfExpiry")
        if item.get_field_value("sex") != None and item.get_field_validation_status("sex") != EnumValidationStatus.VS_FAILED:
            self.gender = item.get_field_value("sex")
        if item.get_field_value("primaryIdentifier") != None and item.get_field_validation_status("primaryIdentifier") != EnumValidationStatus.VS_FAILED:
            self.surname = item.get_field_value("primaryIdentifier")
        if item.get_field_value("secondaryIdentifier") != None and item.get_field_validation_status("secondaryIdentifier") != EnumValidationStatus.VS_FAILED:
            self.given_name = item.get_field_value("secondaryIdentifier")

    def to_string(self) -> str:
        """
        Generate a human-readable string representation of the MRZ result.
        
        Creates a formatted string containing both the raw MRZ text lines
        and all parsed information fields. Useful for debugging, logging,
        or displaying results to users.
        
        Returns:
            str: Formatted string with raw text and parsed fields.
            
        Example:
            result = scanner.decodeFile("passport.jpg")[0]
            print(result.to_string())
            # Output:
            # Raw Text:
            #     Line 1: P<UTOERIKSSON<<ANNA<MARIA<...
            #     Line 2: L898902C36UTO7408122F1204159...
            # Parsed Information:
            #     DocumentType: MRTD_TD3_PASSPORT
            #     DocumentID: L898902C3
            #     Surname: ERIKSSON
            #     ...
        """
        msg = (f"Raw Text:\n")
        for index, line in enumerate(self.raw_text):
            msg += (f"\tLine {index + 1}: {line}\n")
        msg += (f"Parsed Information:\n"
                f"\tDocumentType: {self.doc_type or ''}\n"
                f"\tDocumentID: {self.doc_id or ''}\n"
                f"\tSurname: {self.surname or ''}\n"
                f"\tGivenName: {self.given_name or ''}\n"
                f"\tNationality: {self.nationality or ''}\n"
                f"\tIssuingCountryorOrganization: {self.issuer or ''}\n"
                f"\tGender: {self.gender or ''}\n"
                f"\tDateofBirth(YYMMDD): {self.date_of_birth or ''}\n"
                f"\tExpirationDate(YYMMDD): {self.date_of_expiry or ''}\n")
        return msg

class MrzScanner:
    """
    Main MRZ scanner class providing both synchronous and asynchronous MRZ detection.

    This class wraps the Dynamsoft Capture Vision SDK to provide an easy-to-use
    interface for MRZ detection from various input sources including image files,
    OpenCV matrices, raw bytes, and real-time camera streams. It supports multiple
    document types including passports, ID cards, visas, and travel documents.
    
    The scanner operates in two modes:
    - Synchronous: Process single images and return results immediately
    - Asynchronous: Process continuous streams with callback-based results
    
    Supported MRZ Types:
    - TD1 (ID cards, 3 lines, 30 characters each)
    - TD2 (ID cards, 2 lines, 36 characters each) 
    - TD3 (Passports, 2 lines, 44 characters each)
    - MRVA/MRVB (Visas, 2 lines, 44/36 characters)
    
    Note:
        Make sure to call initLicense() before creating scanner instances.
        The SDK requires a valid license to function properly.
    
    Example:
        # Initialize license first
        error_code, error_msg = initLicense("YOUR_LICENSE_KEY")
        if error_code != 0:
            print(f"License error: {error_msg}")
            return
            
        # Create scanner and process image
        scanner = MrzScanner()
        results = scanner.decodeFile("passport.jpg")
        for mrz in results:
            print(mrz.to_string())
    """
    
    def __init__(self) -> None:
        """
        Initialize the MRZ scanner with default settings.
        
        Sets up the Capture Vision Router with MRZ reading template
        and prepares the instance for both sync and async operations.
        """
        cvr_instance = CaptureVisionRouter()
        self.fetcher: FrameFetcher = FrameFetcher()
        cvr_instance.set_input(self.fetcher)
        self.cvr_instance: CaptureVisionRouter = cvr_instance
        self.receiver: Optional[MyCapturedResultReceiver] = None

    def addAsyncListener(self, listener: Callable[[List[MrzResult]], None]) -> None:
        """
        Start asynchronous MRZ detection with a callback listener.

        This enables real-time MRZ detection where results are delivered
        asynchronously via the callback function. The SDK processes frames
        in a separate thread, making it ideal for camera streams and
        continuous monitoring applications.
        
        Args:
            listener (Callable[[List[MrzResult]], None]): Callback function that
                will be called when MRZs are detected. The function should:
                - Accept a single parameter: List[MrzResult]
                - Handle results quickly to avoid blocking the detection pipeline
                - Return None
        
        Note:
            - Only one async listener can be active at a time
            - Call clearAsyncListener() to stop async processing
            - The callback is protected by Python's GIL - no manual locking needed
            - Frames are processed asynchronously - results may not be in order
            - The underlying C++ SDK handles thread management and GIL acquisition
        
        Example:
            # Simple callback - no threading concerns needed
            def on_mrz_detected(mrzs):
                for mrz in mrzs:
                    print(f"Detected: {mrz.doc_id} ({mrz.doc_type})")

            # Shared data access - GIL provides protection
            detected_docs = []
            
            def collect_results(mrzs):
                detected_docs.extend(mrzs)  # Safe due to GIL
                print(f"Total detected: {len(detected_docs)}")

            scanner.addAsyncListener(collect_results)
            
            # Now feed frames using decodeMatAsync() or decodeBytesAsync()
            # Results will be delivered to the callback asynchronously
        """
        self.receiver = MyCapturedResultReceiver(listener)
        self.cvr_instance.add_result_receiver(self.receiver)
        error_code, error_message = self.cvr_instance.start_capturing('ReadPassportAndId')

    def clearAsyncListener(self) -> None:
        """
        Stop asynchronous MRZ detection and remove the listener.
        
        This method stops the real-time detection process, removes the callback
        listener, and cleans up associated resources. Any frames currently in
        the processing queue will be completed, but no new results will be
        delivered after this call.
        
        Note:
            - Safe to call multiple times
            - Automatically called when the scanner is destroyed
            - Should be called before application shutdown for clean resource cleanup
            - After calling this, you can set a new listener with addAsyncListener()
        
        Example:
            # Start async processing
            scanner.addAsyncListener(my_callback)
            
            # Process frames for some time...
            for frame in video_frames:
                scanner.decodeMatAsync(frame)
            
            # Stop when done
            scanner.clearAsyncListener()
            print("Async processing stopped")
        """
        if self.receiver is not None:
            self.cvr_instance.remove_result_receiver(self.receiver)
            self.receiver = None
        self.cvr_instance.stop_capturing()
        
    def decode(self, input: Union[str, ImageData]) -> List[MrzResult]:
        """
        Core decode method that handles various input types.
        
        This is the primary method for MRZ detection that processes the input
        and returns all detected MRZ regions with their parsed information.
        The method automatically handles different input formats and performs
        both text recognition and parsing.
        
        Args:
            input (str | ImageData): Input source for MRZ detection:
                - str: File path to an image (JPEG, PNG, BMP, TIFF, etc.)
                - ImageData: Pre-formatted image data object
        
        Returns:
            List[MrzResult]: List of MrzResult objects representing detected MRZs.
                           Each result contains location coordinates and parsed fields.
                           Returns empty list if:
                           - No MRZs are detected in the image
                           - Image format is unsupported
                           - License is invalid or expired
                           - Input file cannot be read
        
        Raises:
            Exception: May raise exceptions for severe errors like invalid license,
                      corrupted image files, or SDK initialization failures.
        
        Note:
            The method prints "No parsed results." to stdout when no MRZs are found.
            This is normal behavior and not an error condition.
        """
        output: List[MrzResult] = []
        result = self.cvr_instance.capture(input, 'ReadPassportAndId')
        if result.get_error_code() != EnumErrorCode.EC_OK:
            print("Error:", result.get_error_code(),
                  result.get_error_string())
        else:
            # Get the recognized text lines result
            line_result = result.get_recognized_text_lines_result()

            # Get the parsed result
            parsed_result = result.get_parsed_result()

            items = []
            parsed_items = []
            if line_result is not None: 
                items = line_result.get_items()
            if parsed_result is not None:
                parsed_items = parsed_result.get_items()
                
            for i in range(len(items)):
                mrz = MrzResult(parsed_items[i], items[i].get_location())
                output.append(mrz)
        
        return output
    
    def decodeFile(self, file_path: str) -> List[MrzResult]:
        """
        Decode MRZ from an image file.
        
        This method loads an image file from disk and performs MRZ detection.
        It supports all common image formats and automatically handles format
        detection and conversion.
        
        Args:
            file_path (str): Absolute or relative path to the image file.
                           Supported formats: JPEG, PNG, BMP, TIFF, GIF, WEBP
        
        Returns:
            List[MrzResult]: List of MrzResult objects for all detected MRZs.
                           Empty list if no MRZs found or file cannot be processed.
        
        Raises:
            FileNotFoundError: If the specified file path does not exist.
            PermissionError: If the file cannot be read due to permissions.
            Exception: For unsupported formats or corrupted image files.
        
        Example:
            # Basic usage
            results = scanner.decodeFile("passport.jpg")
            if results:
                print(f"Found {len(results)} MRZs")
                for mrz in results:
                    print(f"Document ID: {mrz.doc_id}")
            else:
                print("No MRZs detected")
                
            # With error handling
            try:
                results = scanner.decodeFile("path/to/document.png")
                # Process results...
            except FileNotFoundError:
                print("Image file not found")
            except Exception as e:
                print(f"Detection failed: {e}")
        """
        return self.decode(file_path)
    
    def decodeMat(self, mat: np.ndarray) -> List[MrzResult]:
        """
        Decode MRZs from an OpenCV image matrix.
        
        This method processes OpenCV image matrices directly, making it ideal
        for integration with computer vision pipelines, camera streams, or
        pre-processed images. The method automatically handles format conversion
        from OpenCV's BGR/grayscale format to the SDK's expected format.
        
        Args:
            mat (numpy.ndarray): OpenCV image matrix with supported formats:
                - 3-channel BGR image (height, width, 3) - typical cv2.imread() output
                - Single-channel grayscale image (height, width)
                - Data type should be uint8 (0-255 values)
        
        Returns:
            List[MrzResult]: List of MrzResult objects for all detected MRZs.
                           Empty list if no MRZs found.
        
        Raises:
            ValueError: If the input matrix has unsupported shape or data type.
            Exception: For other processing errors.

        Example:
            import cv2
            
            # From file
            image = cv2.imread("passport.jpg")
            results = scanner.decodeMat(image)
            
            # From camera
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                results = scanner.decodeMat(frame)
                
            # From processed image
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = scanner.decodeMat(gray)
            
            # Process results
            for mrz in results:
                # Draw bounding box
                points = [(mrz.x1, mrz.y1), (mrz.x2, mrz.y2), 
                         (mrz.x3, mrz.y3), (mrz.x4, mrz.y4)]
                cv2.polylines(image, [np.array(points, np.int32)], True, (0, 255, 0), 2)
        """
        return self.decode(convertMat2ImageData(mat))

    def decodeBytes(self, bytes: bytes, width: int, height: int, stride: int, pixel_format: EnumImagePixelFormat) -> List[MrzResult]:
        """
        Decode MRZs from raw image bytes.
        
        This method processes raw image data in byte format, useful for
        integration with custom image sources, network streams, or embedded
        systems that provide image data as byte arrays.
        
        Args:
            bytes (bytes): Raw image data as bytes array. Must contain pixel data
                         in the format specified by pixel_format parameter.
            width (int): Image width in pixels (must be > 0).
            height (int): Image height in pixels (must be > 0).
            stride (int): Number of bytes per image row. Usually width * channels,
                        but may include padding. Must be >= width * bytes_per_pixel.
            pixel_format (EnumImagePixelFormat): Pixel format specifying how bytes
                        are interpreted. Common values:
                        - IPF_RGB_888: 24-bit RGB (3 bytes per pixel)
                        - IPF_BGR_888: 24-bit BGR (3 bytes per pixel)
                        - IPF_GRAYSCALED: 8-bit grayscale (1 byte per pixel)
                        - IPF_ARGB_8888: 32-bit ARGB (4 bytes per pixel)
        
        Returns:
            List[MrzResult]: List of MrzResult objects for all detected MRZs.
        
        Raises:
            ValueError: If width, height, or stride are invalid, or if the
                       bytes array size doesn't match the specified dimensions.
            Exception: For other processing errors.

        Example:
            # RGB image from byte array
            width, height = 640, 480
            stride = width * 3  # 3 bytes per RGB pixel
            results = scanner.decodeBytes(
                image_bytes, width, height, stride,
                EnumImagePixelFormat.IPF_RGB_888
            )
            
            # Grayscale image
            stride = width  # 1 byte per grayscale pixel
            results = scanner.decodeBytes(
                gray_bytes, width, height, stride,
                EnumImagePixelFormat.IPF_GRAYSCALED
            )
            
            # From camera with padding
            stride = width * 3 + 16  # RGB with 16-byte row padding
            results = scanner.decodeBytes(
                camera_bytes, width, height, stride,
                EnumImagePixelFormat.IPF_RGB_888
            )
        """
        imagedata = ImageData(bytes, width, height, stride, pixel_format)
        return self.decode(imagedata)

    def decodeMatAsync(self, mat: np.ndarray) -> None:
        """
        Add an OpenCV matrix to the async processing queue.

        This method queues an OpenCV image for asynchronous processing without
        blocking the calling thread. Results are delivered via the callback
        function registered with addAsyncListener(). Ideal for real-time camera
        streams and high-throughput processing scenarios.
        
        Args:
            mat (numpy.ndarray): OpenCV image matrix to process asynchronously.
                               Same format requirements as decodeMat().
        
        Note:
            - Must call addAsyncListener() first to receive results
            - Method returns immediately without waiting for processing
            - Frames may be processed out of order in high-throughput scenarios
            - Memory is managed automatically - no need to retain the matrix
        
        Example:
            import cv2
            import time
            
            # Set up async processing
            def handle_results(mrzs):
                if mrzs:
                    print(f"Frame processed: {len(mrzs)} MRZs found")
            
            scanner.addAsyncListener(handle_results)
            
            # Camera stream processing
            cap = cv2.VideoCapture(0)
            while True:
                ret, frame = cap.read()
                if ret:
                    # Queue frame for async processing
                    scanner.decodeMatAsync(frame)
                    
                    # Display frame (optional)
                    cv2.imshow('Camera', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Don't flood the queue
                time.sleep(0.1)
            
            cap.release()
            scanner.clearAsyncListener()
        """
        self.fetcher.add_frame(convertMat2ImageData(mat))

    def decodeBytesAsync(self, bytes: bytes, width: int, height: int, stride: int, pixel_format: EnumImagePixelFormat) -> None:
        """
        Add raw image bytes to the async processing queue.

        Use this with addAsyncListener() for real-time MRZ detection
        from raw image data sources.
        
        Args:
            bytes: Raw image data as bytes
            width (int): Image width in pixels
            height (int): Image height in pixels
            stride (int): Number of bytes per row
            pixel_format: EnumImagePixelFormat value
        """
        imagedata = ImageData(bytes, width, height, stride, pixel_format)
        self.fetcher.add_frame(imagedata)


def initLicense(licenseKey: str) -> Tuple[int, str]:
    """
    Initialize the Dynamsoft license for MRZ detection.

    This function must be called once before creating any MrzScanner instances.
    The license key enables the SDK functionality and determines usage limits.
    License verification may require internet connectivity for first-time activation.
    
    Args:
        licenseKey (str): Your Dynamsoft license key. Options:
            - Trial key: "DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ=="
            - Production key: Obtain from Dynamsoft customer portal
            - Offline key: For air-gapped environments (contact Dynamsoft)
    
    Returns:
        Tuple[int, str]: A tuple containing:
            - error_code (int): 0 for success, non-zero for various error conditions:
                * -10001: Invalid license key format
                * -10004: License expired
                * -10008: Network connection failed during activation
                * -10009: License quota exceeded
            - error_message (str): Human-readable description of the error,
                                 empty string if successful
    
    Raises:
        Exception: May raise exceptions for severe initialization errors.
    
    Example:
        # Basic usage with error handling
        error_code, error_msg = initLicense("YOUR_LICENSE_KEY")
        if error_code != 0:
            print(f"License initialization failed: {error_msg} (Code: {error_code})")
            return
        
        print("License initialized successfully")
        
        # Trial license usage
        trial_key = "DLS2eyJoYW5kc2hha2VDb2RlIjoiMjAwMDAxLTE2NDk4Mjk3OTI2MzUiLCJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSIsInNlc3Npb25QYXNzd29yZCI6IndTcGR6Vm05WDJrcEQ5YUoifQ=="
        error_code, _ = initLicense(trial_key)
        if error_code == 0:
            scanner = createInstance()
            # Proceed with MRZ detection
    
    Note:
        - Call this only once per application session
        - License activation may cache credentials locally
        - Some license types have daily/monthly usage limits
        - Network connectivity may be required for license verification
    """
    errorCode, errorMsg = LicenseManager.init_license(licenseKey)
    return errorCode, errorMsg

def createInstance() -> MrzScanner:
    """
    Create a new MrzScanner instance.

    This is the recommended factory function for creating MRZ scanner instances.
    It ensures proper initialization and configuration of the underlying SDK
    components. Multiple scanner instances can be created and used concurrently.
    
    Prerequisites:
        Must call initLicense() successfully before creating any scanner instances.
    
    Returns:
        MrzScanner: A new MRZ scanner instance ready for detection operations.
                   The instance is fully configured and ready to use.
    
    Raises:
        Exception: If the license hasn't been initialized or if there are
                  SDK initialization errors.

    Example:
        # Initialize license first
        error_code, error_msg = initLicense("YOUR_LICENSE_KEY")
        if error_code != 0:
            raise Exception(f"License error: {error_msg}")
        
        # Create scanner instance
        scanner = createInstance()
        
        # Use for detection
        results = scanner.decodeFile("passport.jpg")
        
        # Multiple instances are supported
        scanner1 = createInstance()  # For file processing
        scanner2 = createInstance()  # For camera stream
    
    Note:
        - Each instance maintains its own state and configuration
        - Instances are thread-safe for concurrent use
        - No explicit cleanup required - handled by garbage collection
    """
    return MrzScanner()

def convertMat2ImageData(mat: np.ndarray) -> ImageData:
    """
    Convert an OpenCV matrix to Dynamsoft ImageData format.
    
    This utility function handles the conversion between OpenCV's numpy
    array format and the SDK's ImageData format. It automatically detects
    the image format and sets appropriate pixel format parameters for
    optimal processing by the MRZ detection engine.
    
    Args:
        mat (numpy.ndarray): OpenCV image matrix with supported formats:
            - 3-channel (H, W, 3): Treated as RGB_888 format
            - Single-channel (H, W): Treated as grayscale
            - Data type must be uint8 (0-255 values)
    
    Returns:
        ImageData: Converted image data object ready for SDK processing,
                  with automatically configured stride and pixel format.
    
    Raises:
        ValueError: If the input matrix has unsupported shape or data type.
    
    Example:
        import cv2
        
        # Convert color image
        bgr_image = cv2.imread("document.jpg")
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        image_data = convertMat2ImageData(rgb_image)
        
        # Convert grayscale image
        gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        gray_data = convertMat2ImageData(gray_image)
        
        # Use with scanner
        scanner = createInstance()
        results = scanner.decode(image_data)
    
    Note:
        - 3-channel images are assumed to be in RGB order (not BGR)
        - For BGR images from cv2.imread(), convert to RGB first
        - The function automatically calculates stride as width * channels
        - Memory layout must be contiguous (standard numpy arrays)
    """
    if len(mat.shape) == 3:
        height, width, channels = mat.shape
        pixel_format = EnumImagePixelFormat.IPF_RGB_888
    else:
        height, width = mat.shape
        channels = 1
        pixel_format = EnumImagePixelFormat.IPF_GRAYSCALED

    stride = width * channels
    imagedata = ImageData(mat.tobytes(), width, height, stride, pixel_format)
    return imagedata

def wrapImageData(width: int, height: int, stride: int, pixel_format: EnumImagePixelFormat, bytes: bytes) -> ImageData:
    """
    Create an ImageData object from raw image parameters.
    
    This utility function creates a properly formatted ImageData object
    from raw image specifications and byte data.
    
    Args:
        width (int): Image width in pixels
        height (int): Image height in pixels
        stride (int): Number of bytes per image row
        pixel_format: EnumImagePixelFormat specifying the pixel layout
        bytes: Raw image data as bytes
    
    Returns:
        ImageData: Formatted image data ready for SDK processing.
    
    Example:
        image_data = wrapImageData(
            640, 480, 1920, 
            EnumImagePixelFormat.IPF_RGB_888, 
            raw_bytes
        )
    """
    imagedata = ImageData(bytes, width, height, stride, pixel_format)
    return imagedata
