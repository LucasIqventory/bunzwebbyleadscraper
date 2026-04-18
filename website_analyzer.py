"""
Website Analyzer — Scores a company's website quality.
Checks: SSL, mobile-friendly, load speed, modern tech, basic SEO.
A low score = bad website = hot lead for web services.
"""

import re
import requests
from urllib.parse import urlparse
from config import PAGESPEED_API_KEY, WEBSITE_SCORE_THRESHOLD


PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Tags/patterns that indicate an outdated website
OUTDATED_SIGNALS = [
    b"<table" ,  # table-based layout
    b"<frameset", b"<frame ",
    b"<marquee",
    b"<blink",
    b"<center>",
    b"<font ",
    b"wix.com",
    b"godaddy.com/websites",
    b"weebly.com",
    b"website under construction",
    b"coming soon",
    b"parked free",
    b"buy this domain",
]

MODERN_SIGNALS = [
    b"viewport",           # mobile meta tag
    b"@media",             # responsive CSS
    b"react",
    b"vue",
    b"angular",
    b"tailwind",
    b"bootstrap",
    b"font-awesome",
    b"googleapis.com/css",  # Google Fonts
]


def check_ssl(url: str) -> bool:
    """Check if the site properly supports HTTPS."""
    parsed = urlparse(url)
    https_url = f"https://{parsed.netloc}"
    try:
        resp = requests.get(https_url, timeout=10, allow_redirects=True)
        return resp.url.startswith("https://")
    except Exception:
        return False


def fetch_page(url: str) -> tuple[bytes | None, int | None, str | None]:
    """Fetch page content. Returns (body_bytes, status_code, final_url)."""
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        return resp.content, resp.status_code, resp.url
    except requests.exceptions.SSLError:
        # Try without SSL
        try:
            parsed = urlparse(url)
            http_url = f"http://{parsed.netloc}{parsed.path}"
            resp = requests.get(http_url, timeout=15, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            return resp.content, resp.status_code, resp.url
        except Exception:
            return None, None, None
    except Exception:
        return None, None, None


def get_pagespeed_score(url: str) -> dict | None:
    """Get Google PageSpeed Insights score (0-100)."""
    params = {
        "url": url,
        "strategy": "mobile",
        "category": ["performance", "accessibility", "best-practices", "seo"],
    }
    if PAGESPEED_API_KEY:
        params["key"] = PAGESPEED_API_KEY

    try:
        resp = requests.get(PAGESPEED_URL, params=params, timeout=60)
        if resp.status_code != 200:
            return None
        data = resp.json()
        categories = data.get("lighthouseResult", {}).get("categories", {})
        scores = {}
        for cat_key, cat_data in categories.items():
            score_val = cat_data.get("score")
            if score_val is not None:
                scores[cat_key] = int(score_val * 100)
        return scores
    except Exception:
        return None


def analyze_html(body: bytes) -> dict:
    """Analyze raw HTML for quality signals."""
    body_lower = body.lower()

    outdated_found = []
    for signal in OUTDATED_SIGNALS:
        if signal.lower() in body_lower:
            outdated_found.append(signal.decode(errors="ignore"))

    modern_found = []
    for signal in MODERN_SIGNALS:
        if signal.lower() in body_lower:
            modern_found.append(signal.decode(errors="ignore"))

    has_viewport = b"viewport" in body_lower
    has_responsive = b"@media" in body_lower
    has_favicon = b"favicon" in body_lower or b"shortcut icon" in body_lower

    # Check for copyright year — old year = stale site
    copyright_years = re.findall(rb"(?:\xc2\xa9|\bcopyright\b)[^\d]*(\d{4})", body_lower)
    latest_year = max((int(y) for y in copyright_years), default=None)

    return {
        "outdated_signals": outdated_found,
        "modern_signals": modern_found,
        "has_viewport": has_viewport,
        "has_responsive_css": has_responsive,
        "has_favicon": has_favicon,
        "copyright_year": latest_year,
    }


def compute_website_score(ssl: bool, html_analysis: dict, pagespeed: dict | None) -> int:
    """Compute an overall website quality score (0-100)."""
    score = 50  # Start at baseline

    # SSL
    if ssl:
        score += 10
    else:
        score -= 15

    # Mobile-friendliness
    if html_analysis["has_viewport"]:
        score += 10
    else:
        score -= 10

    if html_analysis["has_responsive_css"]:
        score += 5

    # Outdated signals (each one hurts)
    score -= len(html_analysis["outdated_signals"]) * 5

    # Modern signals (each one helps)
    score += len(html_analysis["modern_signals"]) * 3

    # Copyright year
    cy = html_analysis.get("copyright_year")
    if cy:
        if cy < 2022:
            score -= 10
        elif cy < 2024:
            score -= 5

    # PageSpeed scores
    if pagespeed:
        perf = pagespeed.get("performance", 50)
        seo = pagespeed.get("seo", 50)
        if perf < 40:
            score -= 10
        elif perf > 80:
            score += 10
        if seo < 60:
            score -= 5
        elif seo > 80:
            score += 5

    return max(0, min(100, score))


def analyze_website(url: str, use_pagespeed: bool = True) -> dict:
    """
    Full website analysis. Returns score and detailed findings.
    """
    result = {
        "url": url,
        "reachable": False,
        "ssl": False,
        "score": 0,
        "grade": "F",
        "is_bad": True,
        "issues": [],
        "details": {},
    }

    if not url:
        result["issues"].append("No website at all")
        return result

    # Fetch the page
    body, status, final_url = fetch_page(url)
    if body is None or status is None:
        result["issues"].append("Website unreachable / down")
        return result

    result["reachable"] = True
    result["final_url"] = final_url

    if status >= 400:
        result["issues"].append(f"HTTP error {status}")
        return result

    # SSL check
    ssl_ok = check_ssl(url)
    result["ssl"] = ssl_ok
    if not ssl_ok:
        result["issues"].append("No SSL / HTTPS")

    # HTML analysis
    html_info = analyze_html(body)
    result["details"] = html_info

    if not html_info["has_viewport"]:
        result["issues"].append("Not mobile-friendly (no viewport tag)")
    if html_info["outdated_signals"]:
        result["issues"].append(f"Outdated code detected: {', '.join(html_info['outdated_signals'][:5])}")
    cy = html_info.get("copyright_year")
    if cy and cy < 2023:
        result["issues"].append(f"Stale content (copyright {cy})")
    if not html_info["has_favicon"]:
        result["issues"].append("Missing favicon")

    # PageSpeed (optional, slower)
    pagespeed = None
    if use_pagespeed:
        print(f"    Running PageSpeed analysis for {url}...")
        pagespeed = get_pagespeed_score(url)
        if pagespeed:
            result["pagespeed"] = pagespeed
            perf = pagespeed.get("performance", 0)
            if perf < 40:
                result["issues"].append(f"Very slow (PageSpeed performance: {perf}/100)")

    # Compute score
    score = compute_website_score(ssl_ok, html_info, pagespeed)
    result["score"] = score

    # Grade
    if score >= 80:
        result["grade"] = "A"
    elif score >= 65:
        result["grade"] = "B"
    elif score >= 50:
        result["grade"] = "C"
    elif score >= 35:
        result["grade"] = "D"
    else:
        result["grade"] = "F"

    result["is_bad"] = score < WEBSITE_SCORE_THRESHOLD

    return result
