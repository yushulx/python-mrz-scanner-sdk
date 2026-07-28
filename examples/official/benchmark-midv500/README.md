# Dynamsoft Capture Vision MRZ Benchmark (Python)

Benchmark the **Dynamsoft Capture Vision** Python SDK for MRZ recognition on a curated MIDV-500 subset.

https://github.com/user-attachments/assets/12334f48-2421-4538-ad39-5bc5e1a0c7fb

## Overview

The preprocessed MIDV-500 MRZ subset contains 3,600 labeled images. During audit, only 285 images were removed from the scoring denominator because the pixels do not support a complete, scoreable MRZ:

- 60 images from `PA17` and `PS17` do not contain a complete MRZ.
- 225 early `PA`/`PS` frames have the MRZ cropped out or not yet visible.

The benchmark now uses the curated `labels.csv` in this project, containing 3,315 scoreable MRZ images. Difficult images with a visible MRZ remain in the benchmark even when the SDK fails to decode them.

The curated set includes 12 MIDV-500 document groups: Azerbaijan passport (`05`), Brazil passport (`06`), Czech passport (`11`), German new passport (`16`), German old passport (`17`), Algerian document with an ID-card style MRZ (`18`), Greek passport (`25`), Croatian passport (`27`), Hungarian passport (`28`), Latvian passport (`32`), Moldovan passport (`34`), and Serbian passport (`41`).

Audit artifacts:

- `assets/midv500_mrz_dataset_audit.json` - audit rules, counts, and before/after summaries
- `assets/midv500_mrz_exclusions.csv` - every excluded image and reason
- `assets/mrz-benchmark-demo.mp4` - short benchmark/audit demo video

## Current Results

The full run below uses the updated all-visible-MRZ curation policy (3,315 images):

| Metric | Original 3,600 labels | Curated 3,315-image benchmark |
|---|---:|---:|
| Exact MRZ matches | 1,603 (44.5%) | 1,602 (48.3%) |
| Successful decodes | 2,139 (59.4%) | 2,128 (64.2%) |
| Average match rate | 53.6% | 58.1% |
| Average decode time | 386.9 ms | 365.2 ms |
| P50 decode time | 283.1 ms | 258.9 ms |
| P95 decode time | 899.6 ms | 919.3 ms |
| P99 decode time | 1,271.0 ms | 1,283.7 ms |

The curated benchmark denominator is smaller but more defensible: it measures MRZ recognition only on images where a complete MRZ is actually visible and scoreable.

The result should be read as a strict exact-match benchmark, not just a detection benchmark. `success_rate` counts any returned MRZ text, while `exact_accuracy` requires the normalized MRZ to match the ground truth exactly. In the latest full run, 526 images returned partial MRZ text but did not match every character. Runtime remained mostly sub-second: 79.1% of images finished in under 500 ms, and only 3.6% exceeded 1,000 ms. The strongest capture conditions were `TA` and `TS`; `PA` and `PS` remained the hardest because of motion, angle, partial entry into frame, and blur.

## Open-Source Comparison (PassportEye, FastMRZ)

The same curated benchmark was run against the two most popular open-source Python MRZ libraries, using the same 3,315 images, the same `labels.csv`, the same metrics, and the same machine:

| Metric | Dynamsoft Capture Vision | PassportEye 2.2.2 | FastMRZ 2.1.2 |
|---|---:|---:|---:|
| Exact MRZ matches | **1,602 (48.33%)** | 9 (0.27%) | 242 (7.30%) |
| Successful decodes | 2,128 (64.19%) | **2,688 (81.09%)** | 1,005 (30.32%) |
| Average match rate | **58.09%** | 32.43% | 19.23% |
| Average decode time | **365.2 ms** | 798.5 ms | 484.0 ms |
| P50 decode time | **258.9 ms** | 748.3 ms | 479.6 ms |
| P95 decode time | 919.3 ms | 1,449.5 ms | **639.9 ms** |

Both open-source libraries are Tesseract-OCR pipelines. MIDV-500 frames come from mobile-phone video clips (glare, motion blur, steep angles, cluttered desks), which is exactly the input Tesseract handles worst: PassportEye returns text for most images but misreads `<` as `K` on slanted OCR-B lines, while FastMRZ's strict line filter keeps it silent on 69.7% of frames. The comparison scripts measure both libraries through their raw MRZ text output so MIDV-500's synthetic specimen MRZ data cannot be rejected by their ICAO checksum validators.

Reproduce the comparison runs:

