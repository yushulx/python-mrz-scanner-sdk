#!/usr/bin/env python3
"""
Benchmark Dynamsoft Capture Vision MRZ decoding on the MIDV-500 passport dataset.

The MIDV-500 dataset is a publicly available collection of 500 video clips
covering 50 identity document types (passports, ID cards, driving licences).
This benchmark evaluates the Dynamsoft Capture Vision Python SDK on the passport
subset and generates:

1) report.json — full machine-readable benchmark output
2) report.html — polished visual report with accuracy and time-cost analysis

Dataset source: https://github.com/fcakyon/midv500

Usage examples:

  # Use an existing preprocessed dataset
  python benchmark_dcv_mrz.py --dataset /path/to/midv-500-passport

  # Smoke test with 5 images
  python benchmark_dcv_mrz.py --dataset /path/to/midv-500-passport --limit 5

  # Download a subset of the MIDV-500 dataset and run the benchmark
  python benchmark_dcv_mrz.py --download --download-limit 3

  # Full run with multiple decode passes
  python benchmark_dcv_mrz.py --dataset /path/to/data --runs 3

  # Speed-only benchmark (no ground truth comparison)
  python benchmark_dcv_mrz.py --dataset /path/to/images --no-ground-truth
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import shutil
import statistics
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.request import urlopen

# ---------------------------------------------------------------------------
# SDK imports — fail fast with a helpful message if not installed
# ---------------------------------------------------------------------------

try:
    from dynamsoft_capture_vision_bundle import (
        CaptureVisionRouter,
        EnumErrorCode,
        EnumValidationStatus,
        FileImageTag,
        LicenseManager,
    )
except ImportError as ex:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: dynamsoft_capture_vision_bundle.\n"
        "Install with: pip install dynamsoft-capture-vision-bundle\n"
        f"Import error: {ex}"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LICENSE = "DLS2eyJvcmdhbml6YXRpb25JRCI6IjIwMDAwMSJ9"
DEFAULT_TEMPLATE = "ReadPassportAndId"
DEFAULT_OUTPUT_DIR = Path("benchmark_report_dcv_python")

# Passport document types in the MIDV-500 dataset.
# Each entry maps the midv500 folder name to the benchmark's 2-letter code.
# The full MIDV-500 dataset has 50 types; only the 12 passport types below
# contain MRZ zones and are used for MRZ benchmarking.
PASSPORT_TYPES: List[Tuple[str, str]] = [
    ("05_aze_passport", "05"),
    ("06_bra_passport", "06"),
    ("11_cze_passport", "11"),
    ("16_deu_passport_new", "16"),
    ("17_deu_passport_old", "17"),
    ("18_dza_passport", "18"),
    ("25_grc_passport", "25"),
    ("27_hrv_passport", "27"),
    ("28_hun_passport", "28"),
    ("32_lva_passport", "32"),
    ("34_mda_passport", "34"),
    ("41_srb_passport", "41"),
]

# FTP base for downloading individual document type archives.
MIDV500_FTP_BASE = "ftp://smartengines.com/midv-500/dataset"

# Bundled labels.csv — ships with this script for ground-truth MRZ labels.
BUNDLED_LABELS_CSV = Path(__file__).resolve().parent / "labels.csv"

# Supported image extensions (including .tif from the raw MIDV-500 dataset).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ImageRecord:
    """A single image paired with its ground-truth MRZ text."""
    key: str
    path: Path
    truth_mrz: str


@dataclass
class ImageResult:
    """Benchmark result for a single image."""
    key: str
    success: bool
    error: Optional[str]
    recognized_mrz: Optional[str]
    truth_mrz: str
    match_rate: float
    exact_match: bool
    run_ms: Optional[float]
    page_number: int


@dataclass
class SummaryStats:
    """Aggregate statistics across all benchmarked images."""
    total_images: int
    success_count: int
    exact_count: int
    avg_match_rate: float
    avg_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    total_wall_ms: float


# ---------------------------------------------------------------------------
# Dataset download and preparation
# ---------------------------------------------------------------------------

def download_and_prepare_dataset(
    target_dir: Path,
    limit: int = 0,
) -> Path:
    """
    Download a subset of the MIDV-500 passport dataset and prepare it for
    benchmarking.

    The full MIDV-500 dataset is ~10 GB across 50 document types.  This
    function downloads only the passport types (12 types, ~2 GB total) and
    optionally limits to the first *limit* types for a quick smoke test.

    After downloading, the raw .tif images are converted to .jpg and organised
    into the directory structure expected by the benchmark.  The bundled
    labels.csv is copied to the dataset root so that ground-truth MRZ labels
    are available.

    Args:
        target_dir: Root directory for the prepared dataset.
        limit: If > 0, download only the first N passport types.

    Returns:
        The path to the prepared dataset directory.
    """
    types_to_download = PASSPORT_TYPES[:limit] if limit > 0 else PASSPORT_TYPES

    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    raw_dir = target_dir / "_raw"
    raw_dir.mkdir(exist_ok=True)

    print(f"\n--- Downloading MIDV-500 passport subset ---")
    print(f"Target: {target_dir}")
    print(f"Types:  {len(types_to_download)} passport document type(s)\n")

    for folder_name, type_code in types_to_download:
        zip_url = f"{MIDV500_FTP_BASE}/{folder_name}.zip"
        zip_path = raw_dir / f"{folder_name}.zip"
        extract_dir = raw_dir / folder_name

        if extract_dir.exists() and any(
            p for p in extract_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in (".tif", ".tiff")
        ):
            print(f"  [skip] {folder_name} (already extracted)")
            continue

        print(f"  [download] {folder_name} ...")
        try:
            _download_zip(zip_url, zip_path)
            print(f"  [extract]  {folder_name} ...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(raw_dir)
            zip_path.unlink(missing_ok=True)
        except Exception as ex:
            print(f"  [error]    {folder_name}: {ex}")
            print(f"             You can manually download from: {zip_url}")
            zip_path.unlink(missing_ok=True)
            continue

    # Convert and organise images
    print(f"\n--- Preparing images ---")
    _convert_and_organize(raw_dir, target_dir, types_to_download)

    # Copy bundled labels.csv (works with the preprocessed dataset structure)
    dest_csv = target_dir / "labels.csv"
    if BUNDLED_LABELS_CSV.exists():
        if not dest_csv.exists():
            shutil.copy2(BUNDLED_LABELS_CSV, dest_csv)
            print(f"\nCopied ground-truth labels.csv to {dest_csv}")
    else:
        print(f"\n[warning] Bundled labels.csv not found at {BUNDLED_LABELS_CSV}")

    # Check if any converted images actually match the labels.csv entries.
    # The bundled labels.csv was built for a preprocessed version of the dataset
    # with a specific directory naming scheme (CA/, CS/, etc.). Downloaded raw
    # data uses a different scheme (05_aze_passport/, etc.), so the labels may
    # not match. In that case, inform the user to use --no-ground-truth.
    if dest_csv.exists():
        truth_map = load_ground_truth(dest_csv)
        all_images = discover_images(target_dir)
        matched = sum(
            1 for p in all_images
            if p.relative_to(target_dir).as_posix().lower() in truth_map
        )
        if matched == 0:
            print(f"\n[info] The bundled labels.csv does not match the downloaded")
            print(f"       image directory structure ({len(all_images)} images found,")
            print(f"       0 matched labels.csv entries).")
            print(f"       Run with --no-ground-truth for a speed-only benchmark,")
            print(f"       or use a preprocessed dataset with --dataset /path/to/data")
            print(f"       for accuracy comparison.")
        else:
            print(f"\n{matched}/{len(all_images)} images matched labels.csv entries.")

    # Keep the raw directory so re-download is not needed if conversion
    # needs to be re-run. The raw .tif files are large but re-downloading
    # from the FTP server takes much longer than disk space.
    print(f"\nRaw data kept at: {raw_dir}")
    print(f"(Delete manually if you need to free disk space)")
    print(f"\nDataset ready at: {target_dir}\n")
    return target_dir


def _download_zip(url: str, dest: Path) -> None:
    """Download a zip file from a URL to a local path."""
    with urlopen(url, timeout=300) as resp:
        with dest.open("wb") as fp:
            while True:
                chunk = resp.read(io.DEFAULT_BUFFER_SIZE)
                if not chunk:
                    break
                fp.write(chunk)


def _convert_and_organize(
    raw_dir: Path,
    target_dir: Path,
    types: List[Tuple[str, str]],
) -> None:
    """
    Convert .tif images from the raw MIDV-500 structure to .jpg in the
    benchmark's expected directory layout.

    The raw structure is::

        raw_dir/05_aze_passport/images/05_aze_passport_*.tif

    The benchmark expects::

        target_dir/CA/CA05_01.jpg
        target_dir/CS/CS05_01.jpg
        ...

    Because the exact mapping between raw capture-condition indices and the
    benchmark's 2-letter codes (CA, CS, ...) is not publicly documented, this
    function organises images into directories named by the midv500 folder
    name (e.g. ``05_aze_passport/``).  The labels.csv bundled with this script
    will match images whose relative path follows the ``<code>/<code>##_##.jpg``
    pattern used in the preprocessed dataset.

    If the raw image filenames do not match the labels.csv entries, the
    benchmark can still run in ``--no-ground-truth`` mode (speed-only).
    """
    try:
        from PIL import Image
    except ImportError:
        print("  [warning] Pillow not installed — skipping .tif conversion.")
        print("            Install with: pip install Pillow")
        print("            The benchmark will only find .jpg/.png images.")
        return

    for folder_name, type_code in types:
        type_dir = raw_dir / folder_name
        if not type_dir.exists():
            print(f"  [skip] {folder_name}: directory not found")
            continue

        # The MIDV-500 zip may store .tif files in images/ subdirectories,
        # or in nested subdirectories. Search recursively.
        tif_files = sorted(
            p for p in type_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in (".tif", ".tiff")
        )

        if not tif_files:
            print(f"  [skip] {folder_name}: no .tif/.tiff files found")
            continue

        out_dir = target_dir / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)

        converted = 0
        for i, tif_path in enumerate(tif_files, start=1):
            jpg_name = f"{folder_name}_{i:03d}.jpg"
            jpg_path = out_dir / jpg_name
            if jpg_path.exists():
                converted += 1
                continue
            try:
                img = Image.open(tif_path)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(jpg_path, "JPEG", quality=90)
                converted += 1
            except Exception as ex:
                print(f"  [error] converting {tif_path.name}: {ex}")

        print(f"  [done] {folder_name}: {converted}/{len(tif_files)} images converted")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    # Resolve default dataset path from env var or fall back to a relative dir.
    env_dataset = os.environ.get("MRZ_DATASET_DIR")
    default_dataset = Path(env_dataset) if env_dataset else None

    parser = argparse.ArgumentParser(
        description=(
            "Benchmark Dynamsoft Capture Vision MRZ on the MIDV-500 passport "
            "dataset. The MIDV-500 dataset is available at "
            "https://github.com/fcakyon/midv500"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Run on an existing dataset\n"
            "  python benchmark_dcv_mrz.py --dataset /path/to/midv-500-passport\n\n"
            "  # Download 3 passport types and benchmark\n"
            "  python benchmark_dcv_mrz.py --download --download-limit 3\n\n"
            "  # Speed-only test (no ground truth)\n"
            "  python benchmark_dcv_mrz.py --dataset /path/to/images --no-ground-truth\n"
        ),
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=default_dataset,
        help=(
            "Dataset root folder containing images and labels.csv. "
            "Can also be set via the MRZ_DATASET_DIR environment variable. "
            "Required unless --download is used."
        ),
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Ground-truth CSV path (default: <dataset>/labels.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output folder for report.json and report.html (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Decode each image N times and keep the best successful timing (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process first N images for quick smoke test",
    )
    parser.add_argument(
        "--license",
        type=str,
        default=DEFAULT_LICENSE,
        help="Dynamsoft license key (default: public trial license)",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=DEFAULT_TEMPLATE,
        help=f"Capture Vision template name (default: {DEFAULT_TEMPLATE})",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help=(
            "Download the MIDV-500 passport dataset before running the benchmark. "
            "The dataset source is https://github.com/fcakyon/midv500"
        ),
    )
    parser.add_argument(
        "--download-limit",
        type=int,
        default=0,
        help=(
            "When using --download, only download the first N passport document types. "
            "Useful for quick testing since the full dataset is large (~2 GB for "
            "passport types only). 0 = download all 12 passport types."
        ),
    )
    parser.add_argument(
        "--no-ground-truth",
        action="store_true",
        help=(
            "Run the benchmark without ground-truth MRZ comparison. "
            "Use this when you have images but no labels.csv. "
            "Only timing and success rate will be reported."
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# MRZ text utilities
# ---------------------------------------------------------------------------

def normalize_mrz(text: Optional[str]) -> str:
    """Normalise MRZ text: uppercase, keep only alphanumerics and '<'."""
    if not text:
        return ""
    return "".join(ch for ch in text.upper() if ch.isalnum() or ch == "<")


def match_rate(a: Optional[str], b: Optional[str]) -> float:
    """
    Character-level match rate between two MRZ strings.

    Returns a float in [0, 1] where 1.0 means an exact match.
    """
    norm_a = normalize_mrz(a)
    norm_b = normalize_mrz(b)
    if not norm_a or not norm_b:
        return 0.0
    limit = max(len(norm_a), len(norm_b))
    same = 0
    for idx in range(limit):
        ca = norm_a[idx] if idx < len(norm_a) else None
        cb = norm_b[idx] if idx < len(norm_b) else None
        if ca is not None and cb is not None and ca == cb:
            same += 1
    return same / limit if limit else 0.0


# ---------------------------------------------------------------------------
# SDK result extraction
# ---------------------------------------------------------------------------

def _is_warning_or_ok(code: int) -> bool:
    """Check if an SDK error code represents success or a non-fatal warning."""
    return code in (EnumErrorCode.EC_OK, EnumErrorCode.EC_UNSUPPORTED_JSON_KEY_WARNING)


def _safe_field(item, name: str) -> Optional[str]:
    """Safely extract a field value from a parsed result item."""
    try:
        value = item.get_field_value(name)
        if value is None:
            return None
        try:
            status = item.get_field_validation_status(name)
            if status == EnumValidationStatus.VS_FAILED:
                return None
        except Exception:
            pass
        return str(value)
    except Exception:
        return None


def extract_mrz_from_captured_result(captured_result) -> Optional[str]:
    """
    Extract MRZ text (line1/line2/line3) from a Dynamsoft Capture Vision
    captured result object.
    """
    try:
        if not _is_warning_or_ok(captured_result.get_error_code()):
            return None
    except Exception:
        return None

    parsed = captured_result.get_parsed_result()
    if parsed is None:
        return None

    try:
        parsed_error = parsed.get_error_code()
        if not _is_warning_or_ok(parsed_error):
            return None
    except Exception:
        pass

    items = parsed.get_items() if hasattr(parsed, "get_items") else None
    if not items:
        return None

    for item in items:
        lines: List[str] = []
        for key in ("line1", "line2", "line3"):
            value = _safe_field(item, key)
            if value:
                lines.append(value)

        if not lines:
            try:
                names = item.get_all_field_names()
                if names:
                    for name in names:
                        if str(name).lower().startswith("line"):
                            value = _safe_field(item, str(name))
                            if value:
                                lines.append(value)
            except Exception:
                pass

        if lines:
            return "\n".join(lines)

    return None


# ---------------------------------------------------------------------------
# Ground-truth and image discovery
# ---------------------------------------------------------------------------

def load_ground_truth(csv_path: Path) -> Dict[str, str]:
    """
    Load ground-truth MRZ labels from a CSV file.

    The CSV has two columns: image path and MRZ text.  The image path is
    normalised to the last two path components (e.g. ``ca/ca05_01.jpg``)
    so that it matches regardless of where the dataset is stored on disk.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    mapping: Dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        for row in reader:
            if not row or len(row) < 2:
                continue
            image_path = row[0].strip()
            mrz_label = row[1].strip()
            if not image_path or not mrz_label:
                continue
            if image_path.lower().startswith("imagepath"):
                continue

            normalised = image_path.replace("\\", "/").strip("/").lower()
            parts = normalised.split("/")
            key = "/".join(parts[-2:]) if len(parts) >= 2 else normalised
            mapping[key] = mrz_label
    return mapping


