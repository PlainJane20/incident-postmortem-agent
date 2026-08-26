"""
Fetches a single Jira issue's key fields for postmortem context.

Uses GET /rest/api/3/issue/{key} directly — verified live against the real
PGMAUTO project before writing this (the search endpoint used elsewhere in
this portfolio was already found to be deprecated once; not assuming this
one is current without checking).
"""

import requests
from requests.auth import HTTPBasicAuth


def fetch_issue(cfg: dict, issue_key: str) -> dict:
    auth = HTTPBasicAuth(cfg["JIRA_EMAIL"], cfg["JIRA_API_TOKEN"])
    resp = requests.get(
        f"{cfg['JIRA_URL']}/rest/api/3/issue/{issue_key}",
        auth=auth,
        headers={"Accept": "application/json"},
        params={"fields": "summary,status,issuetype,priority,updated"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    f = data["fields"]
    return {
        "key": data["key"],
        "summary": f.get("summary", ""),
        "status": f["status"]["name"],
        "type": f["issuetype"]["name"],
        "priority": (f.get("priority") or {}).get("name", "Unset"),
        "updated": f.get("updated"),
    }
