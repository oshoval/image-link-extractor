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
"""Tests for OCR artifact correction."""

import pytest

from extract_links import _fix_hex_segment, _fix_ocr_artifacts


class TestFixHexSegment:
    """Test the low-level hex segment fixer."""

    @pytest.mark.parametrize(
        "segment,expected",
        [
            ("Qaeba2f424949c54d975f9fe78c", "0aeba2f424949c54d975f9fe78c"),
            ("abc123Oef456abc123ef456abc", "abc1230ef456abc123ef456abc"),
            ("Qaeba2f4Q4949c54", "0aeba2f404949c54"),
        ],
    )
    def test_fixes_hex_heavy_segments(self, segment, expected):
        assert _fix_hex_segment(segment) == expected

    @pytest.mark.parametrize(
        "segment",
        [
            "getting-started",
            "README",
            "short",
            "a",
            "",
        ],
    )
    def test_skips_non_hex_segments(self, segment):
        assert _fix_hex_segment(segment) == segment


class TestFixOCRArtifacts:
    """Test OCR misread correction in full URLs."""

    @pytest.mark.parametrize(
        "input_url,expected",
        [
            (
                "https://gist.github.com/user/9611aQaeba2f424949c54d975f9fe78c",
                "https://gist.github.com/user/9611a0aeba2f424949c54d975f9fe78c",
            ),
            (
                "https://github.com/org/repo/commit/abc123Oef456abc123ef456abc",
                "https://github.com/org/repo/commit/abc1230ef456abc123ef456abc",
            ),
            (
                "https://example.com/blob/Qaeba2f4Q4949c54d975f9fe78c",
                "https://example.com/blob/0aeba2f404949c54d975f9fe78c",
            ),
        ],
    )
    def test_fixes_hex_segments(self, input_url, expected):
        assert _fix_ocr_artifacts(input_url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/docs/getting-started",
            "https://example.com/api/v2/status",
            "https://github.com/org/my-project/README",
            "https://example.com/a/b/c",
        ],
    )
    def test_does_not_modify_non_hex_paths(self, url):
        assert _fix_ocr_artifacts(url) == url

    def test_host_is_never_modified(self):
        url = "https://aabbccdd.example.com/path"
        assert _fix_ocr_artifacts(url) == url

    def test_ftp_url_passes_through(self):
        url = "ftp://files.example.com/data"
        assert _fix_ocr_artifacts(url) == url

    def test_empty_path(self):
        url = "https://example.com"
        assert _fix_ocr_artifacts(url) == url
