"""CivicSense Image Validation for Datasets.

Validates candidate image files for:
- File existence & path safety (no directory traversal)
- File size bounds (<= 10MB)
- Magic bytes inspection (JPEG, PNG, WEBP)
- Image decodability and dimensions [64, 8192] px
- Decompression bomb safety (limit 25M pixels)
- SHA-256 computation
- 64-bit difference hash (dHash) computation
- Quality flags (is_blurry, is_low_res)
"""

import hashlib
import io
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

MAGIC_JPEG = b"\xff\xd8\xff"
MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
MAGIC_WEBP_RIFF = b"RIFF"
MAGIC_WEBP_TAG = b"WEBP"
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_PIXELS = 25_000_000
MIN_DIMENSION_PX = 64
MAX_DIMENSION_PX = 8192


@dataclass
class ImageValidationResult:
    """Detailed outcome of validating an image file."""

    is_valid: bool
    path: str
    rejection_reason: str | None = None
    sha256: str = ""
    phash: str = ""
    width: int = 0
    height: int = 0
    mime_type: str = ""
    file_size_bytes: int = 0
    is_blurry: bool = False
    is_low_res: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_dhash(img: Image.Image) -> str:
    """Compute 64-bit difference hash (dHash) using Pillow."""
    gray = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(gray.tobytes())
    diff = []
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            diff.append(1 if left > right else 0)

    decimal_val = 0
    for bit in diff:
        decimal_val = (decimal_val << 1) | bit
    return f"{decimal_val:016x}"


def estimate_blur(img: Image.Image) -> bool:
    """Estimate image blurriness using luminance gradient variance."""
    small = img.convert("L").resize((64, 64), Image.Resampling.BILINEAR)
    pixels = list(small.tobytes())
    diffs: list[float] = []
    for y in range(63):
        for x in range(63):
            val = pixels[y * 64 + x]
            dx = abs(val - pixels[y * 64 + (x + 1)])
            dy = abs(val - pixels[(y + 1) * 64 + x])
            diffs.append(dx + dy)

    if not diffs:
        return False
    mean = sum(diffs) / len(diffs)
    variance = sum((d - mean) ** 2 for d in diffs) / len(diffs)
    return variance < 15.0


def validate_image_file(
    file_path: str | Path,
    base_dir: str | Path | None = None,
) -> ImageValidationResult:
    """Perform rigorous safety and quality checks on a local image file."""
    path_obj = Path(file_path)

    # 1. Path Safety & Traversal Checks
    if base_dir:
        try:
            base_resolved = Path(base_dir).resolve()
            file_resolved = path_obj.resolve()
            if not str(file_resolved).startswith(str(base_resolved)):
                return ImageValidationResult(
                    is_valid=False,
                    path=str(path_obj),
                    rejection_reason="Path traversal violation: file outside base directory",
                )
        except Exception as err:
            return ImageValidationResult(
                is_valid=False,
                path=str(path_obj),
                rejection_reason=f"Path resolution error: {err}",
            )

    # 2. File Existence & Type
    if not path_obj.exists():
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason="File does not exist",
        )
    if not path_obj.is_file():
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason="Path is not a regular file",
        )

    # 3. Read bytes & Size Limits
    try:
        raw_bytes = path_obj.read_bytes()
    except Exception as err:
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason=f"Failed to read file: {err}",
        )

    file_size = len(raw_bytes)
    if file_size == 0:
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason="File is empty (0 bytes)",
        )
    if file_size > MAX_IMAGE_SIZE_BYTES:
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason=(
                f"File exceeds maximum allowed size ({file_size} > {MAX_IMAGE_SIZE_BYTES})"
            ),
        )

    # 4. Magic Bytes Inspection
    mime_type: str | None = None
    if raw_bytes.startswith(MAGIC_JPEG):
        mime_type = "image/jpeg"
    elif raw_bytes.startswith(MAGIC_PNG):
        mime_type = "image/png"
    elif (
        raw_bytes.startswith(MAGIC_WEBP_RIFF)
        and len(raw_bytes) >= 12
        and raw_bytes[8:12] == MAGIC_WEBP_TAG
    ):
        mime_type = "image/webp"
    else:
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason="Unsupported magic bytes; must be valid JPEG, PNG, or WEBP",
            file_size_bytes=file_size,
        )

    # 5. SHA-256
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    # 6. Pillow Decode & Dimension Validation
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    stream = io.BytesIO(raw_bytes)
    try:
        with Image.open(stream) as img:
            width, height = img.size
            if width * height > MAX_IMAGE_PIXELS:
                return ImageValidationResult(
                    is_valid=False,
                    path=str(path_obj),
                    rejection_reason="Decompression bomb detected (exceeds 25M pixels)",
                    sha256=sha256,
                    file_size_bytes=file_size,
                    mime_type=mime_type,
                )
            if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
                return ImageValidationResult(
                    is_valid=False,
                    path=str(path_obj),
                    rejection_reason=(
                        f"Dimensions too small ({width}x{height} < {MIN_DIMENSION_PX}px)"
                    ),
                    sha256=sha256,
                    file_size_bytes=file_size,
                    mime_type=mime_type,
                    width=width,
                    height=height,
                )
            if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
                return ImageValidationResult(
                    is_valid=False,
                    path=str(path_obj),
                    rejection_reason=(
                        f"Dimensions too large ({width}x{height} > {MAX_DIMENSION_PX}px)"
                    ),
                    sha256=sha256,
                    file_size_bytes=file_size,
                    mime_type=mime_type,
                    width=width,
                    height=height,
                )

            # Full decode verification
            img.verify()

        # Reopen for dHash and quality analysis
        stream.seek(0)
        with Image.open(stream) as img2:
            phash = compute_dhash(img2)
            is_blurry = estimate_blur(img2)
            is_low_res = min(width, height) < 128

        warnings: list[str] = []
        if is_blurry:
            warnings.append("Image flagged as blurry")
        if is_low_res:
            warnings.append("Image flagged as low resolution")

        return ImageValidationResult(
            is_valid=True,
            path=str(path_obj),
            sha256=sha256,
            phash=phash,
            width=width,
            height=height,
            mime_type=mime_type,
            file_size_bytes=file_size,
            is_blurry=is_blurry,
            is_low_res=is_low_res,
            warnings=warnings,
        )

    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as err:
        return ImageValidationResult(
            is_valid=False,
            path=str(path_obj),
            rejection_reason=f"Corrupted or invalid image stream: {err}",
            sha256=sha256,
            file_size_bytes=file_size,
            mime_type=mime_type,
        )


