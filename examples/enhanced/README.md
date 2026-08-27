# MRZ Detection by Orientation Correction

This sample shows how to enhance passport MRZ (Machine Readable Zone) detection by
correcting the orientation of the input image. It uses the
[Dynamsoft Capture Vision Python bundle](https://pypi.org/project/dynamsoft-capture-vision-bundle/)
(`dynamsoft-capture-vision-bundle`) — a single SDK that replaces the former separate
`mrz-scanner-sdk` (MRZ recognition) and `document-scanner-sdk` (edge detection and
perspective transformation) packages.

The pipeline is:

1. **Document edge detection + perspective transformation** —
   `CaptureVisionRouter.capture()` with `PT_DETECT_AND_NORMALIZE_DOCUMENT` deskews
   and crops the passport in one call.
2. **Facial orientation correction** — the portrait's face orientation matches the
   MRZ's, so RetinaFace landmarks (left eye / right eye / nose) are used to rotate
   the normalized image to upright.
3. **MRZ detection + parsing** — `CaptureVisionRouter.capture()` with the
   `ReadPassportAndId` template reads and parses the MRZ (TD1/TD2/TD3).

Dlib and MediaPipe are included for comparison only; they fail to provide reliable
landmarks for rotated faces.

## Features

- Detects and parses MRZ from passports at any rotation (0°, 90°, 180°, 270°)
- Document quad visualization (blue contour) and MRZ text-line overlays (green)
- Parsed identity fields: document type, passport number, name, issuing state,
  date of birth, expiry date
- Face-orientation examples with `face_dlib.py`, `face_mediapipe.py`, and
  `face_retina.py`

## Prerequisites

- Python 3.8+
- Valid [Dynamsoft license](https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform)

## Installation

```bash
pip install -r requirements.txt
```

What the packages do:

- `dynamsoft-capture-vision-bundle`: Dynamsoft Capture Vision SDK for Python — MRZ
  recognition, document edge detection, and perspective correction behind one
  `CaptureVisionRouter` API.
- `dlib`: classic frontal-face detector (comparison baseline).
- `mediapipe`: Google's lightweight face detector (comparison baseline).
- `retina-face`: deep-learning face detector with landmarks; the one used for
  orientation correction in `combine.py`. Its model (`retinaface.h5`, ~119 MB) is
  downloaded to `~/.deepface/weights/` on first run.
- `opencv-python`: image loading, display, and result drawing.

## Usage

1. Set your license key, or pass it on the command line:

    ```python
    LICENSE_KEY = "LICENSE-KEY"
    ```

2. Run the scripts:

    ```bash
    python app.py passport.jpg # basic MRZ detection, no orientation correction
    python app.py passport_90.jpg -l <your license key>
    python combine.py passport_90.jpg # normalize + face rotation + MRZ
    python combine.py passport_180.jpg
    python combine.py passport_270.jpg
    ```

   All four orientations of the sample passport decode with the same result:

    ```text
    Document Type: MRTD_TD3_PASSPORT
      Line 1: P<CANAMAN<<RITA<TANIA<<<<<<<<<<<<<<<<<<<<<<<
      Line 2: ERE82721<9CAN8412070M2405252<<<<<<<<<<<<<<08
    ```

3. Optional — compare the three face detectors:

    ```bash
    python face_dlib.py        # needs shape_predictor_68_face_landmarks.dat
    python face_mediapipe.py   # needs blaze_face_short_range.tflite
    python face_retina.py      # auto-downloads retinaface.h5 on first run
    ```

## Files

| File | Description |
|------|-------------|
| `app.py` | MRZ detection with the Capture Vision bundle (`ReadPassportAndId`) and `convertMat2ImageData()` / `print_parsed_result()` helpers |
| `combine.py` | Full pipeline: document normalization → RetinaFace rotation → MRZ detection |
| `face_retina.py` | RetinaFace landmarks + `rotate()` correction used by `combine.py` |
| `face_dlib.py` | Dlib face detection demo (comparison) |
| `face_mediapipe.py` | MediaPipe face detection demo (comparison) |
| `passport*.jpg` | Test passport images at 0°/90°/180°/270° |
| `requirements.txt` | Python dependencies |

![passport-mrz-detection-any-orientation](https://github.com/yushulx/python-mrz-scanner-sdk/assets/2202306/d9e8e185-01a5-4123-92c7-8f83e8d51bc3)

## Related Article

[How to Enhance Passport MRZ Detection in Python by Correcting Image Orientation](https://www.dynamsoft.com/codepool/improve-python-passport-mrz-detection-rate.html)
