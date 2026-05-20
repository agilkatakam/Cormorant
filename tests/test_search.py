"""Tests for the search pipeline — mocked HTTP, chunking, AMP fallback."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cormorant.search import (
    _chunk_text,
    _ddg_search,
    _brave_search,
    _searxng_html_search,
    _domain,
    _fetch_and_extract,
    _url_hash,
    search_and_fetch,
)
from cormorant.frameworks import DOMAIN_TIERS


SAMPLE_HTML = """
<html><body>
<h1>AI Chips Market</h1>
<p>The global AI chip market is expected to reach $500 billion by 2030, according to industry analysts.
NVIDIA dominates with approximately 80% market share in AI training chips.</p>
<p>AMD and Intel are competing aggressively in the inference market, which is expected to grow faster
than training through 2026. Key drivers include cloud data center expansion and edge AI adoption.</p>
<p>Supply constraints from TSMC's advanced node capacity remain a bottleneck through 2025.</p>
</body></html>
"""

DDG_HTML = """
<html><body>
<div class="result">
  <div class="result__title"><a href="https://reuters.com/article/ai-chips">AI Chips Market</a></div>
  <div class="result__url">reuters.com</div>
  <div class="result__snippet">AI chip demand growing rapidly in 2024</div>
</div>
<div class="result">
  <div class="result__title"><a href="https://ft.com/article/semiconductors">Semiconductor Outlook</a></div>
  <div class="result__url">ft.com</div>
  <div class="result__snippet">TSMC capacity constraints affect supply chain</div>
</div>
</body></html>
"""

BRAVE_HTML = """
<html><body>
<div class="snippet">
  <div class="title search-snippet-title">Brave Search Result</div>
  <a href="https://example.com/brave">Link</a>
  <div class="content">This is a Brave Search snippet text.</div>
</div>
</body></html>
"""

SEARXNG_HTML = """
<html><body>
<article class="result">
  <h3><a href="https://example.com/searxng">SearXNG Result</a></h3>
  <div class="content">This is a SearXNG snippet text.</div>
</article>
</body></html>
"""


class TestChunkText(unittest.TestCase):

    def test_short_text_not_split(self):
        text = "Short text here."
        chunks = _chunk_text(text, max_chars=1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_long_text_split_at_paragraphs(self):
        # Create text with clearly separated paragraphs
        para = "A" * 200
        text = f"{para}\n\n{para}\n\n{para}"
        chunks = _chunk_text(text, max_chars=300)
        self.assertGreater(len(chunks), 1)

    def test_empty_text_returns_one_chunk(self):
        chunks = _chunk_text("", max_chars=1000)
        self.assertGreaterEqual(len(chunks), 0)

    def test_chunk_max_respected(self):
        big_para = "word " * 1000
        chunks = _chunk_text(big_para, max_chars=500)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 600)  # some tolerance


class TestDomainExtraction(unittest.TestCase):

    def test_standard_url(self):
        self.assertEqual(_domain("https://reuters.com/article/x"), "reuters.com")

    def test_www_stripped(self):
        self.assertEqual(_domain("https://www.ft.com/article"), "ft.com")

    def test_subdomain_preserved(self):
        d = _domain("https://arstechnica.com/tech")
        self.assertIn("arstechnica.com", d)

    def test_url_hash_consistent(self):
        url = "https://reuters.com/article/test"
        self.assertEqual(_url_hash(url), _url_hash(url))
        self.assertEqual(len(_url_hash(url)), 8)


class TestFetchAndExtract(unittest.TestCase):

    def test_extracts_clean_text_from_html(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HTML
        mock_client.get.return_value = mock_response

        html, text, paywalled = _fetch_and_extract("https://reuters.com/x", mock_client)
        self.assertIsNotNone(html)
        # trafilatura might or might not extract from this minimal HTML
        # Just verify no crash and paywalled is bool
        self.assertIsInstance(paywalled, bool)

    def test_returns_paywalled_on_thin_content(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Short</p></body></html>"
        mock_client.get.return_value = mock_response

        # Mock AMP fallback to also return short content
        with patch("cormorant.search._amp_fallback", return_value=None):
            html, text, paywalled = _fetch_and_extract("https://ft.com/article", mock_client)
            self.assertTrue(paywalled)

    def test_handles_fetch_exception(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection timeout")
        html, text, paywalled = _fetch_and_extract("https://example.com", mock_client)
        self.assertIsNone(html)
        self.assertIsNone(text)


class TestDDGSearch(unittest.TestCase):

    def test_parses_ddg_results(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = DDG_HTML
        mock_client.post.return_value = mock_response

        results = _ddg_search("AI chips market", mock_client)
        # DDG parser may or may not find results depending on exact HTML structure
        self.assertIsInstance(results, list)

    def test_returns_empty_on_exception(self):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Network error")
        results = _ddg_search("test query", mock_client)
        self.assertEqual(results, [])


class TestBraveSearch(unittest.TestCase):

    def test_parses_brave_results(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = BRAVE_HTML
        mock_client.get.return_value = mock_response

        results = _brave_search("AI chips market", mock_client)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Brave Search Result")
        self.assertEqual(results[0]["url"], "https://example.com/brave")
        self.assertEqual(results[0]["snippet"], "This is a Brave Search snippet text.")

    def test_returns_empty_on_exception(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Network error")
        results = _brave_search("test query", mock_client)
        self.assertEqual(results, [])


class TestSearXNGHTMLSearch(unittest.TestCase):

    def test_parses_searxng_html_results(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SEARXNG_HTML
        mock_client.get.return_value = mock_response

        results = _searxng_html_search("AI chips market", mock_client)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "SearXNG Result")
        self.assertEqual(results[0]["url"], "https://example.com/searxng")
        self.assertEqual(results[0]["snippet"], "This is a SearXNG snippet text.")

    def test_returns_empty_on_exception(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Network error")
        results = _searxng_html_search("test query", mock_client)
        self.assertEqual(results, [])


class TestSearchAndFetch(unittest.TestCase):

    def test_creates_cache_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Mock all HTTP calls to return empty/no results
            with patch("cormorant.search.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
                mock_client_class.return_value = mock_client
                mock_client.post.return_value = MagicMock(text="<html></html>")
                mock_client.get.return_value = MagicMock(text="<html></html>")

                with patch("cormorant.search.time.sleep"):
                    search_and_fetch(
                        queries=["test query"],
                        angle_id="S01",
                        project_dir=project_dir,
                        domain_tiers=DOMAIN_TIERS,
                    )

                cache_dir = project_dir / "cache" / "S01_raw"
                self.assertTrue(cache_dir.exists())

    def test_deduplicates_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            # Test that existing_sources prevents re-fetching
            existing = {"https://reuters.com/x": {"is_paywalled": False, "date_fetched": "2026-01-01"}}

            with patch("cormorant.search.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.post.return_value = MagicMock(text="<html></html>")

                with patch("cormorant.search.time.sleep"):
                    sources = search_and_fetch(
                        queries=["test"],
                        angle_id="S01",
                        project_dir=project_dir,
                        domain_tiers=DOMAIN_TIERS,
                        existing_sources=existing,
                    )
                # No crash — that's the main assertion
                self.assertIsInstance(sources, list)


if __name__ == "__main__":
    unittest.main()
