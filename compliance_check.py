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
 
# ── Helper ─────────────────────────────────────────────────
def get_page(path):
    r = session.get(f"{BASE}/dk/da/user-area/users/{USER_ID}/{path}")
    return BeautifulSoup(r.text, "html.parser")
 
# ── Check 1: Chat enabled (Settings) ──────────────────────
try:
    doc = get_page("settings/")
    html = doc.body.get_text(" ", strip=True).lower()
    raw  = str(doc).lower()
    # Find checkbox near "show chat option"
    idx = raw.find("show chat option")
    snippet = raw[max(0, idx-300):idx+300] if idx != -1 else ""
    # Look for checked input before the label
    checked = False
    for inp in doc.find_all("input", {"type": "checkbox"}):
        label = inp.find_next("label") or inp.find_previous("label")
        label_text = label.get_text(strip=True).lower() if label else ""
        if "show chat option" in label_text or "show chat" in label_text:
            checked = inp.get("checked") is not None or "checked" in str(inp)
            break
    # Fallback: check raw snippet
    if not checked and idx != -1:
        checked = 'checked' in snippet
 
    results["chat_enabled"] = {
        "status": "pass" if checked else "fail",
        "detail": "Show chat option er aktiveret" if checked else "Show chat option er ikke aktiveret"
    }
except Exception as e:
    results["chat_enabled"] = {"status": "warn", "detail": str(e)}
 
# ── Check 2: User status (Overview) ───────────────────────
try:
    doc = get_page("overview/")
    status_label = doc.find(string=lambda t: t and "status" in t.lower())
    status_val = ""
    if status_label:
        parent = status_label.find_parent()
        if parent:
            nxt = parent.find_next_sibling()
            status_val = nxt.get_text(strip=True) if nxt else parent.get_text(strip=True)
    active = "active" in status_val.lower()
    results["user_active"] = {
        "status": "pass" if active else "fail",
        "detail": f"Status: {status_val}" if status_val else "Status ikke fundet"
    }
except Exception as e:
    results["user_active"] = {"status": "warn", "detail": str(e)}
 
# ── Output JSON ────────────────────────────────────────────
print(json.dumps(results))
