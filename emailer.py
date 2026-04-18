"""
Email Sender — Sends personalized cold outreach emails to leads.
Uses SMTP with TLS. Includes rate limiting and logging.
"""

import smtplib
import time
import csv
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import (
    SMTP_HOST, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD,
    YOUR_NAME, YOUR_COMPANY, YOUR_PHONE, YOUR_WEBSITE, OUTPUT_DIR,
)


def build_email_no_website(company_name: str, contact_name: str | None) -> tuple[str, str]:
    """Email template for companies with NO website."""
    greeting = f"Hi {contact_name}," if contact_name else f"Hi,"
    subject = f"{company_name} — You're Invisible Online"

    body = f"""{greeting}

I was looking for {company_name} online and couldn't find a website for your company. In 2026, that means potential customers searching for your services are finding your competitors instead.

Here's what you're likely missing out on:
• Customers Googling services you offer — and landing on competitor sites
• Credibility — 75% of people judge a business by its website
• 24/7 lead generation while you sleep

I build clean, fast, mobile-friendly websites specifically for companies like yours. No fluff, no long timelines — just a professional site that makes you money.

I'd love to set up a quick 10-minute call to show you what I have in mind for {company_name}.

Would this week or next work better for a quick chat?

Best,
{YOUR_NAME}
{YOUR_COMPANY}
{YOUR_PHONE}
{YOUR_WEBSITE}"""

    return subject, body


def build_email_bad_website(
    company_name: str,
    contact_name: str | None,
    website_url: str,
    issues: list[str],
    score: int,
) -> tuple[str, str]:
    """Email template for companies with a BAD website."""
    greeting = f"Hi {contact_name}," if contact_name else f"Hi,"
    subject = f"{company_name} — Your Website Is Costing You Customers"

    # Build issues list
    issues_text = ""
    if issues:
        issue_bullets = "\n".join(f"  • {issue}" for issue in issues[:4])
        issues_text = f"\nI took a quick look at {website_url} and noticed a few things:\n{issue_bullets}\n"

    body = f"""{greeting}

I came across {company_name} while researching companies in your area and checked out your website.
{issues_text}
These issues directly affect whether customers trust your business and whether Google shows you in search results. Your site scored {score}/100 on my analysis.

I specialize in rebuilding websites for established companies like yours — fast, modern, mobile-friendly sites that actually generate leads.

Here's what a refresh would look like:
• Modern design that builds instant trust
• Mobile-optimized (60%+ of your traffic is mobile)
• Fast loading speeds (Google ranks this)
• Clear calls-to-action that convert visitors into customers

Would you be open to a quick 10-minute call this week? I can walk you through exactly what I'd do for {company_name} — no pressure, no obligation.

Best,
{YOUR_NAME}
{YOUR_COMPANY}
{YOUR_PHONE}
{YOUR_WEBSITE}"""

    return subject, body


def send_email(to_email: str, subject: str, body: str, dry_run: bool = False) -> bool:
    """Send a single email via SMTP. Returns True on success."""
    if dry_run:
        print(f"    [DRY RUN] Would send to {to_email}: {subject}")
        return True

    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("    [!] SMTP credentials not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{YOUR_NAME} <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"    [✓] Sent to {to_email}")
        return True
    except Exception as e:
        print(f"    [✗] Failed to send to {to_email}: {e}")
        return False


def send_outreach(leads: list[dict], dry_run: bool = True, delay_seconds: int = 30) -> list[dict]:
    """
    Send outreach emails to qualified leads.
    Returns list of send results for logging.
    """
    results = []

    for i, lead in enumerate(leads):
        email = lead.get("best_email")
        if not email:
            print(f"  [skip] {lead['name']} — no email found")
            continue

        company = lead["name"]
        contact_name = lead.get("best_name")
        website = lead.get("website", "")
        has_website = lead.get("has_website", False)
        is_bad = lead.get("website_is_bad", True)
        issues = lead.get("website_issues", [])
        score = lead.get("website_score", 0)

        # Pick the right template
        if not has_website or not website:
            subject, body = build_email_no_website(company, contact_name)
            email_type = "no_website"
        elif is_bad:
            subject, body = build_email_bad_website(company, contact_name, website, issues, score)
            email_type = "bad_website"
        else:
            print(f"  [skip] {company} — website scored {score}/100, not bad enough")
            continue

        success = send_email(email, subject, body, dry_run=dry_run)

        results.append({
            "company": company,
            "email": email,
            "contact_name": contact_name or "",
            "email_type": email_type,
            "subject": subject,
            "sent": success,
            "timestamp": datetime.now().isoformat(),
        })

        # Rate limit between sends
        if not dry_run and i < len(leads) - 1:
            print(f"    Waiting {delay_seconds}s before next email...")
            time.sleep(delay_seconds)

    return results


def log_results(results: list[dict], filename: str = "email_log.csv"):
    """Save send results to CSV for tracking."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    fieldnames = ["timestamp", "company", "email", "contact_name", "email_type", "subject", "sent"]
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

    print(f"\n[*] Email log saved to {filepath}")
