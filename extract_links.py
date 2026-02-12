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

import re
import sys
from pathlib import Path

import pytesseract
from PIL import Image


# Regex to match URLs — covers http(s), ftp, and common bare domains
URL_PATTERN = re.compile(
    r'(?:https?://|ftp://|www\.)'  # scheme or www.
    r'[^\s<>\"\'\)\]\},;!]*'       # URL body (greedy, stops at whitespace/delimiters)
    r'[^\s<>\"\'\)\]\},;!.\:]'     # don't end on trailing punctuation
)


def preprocess_image(image_path: str) -> Image.Image:
    """Load and preprocess image for better OCR accuracy."""
    img = Image.open(image_path)

    # Convert to grayscale for better OCR
    img = img.convert("L")

    # Scale up small images (Tesseract works better on larger text)
    width, height = img.size
    if width < 1000:
        scale = 2
        img = img.resize((width * scale, height * scale), Image.LANCZOS)

    return img


def extract_text(image_path: str) -> str:
    """Extract text from image using Tesseract OCR."""
    img = preprocess_image(image_path)

    # Use PSM 6 (assume uniform block of text) for slide-like images
    custom_config = r"--oem 3 --psm 6"
    text = pytesseract.image_to_string(img, config=custom_config)

    return text


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
    merged = []

    for line in lines:
        stripped = line.strip()

        # Check if previous line ends with a URL and this line looks like a continuation
        if (
            merged
            and URL_PATTERN.search(merged[-1])
            and stripped
            and not stripped.startswith(("*", "-", "•", "●"))
            and _looks_like_url_continuation(stripped)
        ):
            merged[-1] = merged[-1].rstrip() + stripped
        else:
            merged.append(line)

    return "\n".join(merged)


def _looks_like_url_continuation(line: str) -> bool:
    """Heuristic: does this line look like the tail of a wrapped URL?

    Matches lines that are mostly hex chars, path-like segments,
    or query strings — common URL tails.
    """
    # Remove common OCR artifacts (Q->0, O->0, l->1, etc.)
    cleaned = line.strip().rstrip(".,;:!? ")
    if not cleaned:
        return False

    # URL continuation: hex-heavy string, path segments, query params
    # e.g. "0aeba2f424949c54d975f9fe78c" or "index.html?q=foo"
    alnum_count = sum(1 for c in cleaned if c.isalnum() or c in "/-_.~:?#[]@!$&'()*+,;=%")
    return alnum_count / len(cleaned) >= 0.85 and len(cleaned) >= 5


def _fix_ocr_artifacts(url: str) -> str:
    """Fix common OCR character misreads in URLs.

    Tesseract commonly confuses:
      O <-> 0, Q -> 0, l -> 1, I -> 1, S -> 5, etc.

    We only apply corrections in path segments that look like hex strings
    (e.g. git commit hashes, gist IDs) to avoid breaking real words.
    """
    # Split URL into parts: scheme+host vs path
    match = re.match(r'(https?://[^/]+)(.*)', url)
    if not match:
        return url

    host_part = match.group(1)
    path_part = match.group(2)

    # For each path segment, if it looks hex-ish, fix common OCR errors
    def fix_hex_segment(segment: str) -> str:
        # Count how many chars are valid hex
        hex_chars = sum(1 for c in segment if c in "0123456789abcdefABCDEF")
        if len(segment) >= 8 and hex_chars / max(len(segment), 1) >= 0.7:
            # This segment is likely a hex hash — fix OCR errors
            fixes = {"O": "0", "Q": "0", "l": "1", "I": "1", "S": "5", "G": "6"}
            return "".join(fixes.get(c, c) for c in segment)
        return segment

    # Apply to path segments (split by /)
    segments = path_part.split("/")
    fixed_segments = [fix_hex_segment(s) for s in segments]
    return host_part + "/".join(fixed_segments)


def find_urls(text: str) -> list[str]:
    """Find all URLs in extracted text, handling line-wrapped URLs."""
    # First rejoin URLs that span multiple lines
    text = rejoin_wrapped_urls(text)

    urls = URL_PATTERN.findall(text)

    # Fix common OCR misreads in URL path segments
    urls = [_fix_ocr_artifacts(u) for u in urls]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)

    return unique


def process_image(image_path: str) -> dict:
    """Process a single image: extract text and find URLs."""
    path = Path(image_path)
    if not path.exists():
        return {"file": image_path, "error": f"File not found: {image_path}"}
    if not path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
        return {"file": image_path, "error": f"Unsupported format: {path.suffix}"}

    text = extract_text(image_path)
    urls = find_urls(text)

    return {"file": image_path, "text": text, "urls": urls}


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    image_paths = sys.argv[1:]

    for image_path in image_paths:
        result = process_image(image_path)

        if "error" in result:
            print(f"ERROR: {result['error']}", file=sys.stderr)
            continue

        print(f"=== {result['file']} ===")
        urls = result["urls"]
        if urls:
            print(f"Found {len(urls)} link(s):\n")
            for i, url in enumerate(urls, 1):
                print(f"  {i}. {url}")
        else:
            print("  No links found.")

        print()


if __name__ == "__main__":
    main()
