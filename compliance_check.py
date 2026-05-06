import os
import json
import requests
from bs4 import BeautifulSoup

EMAIL    = os.environ["MOVER_EMAIL"]
PASSWORD = os.environ["MOVER_PASSWORD"]
USER_ID  = os.environ["USER_ID"]

BASE = "https://admin.mover.dk"

session = requests.Session()

# ── Login ──────────────────────────────────────────────────
login_page = session.get(f"{BASE}/dk/da/user-area/login/")
soup = BeautifulSoup(login_page.text, "html.parser")
csrf = soup.find("input", {"name": "__RequestVerificationToken"})
csrf_val = csrf["value"] if csrf else ""

session.post(f"{BASE}/dk/da/user-area/login/", data={
    "Email": EMAIL,
    "Password": PASSWORD,
    "__RequestVerificationToken": csrf_val
})

results = {}

def get_page(path):
    r = session.get(f"{BASE}/dk/da/user-area/users/{USER_ID}/{path}")
    return BeautifulSoup(r.text, "html.parser")

# ── Check 1: User active (Overview) ───────────────────────
try:
    doc = get_page("overview/")
    raw = str(doc)
    
    # Find all text nodes and look for Active/Inactive near Status
    status_val = ""
    all_text = doc.get_text(" ", strip=True)
    
    # Look for pattern: "Status Active" or "Status Inactive" in text
    import re
    match = re.search(r'Status\s+(Active|Inactive|Suspended)', all_text, re.IGNORECASE)
    if match:
        status_val = match.group(1)
    
    # Fallback: find label "Status" and get next sibling text
    if not status_val:
        for tag in doc.find_all(True):
            if tag.string and tag.string.strip().lower() == "status":
                nxt = tag.find_next_sibling()
                if not nxt:
                    nxt = tag.parent.find_next_sibling()
                if nxt:
                    status_val = nxt.get_text(strip=True)
                    break

    active = "active" in status_val.lower() if status_val else False
    results["user_active"] = {
        "status": "pass" if active else "fail",
        "detail": f"Status: {status_val}" if status_val else "Status not found in HTML"
    }
except Exception as e:
    results["user_active"] = {"status": "warn", "detail": f"Error: {str(e)}"}

# ── Check 2: Chat enabled (Settings) ──────────────────────
try:
    doc = get_page("settings/")
    
    checked = False
    # Find all checkboxes and check which ones are checked
    for inp in doc.find_all("input", {"type": "checkbox"}):
        # Get surrounding text
        parent = inp.parent
        surrounding = parent.get_text(" ", strip=True).lower() if parent else ""
        if "show chat" in surrounding or "chat option" in surrounding:
            checked = inp.has_attr("checked")
            break
    
    # Fallback: search raw HTML for checked checkbox near "chat"
    if not checked:
        raw = str(doc)
        import re
        # Find all checkbox inputs that are checked
        checked_boxes = re.findall(r'<input[^>]+checked[^>]*type=["\']checkbox["\'][^>]*>|<input[^>]+type=["\']checkbox["\'][^>]*checked[^>]*>', raw, re.IGNORECASE)
        for box in checked_boxes:
            # Get surrounding context
            idx = raw.find(box)
            context = raw[max(0,idx-200):idx+200].lower()
            if "chat" in context:
                checked = True
                break

    results["chat_enabled"] = {
        "status": "pass" if checked else "fail",
        "detail": "Show chat option is enabled" if checked else "Show chat option is not enabled"
    }
except Exception as e:
    results["chat_enabled"] = {"status": "warn", "detail": f"Error: {str(e)}"}

# ── Output JSON ────────────────────────────────────────────
print(json.dumps(results))
