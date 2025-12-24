# app/refiner.py
import re
from datetime import datetime
from app.config import (
    IGNORE_DOMAINS, ACCEPTED_ROLES, PREFIXES_TO_STRIP,
    INDIAN_CITIES, FOREIGN_LOCATIONS
)


def refine_job_batch(raw_jobs: list) -> list:
    """
    Stage 2: Transforms raw blocks into Final Master Tracker rows.
    """
    refined = []

    for job in raw_jobs:
        if job.get("status") != "Selected":
            continue

        raw_text = job.get("Raw_Text", "")

        # 1. Email Extraction & Filtering
        valid_email = extract_valid_email(raw_text)

        # 2. Company Extraction (Priority Logic)
        company = extract_company(raw_text, valid_email)

        # 3. Role Normalization
        role = extract_role(raw_text)

        # 4. Location & Mode
        location = extract_location(raw_text)
        mode = extract_mode(raw_text, location)

        entry = {
            "S.No": len(refined) + 1,
            "Company": company,
            "Role": role,
            "Exp": f"{job.get('Exp_Min')} - {job.get('Exp_Max', '?')} yrs",
            "Location": location,
            "Mode": mode,
            "Email": valid_email,
            "Source_PDF": job.get("Source_PDF"),
            "Notes": generate_tech_notes(raw_text),
            "Domain": extract_domain(raw_text),
            "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        refined.append(entry)

    return refined

# --- HELPERS ---


def extract_valid_email(text: str) -> str:
    # Regex for all emails
    emails = re.findall(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)

    # Filter out generic/aggregator domains
    valid_emails = []
    for email in emails:
        domain = email.split('@')[1].lower()
        if domain not in IGNORE_DOMAINS:
            valid_emails.append(email)

    if valid_emails:
        return valid_emails[0]  # Return first valid company email

    return "Apply via Company Portal"


def extract_company(text: str, email: str) -> str:
    # Priority 1: From Valid Email Domain
    if email != "Apply via Company Portal":
        domain = email.split('@')[1]
        name = domain.split('.')[0]
        # Cleanup (e.g., 'careers' -> invalid, but usually domain is company name)
        if len(name) > 2:
            return name.title()

    # Priority 2: Regex Patterns in Text
    patterns = [
        r"(?:Hiring for|Client[:\-])\s*([A-Z][a-z0-9]+(?:\s[A-Z][a-z0-9]+)*)",
        r"([A-Z][a-z0-9]+)\s+is hiring"
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()

    # Priority 3: Fallback
    return "Confidential / Client via Consultancy"


def extract_role(text: str) -> str:
    text_lower = text.lower()

    # Find longest matching role
    best_match = ""
    for role in ACCEPTED_ROLES:
        if role in text_lower:
            if len(role) > len(best_match):
                best_match = role

    if not best_match:
        return "QA / SDET"

    # Strip prefixes from the FOUND role context?
    # Actually, we map the accepted keyword to a Title Case string.
    # But if text says "Senior QA Engineer", best_match is "QA Engineer".
    # The prompt says "Strip prefixes". So if we found "QA Engineer", we just return that.
    # We DO NOT prepend "Senior".

    return best_match.title()


def extract_location(text: str) -> str:
    t = text.lower()
    locs = set()

    # Check Foreign
    for f_loc in FOREIGN_LOCATIONS:
        if f_loc.lower() in t:
            locs.add(f_loc)

    # Check Indian Cities
    for city in INDIAN_CITIES:
        if city.lower() in t:
            locs.add(city)

    if "pan india" in t:
        locs.add("Pan India")
    elif "remote" in t and not locs:
        locs.add("Remote")

    if not locs:
        return "Not Specified"

    return ", ".join(sorted(locs))


def extract_mode(text: str, location_str: str) -> str:
    t = text.lower()
    if "remote" in t and "hybrid" not in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if "wfo" in t or "work from office" in t or "on-site" in t:
        return "Work From Office"

    # Heuristic: If location is "Remote", mode is Remote
    if "Remote" in location_str:
        return "Remote"

    return "Full-time"


def extract_domain(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["bank", "fintech", "payment", "financial"]):
        return "FinTech"
    if any(k in t for k in ["health", "medical", "pharma"]):
        return "Healthcare"
    if any(k in t for k in ["ecommerce", "retail", "shopping"]):
        return "E-commerce"
    if "saas" in t:
        return "SaaS"
    return "IT Services"


def generate_tech_notes(text: str) -> str:
    t = text.lower()
    keywords = ["java", "python", "selenium",
                "manual", "api", "sql", "appium", "playwright"]
    found = [k.title() for k in keywords if k in t]
    return " + ".join(found) if found else "QA Role"
