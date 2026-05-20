"""Web search pipeline: DuckDuckGo → httpx → trafilatura → chunks."""

from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def _get_headers(engine: str = "generic", url: str | None = None) -> dict:
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
    }
    
    # Custom headers based on User-Agent to match Chrome vs Firefox/Safari
    if "Chrome" in ua:
        headers["sec-ch-ua"] = '"Not A(An:Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"'
        headers["sec-ch-ua-mobile"] = "?0"
        headers["sec-ch-ua-platform"] = '"Windows"' if "Windows" in ua else '"macOS"'
    
    # Set the Referer based on the target engine or generic website URL
    if engine == "ddg":
        headers["Referer"] = "https://duckduckgo.com/"
    elif engine == "brave":
        headers["Referer"] = "https://search.brave.com/"
    elif engine == "searxng" and url:
        headers["Referer"] = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    elif url:
        try:
            parsed = urlparse(url)
            headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        except Exception:
            headers["Referer"] = "https://www.google.com/"
    else:
        headers["Referer"] = "https://www.google.com/"
        
    return headers
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=20.0)

# Anti-Blackhole Logic: Track if an engine is currently failing
ENGINE_STATUS = {
    "ddg": {"ok": True, "failed_at": 0.0},
}

def _is_engine_ok(name: str) -> bool:
    status = ENGINE_STATUS.get(name)
    if not status or status["ok"]:
        return True
    # Cooldown for 10 minutes
    if time.time() - status["failed_at"] > 600:
        status["ok"] = True
        return True
    return False

def _mark_engine_failed(name: str):
    ENGINE_STATUS[name] = {"ok": False, "failed_at": time.time()}

DDG_ENDPOINT = "https://html.duckduckgo.com/html/"
SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.mdosch.de",
    "https://searx.tiekoetter.com",
    "https://searx.priv.at",
    "https://searx.work",
    "https://priv.au",
]

CHUNK_MAX_TOKENS = 1500  # ~6000 chars
MIN_TEXT_LEN = 300


@dataclass
class Source:
    url: str
    domain: str
    title: str
    snippet: str
    clean_text: str
    chunks: list[str]
    tier: int
    date_fetched: str
    is_paywalled: bool = False
    angle_id: str = ""


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lstrip("www.")
    except Exception:
        return url


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]


