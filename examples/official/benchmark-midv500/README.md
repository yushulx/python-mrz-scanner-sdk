# Dynamsoft Capture Vision MRZ Benchmark (Python)

Benchmark the **Dynamsoft Capture Vision** Python SDK for MRZ (Machine-Readable Zone) recognition on the [MIDV-500 passport dataset](https://github.com/fcakyon/midv500).

https://github.com/user-attachments/assets/67ddba89-7092-4d79-aba9-d4fed16f0fcb

## Overview

This tool evaluates the Dynamsoft Capture Vision Python SDK on passport images from the MIDV-500 dataset and generates:

- **report.json** — full machine-readable benchmark output with per-image results
- **report.html** — polished visual dashboard with accuracy metrics, timing distribution, and per-image detail table

The benchmark measures:

- **Exact accuracy** — percentage of images where the recognized MRZ exactly matches the ground truth
- **SDK success rate** — percentage of images where the SDK successfully decoded an MRZ
- **Character-level match rate** — per-image ratio of correctly recognized MRZ characters
- **Timing** — average, P50, P95, P99, min, and max decode time per image

## Dataset

The [MIDV-500 dataset](https://github.com/fcakyon/midv500) contains 500 video clips covering 50 identity document types (passports, ID cards, driving licences). This benchmark uses the 12 passport document types that contain MRZ zones, totaling 3,600 images across 10 capture-condition subsets.

The expected dataset directory structure:

```
dataset_root/
├── CA/
│   ├── CA05_01.jpg
│   ├── CA05_02.jpg
│   └── ...
├── CS/
│   └── ...
├── HA/
│   └── ...
...
├── TS/
│   └── ...
└── labels.csv
```

The `labels.csv` file maps each image to its ground-truth MRZ text. A bundled `labels.csv` is included in this directory for the preprocessed passport subset.

## Requirements

- Python 3.8+
- `dynamsoft-capture-vision-bundle` (Dynamsoft Capture Vision SDK)
- `Pillow` (for .tif to .jpg conversion when downloading raw data)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Use an existing dataset

```bash
python benchmark_dcv_mrz.py --dataset /path/to/midv-500-passport
```

The dataset path can also be set via the `MRZ_DATASET_DIR` environment variable:

```bash
export MRZ_DATASET_DIR=/path/to/midv-500-passport
python benchmark_dcv_mrz.py
```

### Option 2: Download the dataset automatically

```bash
# Download 1 passport type for a quick speed test (no ground truth)
python benchmark_dcv_mrz.py --download --download-limit 1 --no-ground-truth

# Download 3 passport types for a larger speed test
python benchmark_dcv_mrz.py --download --download-limit 3 --no-ground-truth

# Download all 12 passport types (~2 GB)
python benchmark_dcv_mrz.py --download --no-ground-truth
```

The download fetches passport document type archives from the MIDV-500 FTP server (`ftp://smartengines.com/midv-500/dataset/`), extracts `.tif` images, and converts them to `.jpg` using Pillow. Raw downloaded data is kept in the `_raw/` subdirectory so re-running does not require re-downloading.

The bundled `labels.csv` uses a preprocessed directory naming scheme (e.g., `CA/CA05_01.jpg`) that does not match the raw MIDV-500 directory structure (e.g., `05_aze_passport/05_aze_passport_001.jpg`). For downloaded data, use `--no-ground-truth` to run a speed-only benchmark. For accuracy comparison, use a preprocessed dataset with `--dataset /path/to/midv-500-passport`.

### Option 3: Speed-only benchmark (no ground truth)

If you have images but no `labels.csv`, run in speed-only mode to measure decode time and success rate without accuracy comparison:

```bash
python benchmark_dcv_mrz.py --dataset /path/to/images --no-ground-truth
```

### Quick smoke test

Run the benchmark on only 5 images to verify everything works:

```bash
python benchmark_dcv_mrz.py --dataset /path/to/midv-500-passport --limit 5 --output benchmark_report_dcv_python
```

This produces a `benchmark_report_dcv_python/` folder containing `report.json` and `report.html` with results for 5 images. On a clean dataset, expect 100% exact accuracy at ~200 ms per image.

### All command-line options

```
--dataset PATH          Dataset root folder (or set MRZ_DATASET_DIR env var)
--csv PATH              Ground-truth CSV path (default: <dataset>/labels.csv)
--output PATH           Output folder for reports (default: benchmark_report_dcv_python)
--runs N                Decode each image N times, keep best timing (default: 1)
--limit N               Only process first N images for smoke testing
--license KEY           Dynamsoft license key (default: public trial license)
--template NAME         Capture Vision template name (default: ReadPassportAndId)
--download              Download MIDV-500 passport dataset before benchmarking
--download-limit N      Limit download to N passport types (0 = all 12)
--no-ground-truth       Run without ground-truth comparison (speed-only)
```

## Output

The benchmark generates two files in the output directory:

### report.json

Machine-readable JSON with:

- Summary statistics (accuracy, success rate, timing percentiles)
- Per-image results (recognized MRZ, ground truth, match rate, timing)
- Run metadata (dataset path, timestamps, SDK template)

### report.html

A visual dashboard with:

- Summary cards (exact accuracy, success rate, average match rate, timing)
- Timing distribution histogram (SVG)
- Per-image detail table with pass/fail indicators and match bars

## License

The Dynamsoft Capture Vision SDK requires a license key. A public trial license is included by default. For production use, [get a 30-day free trial license](https://www.dynamsoft.com/customer/license/trialLicense/?product=dcv&package=cross-platform).

## Files

```
benchmark_dcv_mrz.py    Main benchmark script
requirements.txt        Python dependencies
labels.csv              Bundled ground-truth MRZ labels for the MIDV-500 passport subset
benchmark_report_dcv_python/        Smoke test report (5 images)
benchmark_report_dcv_python_full/   Full dataset report (3600 images)
```

## Dataset Source

The MIDV-500 dataset is publicly available at:
https://github.com/fcakyon/midv500

Original dataset DOI: https://doi.org/10.18287/2412-6179-2019-43-5-818-824

## Blog
[How to Benchmark Passport MRZ Recognition Accuracy on MIDV-500 with Python](https://www.dynamsoft.com/codepool/benchmark-mrz-recognition-midv500-dataset-python.html)
