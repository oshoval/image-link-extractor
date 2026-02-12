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
"""Tests for the find_urls integration (rejoin + extract + fix)."""

from extract_links import find_urls


class TestFindURLs:
    """Test the full find_urls pipeline."""

    def test_simple_url(self):
        text = "Visit https://example.com/docs for info."
        assert find_urls(text) == ["https://example.com/docs"]

    def test_multiple_urls(self):
        text = "See https://one.com and https://two.com/path"
        result = find_urls(text)
        assert "https://one.com" in result
        assert "https://two.com/path" in result
        assert len(result) == 2

    def test_wrapped_url_with_ocr_artifact(self):
        """Simulate real OCR output: URL wraps + Q misread as 0."""
        text = "POC link: https://gist.github.com/user/9611a\nQaeba2f424949c54d975f9fe78c\n"
        result = find_urls(text)
        assert result == ["https://gist.github.com/user/9611a0aeba2f424949c54d975f9fe78c"]

    def test_deduplication(self):
        text = "https://example.com/page and again https://example.com/page"
        result = find_urls(text)
        assert result == ["https://example.com/page"]
        assert len(result) == 1

    def test_no_urls(self):
        text = "Just some text with no links at all."
        assert find_urls(text) == []

    def test_empty_text(self):
        assert find_urls("") == []

    def test_realistic_slide_text(self):
        """Simulate OCR output from a presentation slide."""
        text = (
            "Self-Heal: Automating Allowlist Maintenance\n"
            "\n"
            "e When Cl hits a new unexpected error,\n"
            "developer need to triage the error, either fix it\n"
            "or add to allowlist (at least until cutoff)\n"
            "\n"
            "e POC link: https://gist.github.com/user/9611a\n"
            "0aeba2f424949c54d975f9fe78c\n"
        )
        result = find_urls(text)
        assert len(result) == 1
        assert result[0] == "https://gist.github.com/user/9611a0aeba2f424949c54d975f9fe78c"
