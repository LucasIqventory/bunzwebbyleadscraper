"""
Bunz Webby Lead Scraper — Fully Automated Pipeline

Finds massive companies in high-revenue industries with bad/no websites,
then emails their owners automatically.

Just run it:
  python main.py              # Full auto — discover, analyze, find emails, send
  python main.py --dry-run    # Same thing but don't actually send emails
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime

from config import OUTPUT_DIR
from scraper import scrape_leads
from website_analyzer import analyze_website
from email_finder import find_emails
from emailer import send_outreach, log_results


def save_leads_csv(leads: list[dict], filename: str = "leads.csv"):
    """Save all lead data to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    if not leads:
        print("[!] No leads to save.")
        return

    fieldnames = [
        "name", "domain", "industry",
        "website", "has_website",
        "website_score", "website_grade", "website_is_bad", "website_issues",
        "best_email", "best_name", "contact_emails",
        "phone", "address", "search_snippet",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"\n[*] Leads saved to {filepath}")


def save_leads_json(leads: list[dict], filename: str = "leads.json"):
    """Save full lead data to JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, default=str)

    print(f"[*] Full data saved to {filepath}")


def run_pipeline(dry_run: bool = False, skip_pagespeed: bool = False, delay_seconds: int = 30):
    """
    Fully automated pipeline. No arguments needed.
    Discovers → Analyzes → Finds emails → Sends.
    """

    mode = "DRY RUN (no emails sent)" if dry_run else "LIVE — EMAILS WILL BE SENT"

    print("=" * 60)
    print(f"  BUNZ WEBBY LEAD SCRAPER")
    print(f"  Mode: {mode}")
    print("=" * 60)

    # ── Step 1: Discover companies ──
    print("\n" + "─" * 40)
    print("STEP 1: Discovering companies across all industries...")
    print("─" * 40)
    leads = scrape_leads()

    if not leads:
        print("[!] No leads found. Check your API key or internet connection.")
        return

    # ── Step 2: Analyze websites ──
    print("\n" + "─" * 40)
    print(f"STEP 2: Analyzing {len(leads)} websites...")
    print("─" * 40)

    for lead in leads:
        print(f"\n  [{lead['name']}]")
        analysis = analyze_website(lead["website"], use_pagespeed=not skip_pagespeed)
        lead["website_score"] = analysis["score"]
        lead["website_grade"] = analysis["grade"]
        lead["website_is_bad"] = analysis["is_bad"]
        lead["website_issues"] = analysis.get("issues", [])
        lead["website_reachable"] = analysis["reachable"]

        status = "BAD" if analysis["is_bad"] else "OK"
        print(f"    Score: {analysis['score']}/100 (Grade: {analysis['grade']}) — {status}")
        if analysis["issues"]:
            for issue in analysis["issues"][:3]:
                print(f"      - {issue}")

        time.sleep(0.5)

    # ── Step 3: Find emails ──
    print("\n" + "─" * 40)
    print("STEP 3: Finding owner/contact emails...")
    print("─" * 40)

    for lead in leads:
        print(f"\n  [{lead['name']}]")
        email_data = find_emails(lead["name"], lead.get("website", ""))
        lead["best_email"] = email_data["best_email"]
        lead["best_name"] = email_data.get("best_name")
        lead["contact_emails"] = ", ".join(email_data.get("contact_emails", []))
        lead["owner_emails"] = email_data.get("owner_emails", [])

        if email_data["best_email"]:
            name_part = f" ({email_data['best_name']})" if email_data.get("best_name") else ""
            print(f"    Email: {email_data['best_email']}{name_part}")
        else:
            print(f"    No email found")

        time.sleep(0.3)

    # ── Step 4: Filter leads worth emailing ──
    hot_leads = [
        l for l in leads
        if l.get("best_email") and l.get("website_is_bad")
    ]

    print("\n" + "─" * 40)
    print(f"RESULTS")
    print("─" * 40)
    print(f"  Total companies found:  {len(leads)}")
    print(f"  Bad website (< 50):     {sum(1 for l in leads if l.get('website_is_bad'))}")
    print(f"  Good website:           {sum(1 for l in leads if not l.get('website_is_bad'))}")
    print(f"  Emails found:           {sum(1 for l in leads if l.get('best_email'))}")
    print(f"  QUALIFIED LEADS:        {len(hot_leads)}")

    # ── Step 5: Save data ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_leads_csv(leads, f"leads_{timestamp}.csv")
    save_leads_json(leads, f"leads_{timestamp}.json")

    # ── Step 6: Send emails ──
    if hot_leads:
        sending = not dry_run
        print("\n" + "─" * 40)
        print(f"STEP 6: {'SENDING' if sending else 'Previewing'} emails to {len(hot_leads)} qualified leads...")
        print("─" * 40)

        results = send_outreach(hot_leads, dry_run=dry_run, delay_seconds=delay_seconds)
        log_results(results, f"email_log_{timestamp}.csv")

        sent_count = sum(1 for r in results if r["sent"])
        print(f"\n  Emails {'sent' if sending else 'previewed'}: {sent_count}/{len(results)}")
    else:
        print("\n[!] No qualified leads to email this run.")

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Bunz Webby Lead Scraper — fully automated")
    parser.add_argument("--dry-run", action="store_true", help="Run everything but don't actually send emails")
    parser.add_argument("--skip-pagespeed", action="store_true", help="Skip PageSpeed analysis (faster)")
    parser.add_argument("--delay", type=int, default=30, help="Seconds between emails (default 30)")
    args = parser.parse_args()

    run_pipeline(
        dry_run=args.dry_run,
        skip_pagespeed=args.skip_pagespeed,
        delay_seconds=args.delay,
    )


if __name__ == "__main__":
    main()