def _chunk_text(text: str, max_chars: int = CHUNK_MAX_TOKENS * 4) -> list[str]:
    """Split at paragraph boundaries, keeping chunks under max_chars."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        # If a single paragraph exceeds max_chars, split it by sentence/char
        if len(para) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            # Hard-split the oversized paragraph
            for i in range(0, len(para), max_chars):
                chunks.append(para[i:i + max_chars])
            continue
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para).strip() if current else para
    if current:
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]


def _amp_fallback(url: str, client: httpx.Client) -> str | None:
    stripped = url.replace("https://", "").replace("http://", "")
    amp_url = f"https://amp.google.com/v/s/{stripped}"
    try:
        html = client.get(amp_url).text
        return trafilatura.extract(html, favor_precision=True)
    except Exception:
        return None


def _fetch_and_extract(url: str, client: httpx.Client) -> tuple[str | None, str | None, bool]:
    """Return (html, clean_text, is_paywalled)."""
    try:
        resp = client.get(url, headers=_get_headers("generic", url))
        html = resp.text
    except Exception as e:
        logger.debug(f"Fetch failed {url}: {e}")
        return None, None, False

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        deduplicate=True,
    )
    if text and len(text) >= MIN_TEXT_LEN:
        return html, text, False

    text = _amp_fallback(url, client)
    if text and len(text) >= MIN_TEXT_LEN:
        return html, text, False

    return html, None, True


def _ddg_search(query: str, client: httpx.Client) -> list[dict]:
    """Return list of {title, url, snippet}."""
    if not _is_engine_ok("ddg"):
        return []
        
    try:
        headers = _get_headers("ddg")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        resp = client.post(
            DDG_ENDPOINT,
            data={"q": query, "b": "", "kl": ""},
            headers=headers,
            follow_redirects=True,
        )
        if resp.status_code in (403, 429):
            raise httpx.HTTPStatusError("DDG Blocked", request=resp.request, response=resp)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            title_el = result.select_one(".result__title")
            url_el = result.select_one(".result__url")
            snippet_el = result.select_one(".result__snippet")
            if not title_el or not url_el:
                continue
            raw_url = title_el.find("a", href=True)
            if not raw_url:
                continue
            href = raw_url["href"]
            # DDG wraps URLs — try to extract direct URL
            if href.startswith("//duckduckgo.com/l/"):
                # Extract uddg param
                from urllib.parse import parse_qs, urlparse as _up
                qs = parse_qs(_up(href).query)
                uddg = qs.get("uddg", [None])[0]
                if uddg:
                    href = uddg
            if not href.startswith("http"):
                continue
            results.append({
                "title": title_el.get_text(strip=True),
                "url": href,
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
        return results
    except Exception:
        _mark_engine_failed("ddg")
        from cormorant.ui import print_warn
        print_warn("DuckDuckGo blacklisted us or timed out. Switching to backup engines...")
        return []


def _brave_search(query: str, client: httpx.Client) -> list[dict]:
    """Scrape Brave Search HTML results."""
    try:
        headers = _get_headers("brave")
        headers["Accept-Encoding"] = "gzip, deflate"
        resp = client.get(
            "https://search.brave.com/search",
            params={"q": query},
            headers=headers,
            timeout=httpx.Timeout(12.0),
        )
        if resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".snippet, .web-detection, .result"):
            if "llm-snippet" in result.get('id', ''):
                continue
            title_el = result.select_one(".title, .snippet-title, h3, h2")
            link_el = result.find("a", href=True)
            snippet_el = result.select_one(".content, .snippet-content, .snippet-description, p")
            if not title_el or not link_el:
                continue
            
            href = link_el["href"]
            if not href.startswith("http"):
                continue
                
            results.append({
                "title": title_el.get_text(strip=True),
                "url": href,
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
        return results
    except Exception as e:
        logger.debug(f"Brave Search failed: {e}")
        return []


def _searxng_html_search(query: str, client: httpx.Client) -> list[dict]:
    """Scrape standard HTML search results from public SearXNG instances."""
    for instance in SEARXNG_INSTANCES:
        try:
            headers = _get_headers("searxng", instance)
            headers["Accept-Encoding"] = "gzip, deflate"
            resp = client.get(
                f"{instance}/search",
                params={"q": query},
                headers=headers,
                timeout=httpx.Timeout(12.0),
            )
            if resp.status_code != 200:
                continue
            
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            
            for result in soup.select("article.result, div.result, .result"):
                title_el = result.find(["h3", "h4", "h2"])
                link_el = result.find("a", href=True)
                snippet_el = result.select_one(".content, .snippet, p")
                
                if not title_el or not link_el:
                    continue
                
                href = link_el["href"]
                if not href.startswith("http"):
                    continue
                
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
            
            if results:
                logger.info(f"  Successfully fetched {len(results)} results from SearXNG ({instance})")
                return results
        except Exception as e:
            logger.debug(f"SearXNG HTML scrape failed for {instance}: {e}")
    return []


def search_and_fetch(
    queries: list[str],
    angle_id: str,
    project_dir: Path,
    domain_tiers: dict[str, int],
    existing_sources: dict[str, dict] | None = None,
) -> list[Source]:
    """Main entry point. Returns a list of Source objects with clean text + chunks."""
    cache_dir = project_dir / "cache" / f"{angle_id}_raw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = cache_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    if existing_sources is None:
        existing_sources = {}

    client = httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True)

    # Collect candidates from all queries
    candidates: list[dict] = []
    seen_urls: set[str] = set()

    for i, query in enumerate(queries):
        logger.info(f"  Searching: {query}")
        
        # Slower query pacing: 6.0 to 12.0 seconds delay to prevent bot blocking
        time.sleep(random.uniform(6.0, 12.0)) 
        
        # 1. Primary: DuckDuckGo
        results = _ddg_search(query, client)
        
        # 2. Secondary Fallback: Brave Search
        if not results:
            logger.info("  DDG failed/blocked, trying Brave Search fallback...")
            time.sleep(random.uniform(3.0, 5.0))
            results = _brave_search(query, client)
            
        # 3. Tertiary Fallback: SearXNG HTML Scraper
        if not results:
            logger.info("  Brave Search failed/blocked, trying randomized SearXNG HTML fallback...")
            time.sleep(random.uniform(3.0, 5.0))
            random.shuffle(SEARXNG_INSTANCES)
            results = _searxng_html_search(query, client)
        
        # If still nothing, try a simplified query with the full cascade
        if not results and len(query.split()) > 4:
            simplified = " ".join(query.split()[:4])
            logger.info(f"  Retrying with simplified query: {simplified}")
            time.sleep(random.uniform(4.0, 6.0))
            
            results = _ddg_search(simplified, client)
            if not results:
                time.sleep(random.uniform(3.0, 5.0))
                results = _brave_search(simplified, client)
            if not results:
                time.sleep(random.uniform(3.0, 5.0))
                results = _searxng_html_search(simplified, client)

        for r in results:
            url = r["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            dom = _domain(url)
            tier = domain_tiers.get(dom, 3)
            # Snippet relevance: count query word overlaps
            query_words = set(query.lower().split())
            snippet_words = set(r["snippet"].lower().split())
            relevance = len(query_words & snippet_words)
            candidates.append({**r, "domain": dom, "tier": tier, "relevance": relevance})

    # Sort: tier ascending (lower = better), then relevance descending
    candidates.sort(key=lambda x: (x["tier"], -x["relevance"]))
    top = candidates[:8]

    sources: list[Source] = []
    from datetime import date
    today = str(date.today())

    for cand in top:
        url = cand["url"]
        dom = cand["domain"]
        url_hash = _url_hash(url)
        cache_txt = cache_dir / f"{dom}_{url_hash}.txt"
        cache_html = cache_dir / f"{dom}_{url_hash}.html"

        # Reuse cache if previously fetched
        if url in existing_sources and cache_txt.exists():
            clean_text = cache_txt.read_text()
            chunks = _chunk_text(clean_text)
            src = Source(
                url=url,
                domain=dom,
                title=cand["title"],
                snippet=cand["snippet"],
                clean_text=clean_text,
                chunks=chunks,
                tier=cand["tier"],
                date_fetched=existing_sources[url].get("date_fetched", today),
                is_paywalled=existing_sources[url].get("is_paywalled", False),
                angle_id=angle_id,
            )
            sources.append(src)
            continue

        html, clean_text, is_paywalled = _fetch_and_extract(url, client)

        if html:
            try:
                cache_html.write_text(html)
            except Exception:
                pass

        if clean_text:
            try:
                cache_txt.write_text(clean_text)
            except Exception:
                pass
            chunks = _chunk_text(clean_text)
            # Cache individual chunks
            for ci, chunk in enumerate(chunks):
                (chunks_dir / f"{dom}_{url_hash}_chunk{ci+1}.txt").write_text(chunk)
        else:
            clean_text = ""
            chunks = []

        src = Source(
            url=url,
            domain=dom,
            title=cand["title"],
            snippet=cand["snippet"],
            clean_text=clean_text,
            chunks=chunks,
            tier=cand["tier"],
            date_fetched=today,
            is_paywalled=is_paywalled,
            angle_id=angle_id,
        )
        sources.append(src)

        if is_paywalled:
            logger.info(f"  Paywalled: {url}")
        else:
            logger.info(f"  Fetched ({len(clean_text)} chars): {url}")

    client.close()
    return sources


def targeted_research(
    angle_id: str,
    gaps: list[str],
    project_dir: Path,
    domain_tiers: dict[str, int],
    existing_sources: dict[str, dict] | None = None,
) -> list[Source]:
    """Re-search with authoritative source targeting for thin/paywalled evidence."""
    target_queries = []
    for gap in gaps[:3]:
        target_queries.append(f"site:sec.gov {gap}")
        target_queries.append(f"site:europa.eu {gap}")
        target_queries.append(f"{gap} filetype:pdf annual report")
        target_queries.append(f"{gap} site:imf.org OR site:worldbank.org")

    return search_and_fetch(
        queries=target_queries[:5],
        angle_id=f"{angle_id}_targeted",
        project_dir=project_dir,
        domain_tiers=domain_tiers,
        existing_sources=existing_sources,
    )
