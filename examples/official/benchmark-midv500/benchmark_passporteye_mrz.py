"""
Benchmark PassportEye MRZ recognition accuracy and speed on a MIDV-500 subset.

This script is the open-source companion to ``benchmark_dcv_mrz.py``. It uses
the same curated ground-truth CSV, the same image discovery, and the same
metrics (exact accuracy, success rate, character-level match rate, and
per-image wall-clock timing), so the results are directly comparable with the
Dynamsoft Capture Vision run.

PassportEye (https://github.com/konstantint/PassportEye) is an MIT-licensed
MRZ extraction pipeline built on Google Tesseract OCR. It requires the
``tesseract`` executable to be available on the system PATH.

Usage:
    python benchmark_passporteye_mrz.py --dataset /path/to/midv-500-mrz --output benchmark_report_passporteye
    python benchmark_passporteye_mrz.py --dataset /path/to/midv-500-mrz --limit 5
"""

import argparse
import csv
import json
import math
import statistics
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}

BUNDLED_LABELS_CSV = Path(__file__).resolve().parent / "labels.csv"


# ---------------------------------------------------------------------------
# Data model (mirrors benchmark_dcv_mrz.py)
# ---------------------------------------------------------------------------

@dataclass
class ImageRecord:
    key: str
    path: Path
    truth_mrz: str


@dataclass
class ImageResult:
    key: str
    success: bool
    error: Optional[str]
    recognized_mrz: Optional[str]
    truth_mrz: str
    match_rate: float
    exact_match: bool
    run_ms: Optional[float]


@dataclass
class SummaryStats:
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
# MRZ text utilities (identical to benchmark_dcv_mrz.py)
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
# Dataset loading (identical to benchmark_dcv_mrz.py)
# ---------------------------------------------------------------------------

def load_ground_truth(csv_path: Path) -> Dict[str, str]:
    """Load ground-truth MRZ labels from a CSV file."""
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
    """Recursively discover all supported image files in the dataset directory."""
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
    """Align discovered images with ground-truth labels."""
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


# ---------------------------------------------------------------------------
# Statistics (identical to benchmark_dcv_mrz.py)
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
# PassportEye decoding
# ---------------------------------------------------------------------------

def decode_once(read_mrz_fn, image_path: Path) -> Tuple[Optional[str], Optional[str], float]:
    """Decode a single image with PassportEye and return (mrz_text, error, elapsed_ms)."""
    start = time.perf_counter()
    try:
        mrz = read_mrz_fn(str(image_path))
    except Exception as exc:  # TesseractError and friends
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return None, f"PassportEye exception: {exc}", elapsed_ms
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    if mrz is None:
        return None, "No MRZ region detected.", elapsed_ms

    raw_text = ""
    try:
        raw_text = str(mrz.aux.get("raw_text") or mrz.aux.get("text") or "")
    except Exception:
        raw_text = ""

    if not raw_text.strip():
        return None, "MRZ region found but no text returned.", elapsed_ms
    return raw_text, None, elapsed_ms


def benchmark(
    read_mrz_fn,
    records: Sequence[ImageRecord],
) -> List[ImageResult]:
    """Run PassportEye over all records and score them against ground truth."""
    output: List[ImageResult] = []
    total = len(records)

    for idx, record in enumerate(records, start=1):
        text, err, elapsed_ms = decode_once(read_mrz_fn, record.path)

        score = match_rate(text, record.truth_mrz)
        exact = score >= 0.99999

        output.append(ImageResult(
            key=record.key,
            success=text is not None,
            error=err if text is None else None,
            recognized_mrz=text,
            truth_mrz=record.truth_mrz,
            match_rate=score,
            exact_match=exact,
            run_ms=elapsed_ms,
        ))

        if idx % 50 == 0 or idx == total:
            print(f"  [{idx}/{total}] processed", flush=True)

    return output


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def result_to_dict(row: ImageResult) -> Dict[str, object]:
    return {
        "image": row.key,
        "success": row.success,
        "error": row.error,
        "recognized_mrz": row.recognized_mrz,
        "truth_mrz": row.truth_mrz,
        "match_rate": round(row.match_rate, 6),
        "exact_match": row.exact_match,
        "decode_ms": round(row.run_ms, 3) if row.run_ms is not None else None,
    }