```bash
pip install -r requirements-compare.txt
# FastMRZ also needs the custom mrz language file (already bundled in tessdata/):
# curl -L -o tessdata/mrz.traineddata https://github.com/sivakumar-mahalingam/fastmrz/raw/main/tessdata/mrz.traineddata

python benchmark_passporteye_mrz.py --dataset /path/to/midv-500-mrz --output benchmark_report_passporteye_python_full
python benchmark_fastmrz_mrz.py --dataset /path/to/midv-500-mrz --output benchmark_report_fastmrz_python_full
```

Both scripts default to the bundled curated `labels.csv` and support `--limit N` for smoke tests. A system [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html) installation is required on the PATH.

## Dataset Layout

Use the preprocessed MIDV-500 MRZ image folder:

```text
dataset_root/
  CA/
    CA05_01.jpg
    CA05_02.jpg
    ...
  CS/
  HA/
  HS/
  KA/
  KS/
  PA/
  PS/
  TA/
  TS/
```

By default, the script uses the bundled curated `labels.csv` from this project. This avoids accidentally scoring against the unfiltered source labels.

## Requirements

- Python 3.8+
- `dynamsoft-capture-vision-bundle`
- `Pillow` for `.tif` to `.jpg` conversion when downloading raw data

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the curated accuracy benchmark:

```bash
python benchmark_dcv_mrz.py --dataset /path/to/midv-500-mrz --output benchmark_report_dcv_python_full
```

Use an explicit ground-truth CSV if needed:

```bash
python benchmark_dcv_mrz.py --dataset /path/to/midv-500-mrz --csv labels.csv
```

Run a quick smoke test if you want a small local sanity check:

```bash
python benchmark_dcv_mrz.py --dataset /path/to/midv-500-mrz --limit 5 --output benchmark_report_dcv_python
```

Run speed-only mode for images without ground truth:

```bash
python benchmark_dcv_mrz.py --dataset /path/to/images --no-ground-truth
```

Download raw MIDV-500 source archives for speed-only testing:

```bash
python benchmark_dcv_mrz.py --download --download-limit 1 --no-ground-truth
python benchmark_dcv_mrz.py --download --no-ground-truth
```

Downloaded raw data uses MIDV-500 archive folder names, not the curated `CA/`, `CS/`, etc. label paths, so use `--no-ground-truth` unless you preprocess it into the expected structure.

## Command-Line Options

```text
--dataset PATH          Dataset root folder (or set MRZ_DATASET_DIR)
--csv PATH              Ground-truth CSV path (default: bundled curated labels.csv)
--output PATH           Output folder for report.json and report.html
--runs N                Decode each image N times, keep best timing
--limit N               Process only first N matched images
--license KEY           Dynamsoft license key
--template NAME         Capture Vision template name
--download              Download MIDV-500 source images before benchmarking
--download-limit N      Limit download to N source document groups
--no-ground-truth       Run without ground-truth comparison
```

## Output

The benchmark writes:

- `report.json` - machine-readable summary and per-image results
- `report.html` - visual dashboard with metrics, timing distribution, and per-image details

The included `benchmark_report_dcv_python_full/` report uses the curated 3,315-image benchmark set.

## Files

```text
benchmark_dcv_mrz.py                         Main benchmark script (Dynamsoft Capture Vision)
benchmark_passporteye_mrz.py                 Open-source comparison script (PassportEye)
benchmark_fastmrz_mrz.py                     Open-source comparison script (FastMRZ)
requirements.txt                             Python dependencies (Dynamsoft benchmark)
requirements-compare.txt                     Python dependencies (open-source comparison)
tessdata/mrz.traineddata                     Custom Tesseract language file required by FastMRZ
labels.csv                                   Curated 3,315-image MRZ ground truth
assets/midv500_mrz_dataset_audit.json        Dataset audit summary and rules
assets/midv500_mrz_exclusions.csv            Excluded image manifest
assets/midv500-mrz-benchmark-cover.png       Cover image
assets/mrz-benchmark-demo.mp4                Demo video
benchmark_report_dcv_python_full/            Curated full report (Dynamsoft Capture Vision)
benchmark_report_passporteye_python_full/    Curated full report (PassportEye)
benchmark_report_fastmrz_python_full/        Curated full report (FastMRZ)
```

## Dataset Source

The MIDV-500 dataset is publicly available at:
https://github.com/fcakyon/midv500

Original dataset DOI: https://doi.org/10.18287/2412-6179-2019-43-5-818-824

## Blog
[How to Benchmark Passport MRZ Recognition Accuracy on MIDV-500 with Python](https://www.dynamsoft.com/codepool/benchmark-mrz-recognition-midv500-dataset-python.html)
