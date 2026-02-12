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
"""Tests for URL_PATTERN regex."""

import pytest

from extract_links import URL_PATTERN


class TestURLPattern:
    """Test URL regex matching."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("https://example.com", ["https://example.com"]),
            ("http://example.com/path", ["http://example.com/path"]),
            ("https://example.com/path?q=1&b=2", ["https://example.com/path?q=1&b=2"]),
            ("ftp://files.example.com/data", ["ftp://files.example.com/data"]),
            ("www.example.com/page", ["www.example.com/page"]),
            (
                "https://github.com/org/repo/commit/abc123def456",
                ["https://github.com/org/repo/commit/abc123def456"],
            ),
        ],
    )
    def test_matches_valid_urls(self, text, expected):
        assert URL_PATTERN.findall(text) == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            # URL followed by period should not include the period
            ("Visit https://example.com.", ["https://example.com"]),
            # URL in parentheses
            ("(https://example.com)", ["https://example.com"]),
            # URL followed by comma
            ("see https://example.com, then", ["https://example.com"]),
        ],
    )
    def test_strips_trailing_punctuation(self, text, expected):
        assert URL_PATTERN.findall(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "no urls here",
            "example.com/path",  # bare domain, no scheme
            "just some text with numbers 12345",
            "",
        ],
    )
    def test_no_match_on_non_urls(self, text):
        assert URL_PATTERN.findall(text) == []

    def test_multiple_urls_in_text(self):
        text = "Check https://one.com and https://two.com/path for details"
        assert URL_PATTERN.findall(text) == ["https://one.com", "https://two.com/path"]