def write_report(
    output_dir: Path,
    results: Sequence[ImageResult],
    summary: SummaryStats,
    dataset_dir: Path,
    csv_path: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_obj = {
        "sdk": "PassportEye",
        "engine": "Tesseract OCR",
        "dataset": str(dataset_dir.resolve()),
        "csv": str(csv_path.resolve()),
        "image_count": summary.total_images,
        "summary": {
            "exact_accuracy": round(summary.exact_count / summary.total_images, 6) if summary.total_images else 0.0,
            "success_rate": round(summary.success_count / summary.total_images, 6) if summary.total_images else 0.0,
            "average_match_rate": round(summary.avg_match_rate, 6),
            "avg_ms": round(summary.avg_ms, 3),
            "min_ms": round(summary.min_ms, 3),
            "max_ms": round(summary.max_ms, 3),
            "p50_ms": round(summary.p50_ms, 3),
            "p95_ms": round(summary.p95_ms, 3),
            "p99_ms": round(summary.p99_ms, 3),
            "total_wall_ms": round(summary.total_wall_ms, 3),
        },
        "results": [result_to_dict(r) for r in results],
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report_obj, indent=2), encoding="utf-8")
    return report_path


def print_summary(summary: SummaryStats) -> None:
    total = summary.total_images or 1
    print("\n===== PassportEye MIDV-500 MRZ Benchmark =====")
    print(f"Total images:        {summary.total_images}")
    print(f"Successful decodes:  {summary.success_count} ({summary.success_count / total * 100:.2f}%)")
    print(f"Exact MRZ matches:   {summary.exact_count} ({summary.exact_count / total * 100:.2f}%)")
    print(f"Average match rate:  {summary.avg_match_rate * 100:.2f}%")
    print(f"Average decode time: {summary.avg_ms:.1f} ms")
    print(f"P50 / P95 / P99:     {summary.p50_ms:.1f} / {summary.p95_ms:.1f} / {summary.p99_ms:.1f} ms")
    print(f"Min / Max:           {summary.min_ms:.1f} / {summary.max_ms:.1f} ms")
    print(f"Total wall time:     {summary.total_wall_ms / 1000.0:.1f} s")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark PassportEye MRZ recognition on the curated MIDV-500 MRZ subset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", type=Path, required=True, help="Dataset root folder (CA/, CS/, ... subfolders).")
    parser.add_argument("--csv", type=Path, default=None, help="Ground-truth CSV path (default: bundled curated labels.csv).")
    parser.add_argument("--output", type=Path, default=Path("benchmark_report_passporteye"), help="Output folder for report.json.")
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N matched images.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    warnings.filterwarnings("ignore")
    try:
        from passporteye import read_mrz
    except ImportError:
        print("PassportEye is not installed. Run: pip install PassportEye", file=sys.stderr)
        return 2

    dataset_dir: Path = args.dataset
    if not dataset_dir.is_dir():
        print(f"Dataset folder not found: {dataset_dir}", file=sys.stderr)
        return 2

    csv_path = args.csv if args.csv else BUNDLED_LABELS_CSV
    if not csv_path.is_file():
        print(f"Ground-truth CSV not found: {csv_path}", file=sys.stderr)
        return 2

    truth_map = load_ground_truth(csv_path)
    records = build_records(dataset_dir, truth_map, limit=args.limit)
    if not records:
        print("No images matched the ground-truth labels.", file=sys.stderr)
        return 1

    print(f"Benchmarking {len(records)} images with PassportEye ...")
    wall_start = time.perf_counter()
    results = benchmark(read_mrz, records)
    wall_ms = (time.perf_counter() - wall_start) * 1000.0

    summary = build_summary(results, wall_ms)
    report_path = write_report(args.output, results, summary, dataset_dir, csv_path)
    print_summary(summary)
    print(f"\nJSON report written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
