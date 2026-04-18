"""
Email Finder — Attempts to find owner/decision-maker emails for a company.
Uses multiple strategies:
  1. Hunter.io API (if key provided)
  2. Common email pattern guessing from domain
  3. Scraping contact pages for mailto: links
"""

import re
import requests
from urllib.parse import urlparse
from config import HUNTER_API_KEY


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    if not url:
        return ""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().replace("www.", "")
    return domain


def hunter_domain_search(domain: str) -> list[dict]:
    """Use Hunter.io to find emails associated with a domain."""
    if not HUNTER_API_KEY or not domain:
        return []

    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
        "limit": 10,
        "type": "personal",  # personal emails, not generic
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        emails = data.get("data", {}).get("emails", [])

        results = []
        for e in emails:
            results.append({
                "email": e.get("value", ""),
                "first_name": e.get("first_name", ""),
                "last_name": e.get("last_name", ""),
                "position": e.get("position", ""),
                "confidence": e.get("confidence", 0),
                "source": "hunter.io",
            })

        # Sort by seniority — prioritize owners, presidents, CEOs
        owner_keywords = ["owner", "president", "ceo", "founder", "director", "principal", "partner"]
        results.sort(key=lambda x: (
            -1 if any(kw in (x.get("position") or "").lower() for kw in owner_keywords) else 0,
            -x.get("confidence", 0),
        ))

        return results
    except Exception:
        return []


def hunter_email_verify(email: str) -> str:
    """Verify an email via Hunter.io. Returns 'valid', 'invalid', or 'unknown'."""
    if not HUNTER_API_KEY or not email:
        return "unknown"

    url = "https://api.hunter.io/v2/email-verifier"
    params = {"email": email, "api_key": HUNTER_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return "unknown"
        data = resp.json()
        return data.get("data", {}).get("status", "unknown")
    except Exception:
        return "unknown"


def scrape_contact_emails(website_url: str) -> list[str]:
    """Scrape the company website for email addresses on contact/about pages."""
    if not website_url:
        return []

    emails_found = set()
    pages_to_check = [
        website_url,
        website_url.rstrip("/") + "/contact",
        website_url.rstrip("/") + "/contact-us",
        website_url.rstrip("/") + "/about",
        website_url.rstrip("/") + "/about-us",
    ]

    email_pattern = re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    )

    # Exclude junk emails
    junk_patterns = [
        "example.com", "sentry.io", "wixpress.com", "wordpress.com",
        "placeholder", "email.com", "domain.com", "yoursite.com",
        ".png", ".jpg", ".gif", ".js", ".css",
    ]

    for page_url in pages_to_check:
        try:
            resp = requests.get(page_url, timeout=10, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code != 200:
                continue

            found = email_pattern.findall(resp.text)
            for em in found:
                em_lower = em.lower()
                if not any(junk in em_lower for junk in junk_patterns):
                    emails_found.add(em_lower)
        except Exception:
            continue

    return list(emails_found)


def guess_owner_emails(domain: str, company_name: str) -> list[str]:
    """Generate common owner email patterns."""
    if not domain:
        return []

    # Common patterns for small/medium business owner emails
    patterns = [
        f"info@{domain}",
        f"contact@{domain}",
        f"owner@{domain}",
        f"admin@{domain}",
        f"sales@{domain}",
    ]
    return patterns


def find_emails(company_name: str, website_url: str) -> dict:
    """
    Main email-finding function. Tries all strategies and returns best results.
    """
    domain = extract_domain(website_url)

    result = {
        "domain": domain,
        "owner_emails": [],       # Personal emails (best)
        "contact_emails": [],     # From website scraping
        "guessed_emails": [],     # Pattern-based guesses
        "best_email": None,
        "best_name": None,
    }

    # Strategy 1: Hunter.io
    if HUNTER_API_KEY and domain:
        print(f"    Searching Hunter.io for {domain}...")
        hunter_results = hunter_domain_search(domain)
        for h in hunter_results:
            result["owner_emails"].append(h)

    # Strategy 2: Scrape website
    if website_url:
        print(f"    Scraping contact pages for {domain}...")
        scraped = scrape_contact_emails(website_url)
        result["contact_emails"] = scraped

    # Strategy 3: Pattern guessing
    if domain:
        result["guessed_emails"] = guess_owner_emails(domain, company_name)

    # Pick the best email
    if result["owner_emails"]:
        best = result["owner_emails"][0]
        result["best_email"] = best["email"]
        fname = best.get("first_name", "")
        lname = best.get("last_name", "")
        if fname or lname:
            result["best_name"] = f"{fname} {lname}".strip()
    elif result["contact_emails"]:
        # Prefer non-generic emails
        generic = {"info@", "contact@", "admin@", "support@", "sales@", "hello@"}
        personal = [e for e in result["contact_emails"] if not any(e.startswith(g) for g in generic)]
        if personal:
            result["best_email"] = personal[0]
        else:
            result["best_email"] = result["contact_emails"][0]
    elif result["guessed_emails"]:
        result["best_email"] = result["guessed_emails"][0]

    return result