def validate_image_directory(
    target_path: Path,
    output_report: Path | None = None,
) -> dict[str, Any]:
    """Validate all images in a directory (or a single file) and produce a validation report."""
    target_path = Path(target_path)
    if not target_path.exists():
        raise FileNotFoundError(f"Path does not exist: {target_path}")

    files_to_check: list[Path] = []
    if target_path.is_file():
        files_to_check = [target_path]
    else:
        extensions = {".jpg", ".jpeg", ".png", ".webp"}
        files_to_check = sorted(
            [p for p in target_path.rglob("*") if p.is_file() and p.suffix.lower() in extensions]
        )

    valid_files: list[dict[str, Any]] = []
    invalid_files: list[dict[str, Any]] = []
    quality_warnings: list[dict[str, Any]] = []

    for file_p in files_to_check:
        res = validate_image_file(file_p)
        res_dict = res.to_dict()
        if res.is_valid:
            valid_files.append(res_dict)
            if res.warnings:
                quality_warnings.append({
                    "path": str(file_p),
                    "warnings": res.warnings,
                    "is_blurry": res.is_blurry,
                    "is_low_res": res.is_low_res,
                })
        else:
            invalid_files.append(res_dict)

    report = {
        "target_path": str(target_path),
        "total_checked": len(files_to_check),
        "valid_count": len(valid_files),
        "invalid_count": len(invalid_files),
        "warning_count": len(quality_warnings),
        "valid_files": valid_files,
        "invalid_files": invalid_files,
        "quality_warnings": quality_warnings,
    }

    if output_report:
        output_report = Path(output_report)
        output_report.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            import json

            json.dump(report, f, indent=2)

    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CivicSense Image Validation Tool")
    parser.add_argument("path", help="Path to an image file or directory")
    parser.add_argument(
        "--output-report",
        default=None,
        help="Path to write JSON validation report",
    )

    args = parser.parse_args()
    report = validate_image_directory(
        target_path=Path(args.path),
        output_report=Path(args.output_report) if args.output_report else None,
    )

    print("=" * 60)
    print(" CIVICSENSE IMAGE VALIDATION REPORT")
    print("=" * 60)
    print(f"Target Path     : {report['target_path']}")
    print(f"Total Checked   : {report['total_checked']}")
    print(f"Valid Files     : {report['valid_count']}")
    print(f"Invalid Files   : {report['invalid_count']}")
    print(f"Warnings        : {report['warning_count']}")

    if report["invalid_files"]:
        print("-" * 60)
        print("REJECTED FILES:")
        for inv in report["invalid_files"]:
            print(f" - {inv['path']}: {inv['rejection_reason']}")

    if args.output_report:
        print(f"\nReport written to: {args.output_report}")


if __name__ == "__main__":
    main()
