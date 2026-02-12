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
"""Tests for URL continuation detection and line-wrap rejoining."""

import pytest

from extract_links import _looks_like_url_continuation, rejoin_wrapped_urls


class TestLooksLikeURLContinuation:
    """Test the heuristic for detecting URL tail lines."""

    @pytest.mark.parametrize(
        "line",
        [
            "0aeba2f424949c54d975f9fe78c",
            "project/tree/main",
            "index.html?q=foo",
            "v2/status/health",
            "abc123def456ghi789",
        ],
    )
    def test_recognizes_url_tails(self, line):
        assert _looks_like_url_continuation(line) is True

    @pytest.mark.parametrize(
        "line",
        [
            "This is a normal sentence about something.",
            "- bullet point item",
            "• another bullet point",
            "● yet another bullet",
            "* starred item",
            "",
            "    ",
            "hi",  # too short (< 5 chars)
        ],
    )
    def test_rejects_non_url_lines(self, line):
        assert _looks_like_url_continuation(line) is False


class TestRejoinWrappedURLs:
    """Test rejoining URLs split across multiple lines."""

    def test_joins_hex_continuation(self):
        text = "POC link: https://gist.github.com/user/9611a\n0aeba2f424949c54d975f9fe78c"
        result = rejoin_wrapped_urls(text)
        assert "https://gist.github.com/user/9611a0aeba2f424949c54d975f9fe78c" in result

    def test_joins_path_continuation(self):
        text = "Repo: https://github.com/org/example-\nproject/tree/main"
        result = rejoin_wrapped_urls(text)
        assert "https://github.com/org/example-project/tree/main" in result

    def test_does_not_join_normal_text(self):
        text = "Visit https://example.com for details.\nThis is a normal next line."
        result = rejoin_wrapped_urls(text)
        assert "https://example.com" in result
        assert "This is a normal next line." in result
        # Should remain separate lines
        lines = result.split("\n")
        assert len(lines) == 2

    def test_does_not_join_bullet_points(self):
        text = "Link: https://example.com/path\n- Next bullet point"
        result = rejoin_wrapped_urls(text)
        lines = result.split("\n")
        assert len(lines) == 2

    def test_no_urls_passes_through(self):
        text = "Just some text\nwith multiple lines\nand no URLs."
        assert rejoin_wrapped_urls(text) == text

    def test_empty_string(self):
        assert rejoin_wrapped_urls("") == ""
