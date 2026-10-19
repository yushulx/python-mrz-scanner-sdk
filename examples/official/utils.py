from dynamsoft_capture_vision_bundle import *
import numpy as np


def convertImageData2Mat(normalized_image):
    """Convert a Dynamsoft ImageData object to an OpenCV BGR/gray matrix."""
    width = normalized_image.get_width()
    height = normalized_image.get_height()
    stride = normalized_image.get_stride()
    pixel_format = normalized_image.get_image_pixel_format()
    raw = np.frombuffer(normalized_image.get_bytes(), dtype=np.uint8)

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image size: {width}x{height}")
    if stride <= 0:
        stride = len(raw) // height
    if len(raw) < stride * height:
        raise ValueError(
            f"ImageData buffer is too small: {len(raw)} bytes, "
            f"expected {stride * height} (stride={stride}, height={height})"
        )

    rows = raw[: stride * height].reshape(height, stride)

    if pixel_format in (EnumImagePixelFormat.IPF_BINARY, EnumImagePixelFormat.IPF_BINARYINVERTED):
        gray = np.unpackbits(rows, axis=1)[:, :width].astype(np.uint8) * 255
        if pixel_format == EnumImagePixelFormat.IPF_BINARYINVERTED:
            gray = 255 - gray
        return np.ascontiguousarray(gray)

    if pixel_format in (
        EnumImagePixelFormat.IPF_GRAYSCALED,
        EnumImagePixelFormat.IPF_BINARY_8,
        EnumImagePixelFormat.IPF_BINARY_8_INVERTED,
    ):
        gray = rows[:, :width]
        if pixel_format == EnumImagePixelFormat.IPF_BINARY_8_INVERTED:
            gray = 255 - gray
        return np.ascontiguousarray(gray)

    if pixel_format in (EnumImagePixelFormat.IPF_RGB_888, EnumImagePixelFormat.IPF_BGR_888):
        channels = 3
    elif pixel_format in (EnumImagePixelFormat.IPF_ARGB_8888, EnumImagePixelFormat.IPF_ABGR_8888):
        channels = 4
    else:
        raise ValueError(f"Unsupported pixel format: {pixel_format}")

    if stride < width * channels:
        raise ValueError(
            f"Invalid stride {stride} for a {width}x{height} image with "
            f"{channels} channels"
        )

    mat = rows[:, : width * channels].reshape(height, width, channels)
    if pixel_format == EnumImagePixelFormat.IPF_RGB_888:
        return np.ascontiguousarray(mat[:, :, ::-1])  # RGB -> BGR
    if pixel_format == EnumImagePixelFormat.IPF_BGR_888:
        return np.ascontiguousarray(mat)
    if pixel_format == EnumImagePixelFormat.IPF_ARGB_8888:
        return np.ascontiguousarray(mat[:, :, 3:0:-1])  # ARGB -> BGR
    # IPF_ABGR_8888 (A, B, G, R) -> BGR
    return np.ascontiguousarray(mat[:, :, 1:4])


def convertMat2ImageData(mat):
    if not isinstance(mat, np.ndarray):
        raise TypeError("mat must be a numpy.ndarray")

    mat = np.ascontiguousarray(mat)
    if mat.ndim == 3 and mat.shape[2] == 1:
        mat = mat[:, :, 0]

    if mat.ndim == 3 and mat.shape[2] == 3:
        height, width = mat.shape[:2]
        pixel_format = EnumImagePixelFormat.IPF_RGB_888
    elif mat.ndim == 2:
        height, width = mat.shape
        pixel_format = EnumImagePixelFormat.IPF_GRAYSCALED
    else:
        raise ValueError(
            "Unsupported image shape %r; expected (H, W), (H, W, 1) or (H, W, 3)"
            % (mat.shape,)
        )

    imagedata = ImageData(mat.tobytes(), width, height, mat.strides[0], pixel_format)
    return imagedata


class MRZResult:
    def __init__(self, item: ParsedResultItem):
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

    def to_string(self):
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


def print_results(result: ParsedResult) -> None:
    tag = result.get_original_image_tag()
    if isinstance(tag, FileImageTag):
        print("File:", tag.get_file_path())
    if result.get_error_code() != EnumErrorCode.EC_OK:
        print("Error:", result.get_error_string())
    else:
        items = result.get_items()
        print("Parsed", len(items), "MRZ Zones.")
        for item in items:
            mrz_result = MRZResult(item)
            print(mrz_result.to_string())
