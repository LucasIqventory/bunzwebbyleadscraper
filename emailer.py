"""
Email Sender — Sends personalized cold outreach emails to leads.
Uses SMTP with TLS. Includes rate limiting and logging.
"""

import smtplib
import time
import csv
import os
import random
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_EMAIL, SMTP_PASSWORD,
    YOUR_NAME, YOUR_COMPANY, YOUR_PHONE, YOUR_WEBSITE, OUTPUT_DIR,
    DISABLE_SENDGRID_CLICK_TRACKING, PAST_PROJECT_NAME, PAST_PROJECT_DISPLAY_URL,
    EMAIL_DELAY_MAX_SECONDS, EMAIL_DELAY_MIN_SECONDS, EMAIL_SEND_HISTORY_FILE,
    MAX_EMAILS_PER_DAY, SKIP_PREVIOUSLY_EMAILED,
)


def build_email_no_website(company_name: str, contact_name: str | None) -> tuple[str, str]:
    """Email template for companies with NO website."""
    greeting = f"Hi {contact_name}," if contact_name else f"Hi,"
    subject = f"quick question about {company_name}"

    body = f"""{greeting}

I was looking up {company_name} and noticed I couldn't find a website linked for the business.

I build simple, clean websites for companies that do real-world work and do not need a bunch of marketing fluff. One recent project we worked on is {PAST_PROJECT_NAME} at {PAST_PROJECT_DISPLAY_URL}.

I know this is out of the blue, but if getting a straightforward website up is something you have been meaning to handle, I would be happy to send over a couple ideas for what that could look like for {company_name}.

Worth a quick conversation sometime this week?

Best,
{YOUR_NAME}
{YOUR_COMPANY}
{YOUR_PHONE}
{YOUR_WEBSITE}"""

    return subject, body


def _send_history_path() -> str:
    return os.path.join(OUTPUT_DIR, EMAIL_SEND_HISTORY_FILE)


def load_send_history() -> list[dict]:
    """Load persistent successful-send history used for daily caps and duplicate checks."""
    filepath = _send_history_path()
    if not os.path.exists(filepath):
        return []

    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_send_history(rows: list[dict]) -> None:
    """Append successful live sends to the persistent history file."""
    if not rows:
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = _send_history_path()
    fieldnames = ["timestamp", "company", "email", "email_type", "subject"]
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def sent_today_count(history: list[dict]) -> int:
    today = datetime.now().date().isoformat()
    return sum(1 for row in history if (row.get("timestamp") or "")[:10] == today)


def already_emailed(email: str, history: list[dict]) -> bool:
    email_lower = (email or "").strip().lower()
    return any((row.get("email") or "").strip().lower() == email_lower for row in history)


def _next_delay_seconds(
    fixed_delay_seconds: int | None,
    min_delay_seconds: int,
    max_delay_seconds: int,
) -> int:
    if fixed_delay_seconds is not None:
        return max(0, fixed_delay_seconds)

    low = max(0, min_delay_seconds)
    high = max(low, max_delay_seconds)
    return random.randint(low, high)