def discover_images(dataset_dir: Path) -> List[Path]:
    """
    Recursively discover all supported image files in the dataset directory.

    Supports .jpg, .jpeg, .png, .bmp, .webp, .gif, .tif, and .tiff formats.
    """
    images = [
        p for p in dataset_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    images.sort()
    return images


def build_records(
    dataset_dir: Path,
    truth_map: Dict[str, str],
    limit: int = 0,
) -> List[ImageRecord]:
    """
    Build a list of ImageRecords by aligning discovered images with
    ground-truth labels.  Images without a matching label are skipped.
    """
    records: List[ImageRecord] = []
    for full_path in discover_images(dataset_dir):
        rel = full_path.relative_to(dataset_dir).as_posix().lower()
        truth = truth_map.get(rel)
        if truth is None:
            continue
        records.append(ImageRecord(key=rel, path=full_path, truth_mrz=truth))

    if limit > 0:
        records = records[:limit]

    return records


def build_records_no_truth(
    dataset_dir: Path,
    limit: int = 0,
) -> List[ImageRecord]:
    """
    Build ImageRecords without ground-truth labels (speed-only mode).
    Every discovered image is included with an empty truth_mrz string.
    """
    records: List[ImageRecord] = []
    for full_path in discover_images(dataset_dir):
        rel = full_path.relative_to(dataset_dir).as_posix().lower()
        records.append(ImageRecord(key=rel, path=full_path, truth_mrz=""))
    if limit > 0:
        records = records[:limit]
    return records


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def quantile(values: Sequence[float], q: float) -> float:
    """Compute the q-th quantile of a sequence using linear interpolation."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    pos = (len(sorted_vals) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return float(sorted_vals[low])
    frac = pos - low
    return float(sorted_vals[low] * (1 - frac) + sorted_vals[high] * frac)


def build_summary(results: Sequence[ImageResult], wall_ms: float) -> SummaryStats:
    """Compute aggregate statistics from a list of ImageResult objects."""
    total = len(results)
    success_count = sum(1 for row in results if row.success)
    exact_count = sum(1 for row in results if row.exact_match)
    avg_match = sum(row.match_rate for row in results) / total if total else 0.0

    timings = [row.run_ms for row in results if row.run_ms is not None]
    if timings:
        avg_ms = float(statistics.fmean(timings))
        min_ms = float(min(timings))
        max_ms = float(max(timings))
        p50 = quantile(timings, 0.50)
        p95 = quantile(timings, 0.95)
        p99 = quantile(timings, 0.99)
    else:
        avg_ms = min_ms = max_ms = p50 = p95 = p99 = 0.0

    return SummaryStats(
        total_images=total,
        success_count=success_count,
        exact_count=exact_count,
        avg_match_rate=avg_match,
        avg_ms=avg_ms,
        min_ms=min_ms,
        max_ms=max_ms,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        total_wall_ms=wall_ms,
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def pct(value: float) -> str:
    """Format a fraction as a percentage string."""
    return f"{value * 100:.2f}%"


def ms(value: float) -> str:
    """Format milliseconds with thousands separator."""
    return f"{round(value):,} ms"


# ---------------------------------------------------------------------------
# SVG chart generation
# ---------------------------------------------------------------------------

def histogram_svg(
    values: Sequence[float],
    color: str,
    width: int = 800,
    height: int = 180,
    bins: int = 24,
) -> str:
    """Generate an SVG histogram of timing values."""
    if not values:
        return '<div class="empty-chart">No timing data</div>'

    min_v = min(values)
    max_v = max(values)
    if math.isclose(min_v, max_v):
        max_v = min_v + 1

    counts = [0] * bins
    for val in values:
        idx = int((val - min_v) / (max_v - min_v) * bins)
        idx = min(bins - 1, max(0, idx))
        counts[idx] += 1

    max_count = max(counts) if counts else 1
    bar_w = width / bins

    bars = []
    for i, count in enumerate(counts):
        h = 4 if max_count == 0 else (count / max_count) * (height - 24)
        x = i * bar_w + 1
        y = height - h - 16
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(1.0, bar_w - 2):.2f}" '
            f'height="{h:.2f}" rx="2" fill="{color}" opacity="0.84" />'
        )

    labels = (
        f'<text x="2" y="{height - 2}" class="axis-label">{ms(min_v)}</text>'
        f'<text x="{width - 2}" y="{height - 2}" class="axis-label" text-anchor="end">{ms(max_v)}</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="Timing histogram">'
        + "".join(bars)
        + labels
        + "</svg>"
    )


def progress_bar_svg(match_rate_value: float, width: int = 140, height: int = 10) -> str:
    """Generate a small SVG progress bar for match rate."""
    filled = max(0.0, min(1.0, match_rate_value)) * width
    color = "#17c964" if match_rate_value >= 0.99999 else (
        "#f5a524" if match_rate_value >= 0.9 else "#f31260"
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" class="mini-bar" aria-hidden="true">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="5" fill="#2a344f" opacity="0.3"></rect>'
        f'<rect x="0" y="0" width="{filled:.1f}" height="{height}" rx="5" fill="{color}"></rect>'
        "</svg>"
    )


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------

def build_html(report: dict, summary: SummaryStats) -> str:
    """Generate a full HTML dashboard from the benchmark report."""
    results: List[dict] = report["results"]
    timings = [float(r["run_ms"]) for r in results if r["run_ms"] is not None]

    has_ground_truth = report.get("has_ground_truth", True)

    rows_html = []
    for row in results:
        if has_ground_truth:
            exact_icon = "PASS" if row["exact_match"] else "MISS"
            status_cls = "pass" if row["exact_match"] else (
                "warn" if row["success"] else "fail"
            )
        else:
            exact_icon = "OK" if row["success"] else "ERR"
            status_cls = "pass" if row["success"] else "fail"

        recognized = row["recognized_mrz"] or ""
        recognized_short = recognized.replace("\n", " ")[:64]
        if recognized and len(recognized.replace("\n", " ")) > 64:
            recognized_short += "..."

        truth_display = (
            escape(row["truth_mrz"].replace("\n", " ")[:64]) + "..."
            if has_ground_truth and row.get("truth_mrz")
            else "-"
        )

        rows_html.append(
            "<tr>"
            f'<td class="path">{escape(row["key"])}</td>'
            f'<td><span class="tag {status_cls}">{exact_icon}</span></td>'
            f"<td>{pct(float(row['match_rate']))}</td>"
            f'<td>{progress_bar_svg(float(row["match_rate"]))}</td>'
            f'<td>{ms(float(row["run_ms"])) if row["run_ms"] is not None else "-"}</td>'
            f'<td class="mono" title="{escape(recognized)}">{escape(recognized_short) if recognized_short else "-"}</td>'
            f'<td class="mono">{truth_display}</td>'
            "</tr>"
        )

    histogram = histogram_svg(timings, color="#ff7a18")

    started = escape(report["started_at"])
    finished = escape(report["finished_at"])
    dataset = escape(report["dataset"])

    success_rate = summary.success_count / summary.total_images if summary.total_images else 0.0
    exact_rate = summary.exact_count / summary.total_images if summary.total_images else 0.0

    exact_card = f"""
      <article class="card">
        <div class="label">Exact Accuracy</div>
        <div class="value">{pct(exact_rate)}</div>
        <div class="note">{summary.exact_count:,} / {summary.total_images:,} exact MRZ matches</div>
      </article>""" if has_ground_truth else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dynamsoft MRZ Benchmark Report</title>
  <style>
    :root {{
      --bg:#0b1020;
      --bg-2:#111830;
      --card:#161f3d;
      --card-2:#1a264b;
      --text:#e8ecff;
      --muted:#9fb0dd;
      --accent:#ff7a18;
      --accent-2:#ffd166;
      --good:#17c964;
      --warn:#f5a524;
      --bad:#f31260;
      --line:#2a3660;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      color:var(--text);
      background:
        radial-gradient(circle at 12% 12%, rgba(255,122,24,.26), transparent 38%),
        radial-gradient(circle at 88% 0%, rgba(255,209,102,.17), transparent 34%),
        linear-gradient(165deg, var(--bg) 0%, #091129 45%, #060c1b 100%);
      font-family:"Segoe UI Variable Display","Aptos","Trebuchet MS",sans-serif;
      line-height:1.45;
    }}
    .wrap {{ max-width:1280px; margin:0 auto; padding:28px 20px 34px; }}
    .hero {{
      background:linear-gradient(135deg, rgba(255,122,24,.20), rgba(255,122,24,.04));
      border:1px solid rgba(255,122,24,.38);
      border-radius:24px;
      padding:24px 26px;
      box-shadow:0 18px 36px rgba(0,0,0,.28);
      backdrop-filter: blur(8px);
    }}
    .kicker {{
      letter-spacing:.14em;
      text-transform:uppercase;
      color:var(--accent-2);
      font-size:12px;
      margin-bottom:10px;
      font-weight:700;
    }}
    h1 {{ margin:0; font-size:34px; line-height:1.2; font-weight:800; }}
    .sub {{ color:var(--muted); margin-top:10px; font-size:14px; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }}
    .pill {{
      font-size:12px;
      color:#d8e2ff;
      border:1px solid var(--line);
      background:rgba(10,16,34,.52);
      padding:6px 10px;
      border-radius:999px;
    }}
    .grid {{
      margin-top:18px;
      display:grid;
      gap:14px;
      grid-template-columns:repeat(auto-fit, minmax(210px, 1fr));
    }}
    .card {{
      background:linear-gradient(155deg, var(--card), var(--card-2));
      border:1px solid var(--line);
      border-radius:18px;
      padding:16px;
      box-shadow:0 12px 24px rgba(0,0,0,.22);
    }}
    .label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    .value {{ font-size:30px; font-weight:800; margin-top:6px; }}
    .note {{ color:var(--muted); font-size:13px; margin-top:6px; }}
    .chart-card {{ margin-top:14px; }}
    .chart {{ width:100%; display:block; }}
    .axis-label {{ fill:var(--muted); font-size:12px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:14px; }}
    thead th {{
      text-align:left;
      color:var(--muted);
      font-size:12px;
      letter-spacing:.08em;
      text-transform:uppercase;
      padding:10px 10px;
      border-bottom:1px solid var(--line);
      position:sticky;
      top:0;
      background:rgba(15,23,47,.95);
      backdrop-filter: blur(4px);
    }}
    tbody td {{
      padding:9px 10px;
      border-bottom:1px solid rgba(42,54,96,.6);
      font-size:13px;
      vertical-align:middle;
    }}
    tbody tr:hover {{ background:rgba(30,45,82,.4); }}
    .path {{ color:#dae4ff; font-family:"Cascadia Mono","Consolas",monospace; font-size:12px; }}
    .mono {{ font-family:"Cascadia Mono","Consolas",monospace; font-size:12px; color:#ced8fb; }}
    .table-wrap {{ max-height:620px; overflow:auto; border:1px solid var(--line); border-radius:14px; margin-top:10px; }}
    .tag {{
      font-size:11px;
      font-weight:700;
      border-radius:999px;
      padding:4px 8px;
      border:1px solid transparent;
      display:inline-block;
      min-width:50px;
      text-align:center;
    }}
    .pass {{ color:#062f1b; background:rgba(23,201,100,.9); border-color:rgba(23,201,100,.8); }}
    .warn {{ color:#3a2b00; background:rgba(245,165,36,.88); border-color:rgba(245,165,36,.8); }}
    .fail {{ color:#fff; background:rgba(243,18,96,.85); border-color:rgba(243,18,96,.8); }}
    .mini-bar {{ width:140px; height:10px; display:block; }}
    .foot {{ margin-top:14px; color:var(--muted); font-size:12px; text-align:center; }}
    .empty-chart {{ color:var(--muted); font-size:13px; padding:16px 0; }}
    @media (max-width:760px) {{
      h1 {{ font-size:28px; }}
      .value {{ font-size:24px; }}
      .wrap {{ padding:16px 12px 26px; }}
      .hero {{ padding:18px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="kicker">Dynamsoft Capture Vision</div>
      <h1>MRZ Benchmark Dashboard</h1>
      <div class="sub">MIDV-500 passport dataset accuracy and time-cost benchmark generated by Python.</div>
      <div class="meta">
        <span class="pill">Dataset: {dataset}</span>
        <span class="pill">Start: {started}</span>
        <span class="pill">End: {finished}</span>
        <span class="pill">Images: {summary.total_images:,}</span>
      </div>
    </section>

    <section class="grid">
      {exact_card}
      <article class="card">
        <div class="label">SDK Success Rate</div>
        <div class="value">{pct(success_rate)}</div>
        <div class="note">{summary.success_count:,} / {summary.total_images:,} successful decodes</div>
      </article>
      <article class="card">
        <div class="label">Average Match Rate</div>
        <div class="value">{pct(summary.avg_match_rate)}</div>
        <div class="note">Character-level match against ground truth</div>
      </article>
      <article class="card">
        <div class="label">Average Time Cost</div>
        <div class="value">{ms(summary.avg_ms)}</div>
        <div class="note">P50 {ms(summary.p50_ms)} · P95 {ms(summary.p95_ms)} · P99 {ms(summary.p99_ms)}</div>
      </article>
      <article class="card">
        <div class="label">Total Elapsed</div>
        <div class="value">{ms(summary.total_wall_ms)}</div>
        <div class="note">Min {ms(summary.min_ms)} · Max {ms(summary.max_ms)}</div>
      </article>
    </section>

    <section class="card chart-card">
      <div class="label">Timing Distribution</div>
      <div class="note">Distribution of per-image best decode time (ms).</div>
      {histogram}
    </section>

    <section class="card" style="margin-top:14px;">
      <div class="label">Per-Image Detail</div>
      <div class="note">Exact pass/fail, match ratio, and timing for every image.</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Image</th>
              <th>Exact</th>
              <th>Match</th>
              <th>Match Bar</th>
              <th>Time</th>
              <th>Recognized MRZ</th>
              <th>Ground Truth</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </section>

    <div class="foot">Generated by benchmark_dcv_mrz.py · Dataset: https://github.com/fcakyon/midv500</div>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# SDK initialisation and decoding
# ---------------------------------------------------------------------------

def init_dynamsoft_router(license_key: str) -> CaptureVisionRouter:
    """Initialise the Dynamsoft license and create a CaptureVisionRouter."""
    code, message = LicenseManager.init_license(license_key)
    if code not in (EnumErrorCode.EC_OK, EnumErrorCode.EC_LICENSE_WARNING):
        raise RuntimeError(
            f"License initialization failed. code={code}, message={message}"
        )
    return CaptureVisionRouter()


def _page_number(captured_result, fallback: int) -> int:
    """Extract the page number from a captured result's image tag."""
    try:
        tag = captured_result.get_original_image_tag()
        if isinstance(tag, FileImageTag):
            return int(tag.get_page_number()) + 1
    except Exception:
        pass
    return fallback


def decode_once(
    router: CaptureVisionRouter,
    image_path: Path,
    template_name: str,
) -> Tuple[Optional[str], Optional[str], int, float]:
    """
    Decode a single image and return (mrz_text, error, page_number, elapsed_ms).
    """
    start = time.perf_counter()
    result_array = router.capture_multi_pages(str(image_path), template_name)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    results = result_array.get_results() if result_array is not None else None
    if not results:
        return None, "No captured results.", 1, elapsed_ms

    for index, captured in enumerate(results, start=1):
        text = extract_mrz_from_captured_result(captured)
        if text:
            return text, None, _page_number(captured, index), elapsed_ms

    first = results[0]
    try:
        err_text = f"Capture error {first.get_error_code()}: {first.get_error_string()}"
    except Exception:
        err_text = "No parsable MRZ found in captured result."
    return None, err_text, _page_number(first, 1), elapsed_ms


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def benchmark(
    router: CaptureVisionRouter,
    records: Sequence[ImageRecord],
    runs: int,
    template_name: str,
    has_ground_truth: bool = True,
) -> List[ImageResult]:
    """
    Run the benchmark on all records.

    For each image, decode it *runs* times and keep the best (fastest
    successful) timing.  If has_ground_truth is False, match_rate is
    always 0.0 and exact_match is always False.
    """
    output: List[ImageResult] = []
    total = len(records)

    for idx, record in enumerate(records, start=1):
        best_text: Optional[str] = None
        best_err: Optional[str] = None
        best_page = 1
        best_ms: Optional[float] = None

        for _ in range(max(1, runs)):
            recognized, err, page_number, elapsed_ms = decode_once(
                router=router,
                image_path=record.path,
                template_name=template_name,
            )

            is_better = best_ms is None or elapsed_ms < best_ms
            prefer_success = recognized is not None and best_text is None
            if prefer_success or is_better:
                best_text = recognized
                best_err = err
                best_page = page_number
                best_ms = elapsed_ms

        if has_ground_truth:
            score = match_rate(best_text, record.truth_mrz)
            exact = score >= 0.99999
        else:
            score = 0.0
            exact = False

        success = best_text is not None

        output.append(
            ImageResult(
                key=record.key,
                success=success,
                error=best_err if not success else None,
                recognized_mrz=best_text,
                truth_mrz=record.truth_mrz,
                match_rate=score,
                exact_match=exact,
                run_ms=best_ms,
                page_number=best_page,
            )
        )

        if has_ground_truth:
            tag = "PASS" if exact else ("MISS" if success else "ERR")
        else:
            tag = "OK" if success else "ERR"
        time_text = ms(best_ms) if best_ms is not None else "-"
        print(f"[{idx:>4}/{total}] {record.key:<32} {tag:<4} {time_text}")

    return output


def result_to_dict(row: ImageResult) -> dict:
    """Convert an ImageResult to a JSON-serialisable dictionary."""
    return {
        "key": row.key,
        "success": row.success,
        "error": row.error,
        "recognized_mrz": row.recognized_mrz,
        "truth_mrz": row.truth_mrz,
        "match_rate": round(row.match_rate, 6),
        "exact_match": row.exact_match,
        "run_ms": round(row.run_ms, 3) if row.run_ms is not None else None,
        "page_number": row.page_number,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the benchmark end-to-end."""
    args = parse_args()

    # --- Dataset resolution ------------------------------------------------
    if args.download:
        dataset_dir = args.dataset or Path("./midv-500-data")
        download_and_prepare_dataset(dataset_dir, limit=max(0, args.download_limit))
    else:
        dataset_dir = args.dataset

    if dataset_dir is None:
        print(
            "Error: No dataset path specified.\n"
            "Use --dataset /path/to/data or set MRZ_DATASET_DIR env var,\n"
            "or use --download to fetch the MIDV-500 dataset automatically.\n"
            "Dataset source: https://github.com/fcakyon/midv500"
        )
        sys.exit(1)

    dataset_dir = Path(dataset_dir)
    if not dataset_dir.exists():
        raise SystemExit(f"Dataset folder not found: {dataset_dir}")

    csv_path = args.csv if args.csv else dataset_dir / "labels.csv"

    # --- Ground truth loading ----------------------------------------------
    has_ground_truth = not args.no_ground_truth
    truth_map: Dict[str, str] = {}

    if has_ground_truth:
        if not csv_path.exists():
            # Try bundled labels.csv as a fallback
            if BUNDLED_LABELS_CSV.exists():
                print(f"[info] CSV not found at {csv_path}, using bundled {BUNDLED_LABELS_CSV}")
                csv_path = BUNDLED_LABELS_CSV
            else:
                print(f"[warning] No labels.csv found — switching to speed-only mode.")
                has_ground_truth = False
        else:
            truth_map = load_ground_truth(csv_path)

    # --- Record building ---------------------------------------------------
    if has_ground_truth and truth_map:
        records = build_records(dataset_dir, truth_map, limit=max(0, args.limit))
    else:
        records = build_records_no_truth(dataset_dir, limit=max(0, args.limit))

    if not records:
        raise SystemExit(
            "No images found. Check dataset path and image files.\n"
            f"Dataset: {dataset_dir}"
        )

    # --- Print run info ----------------------------------------------------
    print("Dynamsoft Capture Vision MRZ Benchmark")
    print(f"Dataset : {dataset_dir}")
    print(f"CSV     : {csv_path if has_ground_truth else '(none — speed-only mode)'}")
    print(f"Output  : {args.output.resolve()}")
    print(f"Runs    : {max(1, args.runs)}")
    print(f"Mode    : {'accuracy' if has_ground_truth else 'speed-only'}")
    print(f"Images  : {len(records)}")

    # --- Run benchmark -----------------------------------------------------
    started_at = datetime.now().isoformat(timespec="seconds")
    wall_start = time.perf_counter()

    router = init_dynamsoft_router(args.license)
    results = benchmark(
        router,
        records,
        runs=args.runs,
        template_name=args.template,
        has_ground_truth=has_ground_truth,
    )

    total_wall_ms = (time.perf_counter() - wall_start) * 1000.0
    finished_at = datetime.now().isoformat(timespec="seconds")

    summary = build_summary(results, total_wall_ms)

    # --- Build and save report ---------------------------------------------
    report_obj = {
        "sdk": "Dynamsoft Capture Vision",
        "template": args.template,
        "dataset": str(dataset_dir.resolve()),
        "csv": str(csv_path.resolve()) if has_ground_truth else None,
        "dataset_source": "https://github.com/fcakyon/midv500",
        "started_at": started_at,
        "finished_at": finished_at,
        "runs": max(1, args.runs),
        "has_ground_truth": has_ground_truth,
        "image_count": summary.total_images,
        "summary": {
            "exact_accuracy": round(
                summary.exact_count / summary.total_images if summary.total_images else 0.0, 6
            ),
            "success_rate": round(
                summary.success_count / summary.total_images if summary.total_images else 0.0, 6
            ),
            "average_match_rate": round(summary.avg_match_rate, 6),
            "avg_ms": round(summary.avg_ms, 3),
            "min_ms": round(summary.min_ms, 3),
            "max_ms": round(summary.max_ms, 3),
            "p50_ms": round(summary.p50_ms, 3),
            "p95_ms": round(summary.p95_ms, 3),
            "p99_ms": round(summary.p99_ms, 3),
            "total_wall_ms": round(summary.total_wall_ms, 3),
            "success_count": summary.success_count,
            "exact_count": summary.exact_count,
        },
        "results": [result_to_dict(r) for r in results],
    }

    args.output.mkdir(parents=True, exist_ok=True)
    json_path = args.output / "report.json"
    html_path = args.output / "report.html"

    json_path.write_text(
        json.dumps(report_obj, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    html_path.write_text(build_html(report_obj, summary), encoding="utf-8")

    # --- Print summary -----------------------------------------------------
    print("\nSummary")
    if has_ground_truth:
        print(f"  Exact accuracy : {pct(report_obj['summary']['exact_accuracy'])}")
    print(f"  Success rate   : {pct(report_obj['summary']['success_rate'])}")
    print(f"  Avg match rate : {pct(report_obj['summary']['average_match_rate'])}")
    print(f"  Avg time cost  : {ms(report_obj['summary']['avg_ms'])}")
    print(f"  P50 time cost  : {ms(report_obj['summary']['p50_ms'])}")
    print(f"  P95 time cost  : {ms(report_obj['summary']['p95_ms'])}")
    print(f"  Total elapsed  : {ms(report_obj['summary']['total_wall_ms'])}")

    print("\nReports generated:")
    print(f"  JSON: {json_path.resolve()}")
    print(f"  HTML: {html_path.resolve()}")


if __name__ == "__main__":
    main()
