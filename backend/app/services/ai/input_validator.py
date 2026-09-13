import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import (
    CorruptImageError,
    ImageDecompressionBombError,
    ImageDimensionsInvalidError,
    InvalidImagePayloadError,
    OversizedImageError,
    TextValidationError,
    UnsupportedImageTypeError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidatedImageResult:
    """Outcome of rigorous image stream validation and metadata inspection."""

    raw_bytes: bytes
    mime_type: str
    file_extension: str
    width: int
    height: int
    total_pixels: int
    sha256: str
    file_size_bytes: int
    has_exif: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidatedTextResult:
    """Outcome of Unicode normalization and sanitization."""

    cleaned_text: str
    original_text: str
    character_count: int
    word_count: int
    warnings: list[str] = field(default_factory=list)


class InputValidator:
    """Production quality gate for validating and hardening image and text inputs."""

    # Explicit magic byte signatures
    MAGIC_JPEG = b"\xff\xd8\xff"
    MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
    MAGIC_WEBP_RIFF = b"RIFF"
    MAGIC_WEBP_TAG = b"WEBP"
    MAGIC_GIF = (b"GIF87a", b"GIF89a")

    @classmethod
    def validate_image_bytes(
        cls,
        raw_bytes: bytes,
        declared_mime_type: str | None = None,
    ) -> ValidatedImageResult:
        """Validate raw image bytes with strict signature, dimension, and decompression safety.

        Raises specialized domain exceptions on any safety violation.
        Does NOT trust client-declared MIME types.
        """
        settings = get_settings()

        # 1. Missing / Empty Payload Detection
        if not raw_bytes or len(raw_bytes) == 0:
            raise InvalidImagePayloadError("Image payload is empty (0 bytes).")

        # 2. Maximum Payload Size Bounds
        byte_size = len(raw_bytes)
        if byte_size > settings.MAX_IMAGE_SIZE_BYTES:
            raise OversizedImageError(byte_size, settings.MAX_IMAGE_SIZE_BYTES)

        # 3. Signature / Magic-Byte Inspection
        detected_mime: str | None = None
        detected_ext: str | None = None

        if raw_bytes.startswith(cls.MAGIC_JPEG):
            detected_mime = "image/jpeg"
            detected_ext = ".jpg"
        elif raw_bytes.startswith(cls.MAGIC_PNG):
            detected_mime = "image/png"
            detected_ext = ".png"
        elif raw_bytes.startswith(cls.MAGIC_WEBP_RIFF) and len(raw_bytes) >= 12:
            if raw_bytes[8:12] == cls.MAGIC_WEBP_TAG:
                detected_mime = "image/webp"
                detected_ext = ".webp"

        # Check for explicit unsupported or dangerous types before generic error
        if not detected_mime:
            if any(raw_bytes.startswith(sig) for sig in cls.MAGIC_GIF):
                raise UnsupportedImageTypeError("image/gif")
            if raw_bytes.strip().startswith(b"<?xml") or b"<svg" in raw_bytes[:100].lower():
                raise UnsupportedImageTypeError("image/svg+xml")
            if raw_bytes.startswith(b"MZ") or raw_bytes.startswith(b"\x7fELF"):
                raise UnsupportedImageTypeError("application/octet-stream")
            raise UnsupportedImageTypeError(declared_mime_type or "unknown/unsupported")

        if detected_mime not in settings.ALLOWED_IMAGE_MIME_TYPES:
            raise UnsupportedImageTypeError(detected_mime)

        # 4. Safe Pillow Inspection without Early Rasterization
        # Enforce decompression bomb pixel ceiling in Pillow
        Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS

        stream = io.BytesIO(raw_bytes)
        try:
            with Image.open(stream) as img:
                width, height = img.size
                total_pixels = width * height

                # 5. Decompression-Bomb Protection
                if total_pixels > settings.MAX_IMAGE_PIXELS:
                    raise ImageDecompressionBombError(total_pixels, settings.MAX_IMAGE_PIXELS)

                # 6. Usable Dimension Bounds
                if (
                    width < settings.MIN_IMAGE_DIMENSION
                    or height < settings.MIN_IMAGE_DIMENSION
                    or width > settings.MAX_IMAGE_DIMENSION
                    or height > settings.MAX_IMAGE_DIMENSION
                ):
                    raise ImageDimensionsInvalidError(
                        width, height, settings.MIN_IMAGE_DIMENSION, settings.MAX_IMAGE_DIMENSION
                    )

                # 7. Structural Integrity & Truncation Check
                img.verify()

        except Image.DecompressionBombError as err:
            raise ImageDecompressionBombError(
                settings.MAX_IMAGE_PIXELS + 1, settings.MAX_IMAGE_PIXELS
            ) from err
        except UnidentifiedImageError as err:
            raise CorruptImageError(
                "Unidentified image format or malformed header structure."
            ) from err
        except (ImageDimensionsInvalidError, ImageDecompressionBombError):
            raise
        except Exception as err:
            raise CorruptImageError(f"Image header verification failed: {err}") from err

        # 8. Complete Rasterization Decode Check
        # verify() only checks the header/tables; load() ensures pixel stream is readable.
        has_exif = False
        raster_stream = io.BytesIO(raw_bytes)
        try:
            with Image.open(raster_stream) as raster_img:
                raster_img.load()
                # Safely inspect EXIF presence without leaking values
                exif_data = raster_img.getexif()
                has_exif = bool(exif_data and len(exif_data) > 0)
        except Image.DecompressionBombError as err:
            raise ImageDecompressionBombError(
                settings.MAX_IMAGE_PIXELS + 1, settings.MAX_IMAGE_PIXELS
            ) from err
        except Exception as err:
            raise CorruptImageError(
                f"Image raster decoding failed (corrupted/truncated data): {err}"
            ) from err

        # 9. Cryptographic Hash
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

        return ValidatedImageResult(
            raw_bytes=raw_bytes,
            mime_type=detected_mime,
            file_extension=detected_ext or "",
            width=width,
            height=height,
            total_pixels=total_pixels,
            sha256=sha256_hash,
            file_size_bytes=byte_size,
            has_exif=has_exif,
            metadata={
                "aspect_ratio": round(width / height, 3) if height > 0 else 1.0,
                "detected_mime": detected_mime,
            },
        )

    @classmethod
    def validate_and_sanitize_text(cls, raw_text: str) -> ValidatedTextResult:
        """Sanitize citizen problem text using Unicode NFKC and control char stripping."""
        settings = get_settings()

        if raw_text is None:
            raise TextValidationError("Description cannot be null.")

        # 1. Trim surrounding whitespace
        trimmed = raw_text.strip()
        if not trimmed:
            raise TextValidationError("Description cannot be empty or whitespace-only.")

        # 2. Unicode NFKC Normalization
        normalized = unicodedata.normalize("NFKC", trimmed)

        # 3. Strip dangerous control characters while preserving standard whitespace (\n, \r, \t)
        # Keeps all multilingual characters (Malayalam, Hindi, Arabic, etc.) intact
        cleaned_chars = []
        for ch in normalized:
            if ch in ("\n", "\r", "\t"):
                cleaned_chars.append(ch)
            elif unicodedata.category(ch) != "Cc":
                cleaned_chars.append(ch)
        cleaned = "".join(cleaned_chars).strip()

        # 4. Collapse excessive blank newlines (max 2 consecutive newlines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 5. Length Constraints
        length = len(cleaned)
        if length > settings.MAX_DESCRIPTION_LENGTH:
            msg = (
                f"Description length ({length}) exceeds maximum limit "
                f"({settings.MAX_DESCRIPTION_LENGTH} characters)."
            )
            raise TextValidationError(msg)

        warnings: list[str] = []

        # Meaningful short civic signal allowance vs minimum length constraint
        if length < 3:
            raise TextValidationError("Description must be at least 3 characters long.")
        elif length <= 4:
            warnings.append("SHORT_DESCRIPTION_ACCEPTED")

        # 6. Repeated Character Run Detection (Spam / Pathological inputs)
        # Detect runs of >= 20 identical characters
        repeated_pattern = re.compile(
            r"(.)\1{" + str(settings.MAX_REPEATED_CHARACTER_RUN - 1) + r",}"
        )
        match = repeated_pattern.search(cleaned)
        if match:
            repeated_char = match.group(1)
            # Allow common expressive punctuation or repeated numbers (e.g. road code or 100000)
            if repeated_char in (".", "-", "_", "!", "?", "0", " "):
                # Compress excessive decorative punctuation
                cleaned = repeated_pattern.sub(repeated_char * 3, cleaned)
                warnings.append("EXCESSIVE_PUNCTUATION_COMPRESSED")
            else:
                msg = (
                    f"Description contains excessive repeated character run "
                    f"('{repeated_char * 5}...'). "
                    "Please provide a meaningful problem description."
                )
                raise TextValidationError(msg)

        words = [w for w in re.split(r"\s+", cleaned) if w]
        return ValidatedTextResult(
            cleaned_text=cleaned,
            original_text=raw_text,
            character_count=len(cleaned),
            word_count=len(words),
            warnings=warnings,
        )