def build_email_bad_website(
    company_name: str,
    contact_name: str | None,
    website_url: str,
    issues: list[str],
    score: int,
) -> tuple[str, str]:
    """Email template for companies with a BAD website."""
    greeting = f"Hi {contact_name}," if contact_name else f"Hi,"
    subject = f"quick note about {company_name}'s website"

    # Build issues list
    issues_text = ""
    if issues:
        issue_bullets = "\n".join(f"- {issue}" for issue in issues[:3])
        issues_text = f"\nA few small things stood out:\n{issue_bullets}\n"

    body = f"""{greeting}

I came across {company_name} and took a quick look at {website_url}. The company looks solid, but the site felt like it might not be doing as much work as it could.
{issues_text}
We build straightforward, modern websites for companies in industrial, construction, and materials-related spaces. One recent project we worked on is {PAST_PROJECT_NAME} at {PAST_PROJECT_DISPLAY_URL}.

Not trying to pitch a huge rebuild out of nowhere. I just thought there may be a few simple changes that would make the site feel more current and easier for customers to use.

Would you be open to me sending over a couple quick thoughts for {company_name}?

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

    if not SMTP_EMAIL or not SMTP_USERNAME or not SMTP_PASSWORD:
        print("    [!] SMTP credentials not configured. Set SMTP_EMAIL, SMTP_USERNAME, and SMTP_PASSWORD in .env")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{YOUR_NAME} <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    if DISABLE_SENDGRID_CLICK_TRACKING and "sendgrid" in SMTP_HOST.lower():
        msg["X-SMTPAPI"] = json.dumps({
            "filters": {
                "clicktrack": {
                    "settings": {
                        "enable": 0,
                        "enable_text": 0,
                    }
                }
            }
        })
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"    [sent] Sent to {to_email}")
        return True
    except Exception as e:
        print(f"    [failed] Failed to send to {to_email}: {e}")
        return False


def send_outreach(
    leads: list[dict],
    dry_run: bool = True,
    delay_seconds: int | None = None,
    max_per_day: int = MAX_EMAILS_PER_DAY,
    min_delay_seconds: int = EMAIL_DELAY_MIN_SECONDS,
    max_delay_seconds: int = EMAIL_DELAY_MAX_SECONDS,
    skip_previously_emailed: bool = SKIP_PREVIOUSLY_EMAILED,
) -> list[dict]:
    """
    Send outreach emails to qualified leads.
    Returns list of send results for logging.
    """
    results = []
    history = load_send_history()
    already_sent_today = sent_today_count(history)
    remaining_today = max(0, max_per_day - already_sent_today) if max_per_day > 0 else len(leads)
    sent_this_run = 0

    if not dry_run:
        print(f"  Daily cap: {max_per_day} emails/day; already sent today: {already_sent_today}; remaining: {remaining_today}")
        if remaining_today <= 0:
            print("  [limit] Daily send cap already reached. No emails will be sent this run.")
            return results

    for i, lead in enumerate(leads):
        email = lead.get("best_email")
        if not email:
            print(f"  [skip] {lead['name']} — no email found")
            continue

        if not dry_run and sent_this_run >= remaining_today:
            print(f"  [limit] Daily send cap reached after {sent_this_run} email(s) this run.")
            break

        if skip_previously_emailed and already_emailed(email, history):
            print(f"  [skip] {lead['name']} — {email} was already emailed before")
            results.append({
                "company": lead["name"],
                "email": email,
                "contact_name": lead.get("best_name") or "",
                "email_type": "",
                "subject": "",
                "sent": False,
                "status": "skipped",
                "reason": "already_emailed",
                "timestamp": datetime.now().isoformat(),
            })
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
        timestamp = datetime.now().isoformat()
        status = "previewed" if dry_run else ("sent" if success else "failed")

        results.append({
            "company": company,
            "email": email,
            "contact_name": contact_name or "",
            "email_type": email_type,
            "subject": subject,
            "sent": success and not dry_run,
            "status": status,
            "reason": "",
            "timestamp": timestamp,
        })

        if success and not dry_run:
            sent_this_run += 1
            history_row = {
                "timestamp": timestamp,
                "company": company,
                "email": email,
                "email_type": email_type,
                "subject": subject,
            }
            append_send_history([history_row])
            history.append(history_row)

        # Rate limit between sends
        if success and not dry_run and sent_this_run < remaining_today and i < len(leads) - 1:
            wait_seconds = _next_delay_seconds(delay_seconds, min_delay_seconds, max_delay_seconds)
            print(f"    Waiting {wait_seconds}s before next email...")
            time.sleep(wait_seconds)

    return results


def log_results(results: list[dict], filename: str = "email_log.csv"):
    """Save send results to CSV for tracking."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    fieldnames = ["timestamp", "company", "email", "contact_name", "email_type", "subject", "sent", "status", "reason"]
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

    print(f"\n[*] Email log saved to {filepath}")
