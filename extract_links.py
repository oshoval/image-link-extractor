#!/usr/bin/env python3
#
# Copyright 2026 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Extract URLs from images using Tesseract OCR.

Deterministic, free, local-only — no cloud APIs or deep learning models.
Uses Tesseract (classical OCR) + regex to find URLs in image text.

Usage:
    python3 extract_links.py <image_path> [image_path2 ...]
    python3 extract_links.py screenshot.png
    python3 extract_links.py slide1.png slide2.png
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytesseract
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r"(?:https?://|ftp://|www\.)"  # scheme or www.
    r"[^\s<>\"\'\)\]\},;!]*"  # URL body (greedy, stops at whitespace/delimiters)
    r"[^\s<>\"\'\)\]\},;!.\:]"  # don't end on trailing punctuation
)

SUPPORTED_FORMATS = frozenset((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"))

BULLET_PREFIXES = ("*", "-", "•", "●", "+")

# Characters that are valid inside a URL (RFC 3986 + common extras)
URL_CHARS = frozenset("/-_.~:?#[]@!$&'()*+,;=%")

# OCR character misreads commonly seen in hex-heavy strings
OCR_HEX_FIXES: dict[str, str] = {
    "O": "0",
    "Q": "0",
    "l": "1",
    "I": "1",
    "S": "5",
    "G": "6",
}

# Image preprocessing thresholds
MIN_WIDTH_FOR_UPSCALE = 1000
UPSCALE_FACTOR = 2

# URL continuation heuristic thresholds
URL_CHAR_RATIO_THRESHOLD = 0.85
MIN_CONTINUATION_LENGTH = 5

# Hex segment detection thresholds
MIN_HEX_SEGMENT_LENGTH = 8
HEX_CHAR_RATIO_THRESHOLD = 0.7

HEX_CHARS = frozenset("0123456789abcdefABCDEF")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ExtractionResult:
    """Result of processing a single image."""

    file: str
    urls: list[str] = field(default_factory=list)
    text: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


# ---------------------------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------------------------


def preprocess_image(image_path: Path) -> Image.Image:
    """Load and preprocess image for better OCR accuracy."""
    img = Image.open(image_path)
    img = img.convert("L")

    width, height = img.size
    if width < MIN_WIDTH_FOR_UPSCALE:
        img = img.resize(
            (width * UPSCALE_FACTOR, height * UPSCALE_FACTOR),
            Image.LANCZOS,
        )

    return img


def extract_text(image_path: Path) -> str:
    """Extract text from image using Tesseract OCR."""
    img = preprocess_image(image_path)
    return pytesseract.image_to_string(img, config="--oem 3 --psm 6")


# ---------------------------------------------------------------------------
# URL extraction pipeline
# ---------------------------------------------------------------------------


def rejoin_wrapped_urls(text: str) -> str:
    """Rejoin URLs that wrap across multiple lines.

    When a URL is split across lines in an image, OCR produces:
        https://example.com/abc123
        def456ghi
    This function detects continuation lines (lines that look like
    hex strings, path segments, or URL fragments) and joins them
    back to the URL on the previous line.
    """
    lines = text.split("\n")
    merged: list[str] = []

    for line in lines:
        stripped = line.strip()
        if _should_join_to_previous(merged, stripped):
            merged[-1] = merged[-1].rstrip() + stripped
        else:
            merged.append(line)

    return "\n".join(merged)


def _should_join_to_previous(merged_lines: list[str], stripped_line: str) -> bool:
    """Determine if a line should be joined to the previous URL line."""
    return bool(
        merged_lines
        and URL_PATTERN.search(merged_lines[-1])
        and stripped_line
        and not stripped_line.startswith(BULLET_PREFIXES)
        and _looks_like_url_continuation(stripped_line)
    )


def _looks_like_url_continuation(line: str) -> bool:
    """Heuristic: does this line look like the tail of a wrapped URL?

    Matches lines that are mostly URL-valid characters, without spaces,
    and at least MIN_CONTINUATION_LENGTH chars long.
    """
    cleaned = line.strip().rstrip(".,;:!? ")
    if not cleaned:
        return False

    if " " in cleaned:
        return False

    url_char_count = sum(1 for c in cleaned if c.isalnum() or c in URL_CHARS)
    return (
        url_char_count / len(cleaned) >= URL_CHAR_RATIO_THRESHOLD
        and len(cleaned) >= MIN_CONTINUATION_LENGTH
    )


def _fix_hex_segment(segment: str) -> str:
    """Fix common OCR misreads in a single path segment that looks like a hex hash."""
    if len(segment) < MIN_HEX_SEGMENT_LENGTH:
        return segment

    hex_count = sum(1 for c in segment if c in HEX_CHARS)
    if hex_count / len(segment) >= HEX_CHAR_RATIO_THRESHOLD:
        return "".join(OCR_HEX_FIXES.get(c, c) for c in segment)
    return segment


def _fix_ocr_artifacts(url: str) -> str:
    """Fix common OCR character misreads in URL path segments.

    Only applies corrections to segments that look like hex strings
    (e.g. git commit hashes, gist IDs) to avoid breaking real words.
    """
    match = re.match(r"(https?://[^/]+)(.*)", url)
    if not match:
        return url

    host = match.group(1)
    path = match.group(2)

    fixed_segments = [_fix_hex_segment(s) for s in path.split("/")]
    return host + "/".join(fixed_segments)


def _deduplicate(items: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    return list(dict.fromkeys(items))


def find_urls(text: str) -> list[str]:
    """Find all URLs in extracted text, handling line-wrapped URLs."""
    text = rejoin_wrapped_urls(text)
    urls = URL_PATTERN.findall(text)
    urls = [_fix_ocr_artifacts(u) for u in urls]
    return _deduplicate(urls)


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------


def process_image(image_path: str) -> ExtractionResult:
    """Process a single image: extract text and find URLs."""
    path = Path(image_path)

    if not path.exists():
        return ExtractionResult(file=image_path, error=f"File not found: {image_path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        return ExtractionResult(file=image_path, error=f"Unsupported format: {path.suffix}")

    text = extract_text(path)
    urls = find_urls(text)
    return ExtractionResult(file=image_path, urls=urls, text=text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_result(result: ExtractionResult) -> str:
    """Format a single extraction result for terminal output."""
    if not result.ok:
        return f"ERROR: {result.error}"

    lines = [f"=== {result.file} ==="]
    if result.urls:
        lines.append(f"Found {len(result.urls)} link(s):\n")
        for i, url in enumerate(result.urls, 1):
            lines.append(f"  {i}. {url}")
    else:
        lines.append("  No links found.")
    lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    for image_path in sys.argv[1:]:
        result = process_image(image_path)
        if not result.ok:
            print(_format_result(result), file=sys.stderr)
        else:
            print(_format_result(result))


if __name__ == "__main__":
    main()
