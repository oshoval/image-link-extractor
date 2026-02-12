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

from extract_links import _fix_ocr_artifacts


class TestFixOCRArtifacts:
    """Test OCR misread correction in URL path segments."""

    @pytest.mark.parametrize(
        "input_url,expected",
        [
            # Q -> 0 in hex hash
            (
                "https://gist.github.com/user/9611aQaeba2f424949c54d975f9fe78c",
                "https://gist.github.com/user/9611a0aeba2f424949c54d975f9fe78c",
            ),
            # O -> 0 in hex hash
            (
                "https://github.com/org/repo/commit/abc123Oef456abc123ef456abc",
                "https://github.com/org/repo/commit/abc1230ef456abc123ef456abc",
            ),
            # Multiple fixes in one segment
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
            # Normal words in path — should NOT be modified
            "https://example.com/docs/getting-started",
            "https://example.com/api/v2/status",
            "https://github.com/org/my-project/README",
            # Short segments — should NOT be modified
            "https://example.com/a/b/c",
        ],
    )
    def test_does_not_modify_non_hex_paths(self, url):
        assert _fix_ocr_artifacts(url) == url

    def test_host_is_never_modified(self):
        # Even if host looks hex-ish, don't touch it
        url = "https://aabbccdd.example.com/path"
        assert _fix_ocr_artifacts(url) == url

    def test_ftp_url_passes_through(self):
        # ftp:// doesn't match the http(s) pattern, returned as-is
        url = "ftp://files.example.com/data"
        assert _fix_ocr_artifacts(url) == url

    def test_empty_path(self):
        url = "https://example.com"
        assert _fix_ocr_artifacts(url) == url
