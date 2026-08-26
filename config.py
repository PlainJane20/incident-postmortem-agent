"""
Credential resolution via sibling-repo .env fallback chain — same pattern
used across this portfolio (exec-status-rollup, spec-review-agent): reuse
already-configured live credentials instead of asking for a fourth copy of
the same secrets.
"""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

HERE = Path(__file__).parent
SLACK_FALLBACK_ENV = HERE.parent / "slack-daily-agent" / ".env"
JIRA_FALLBACK_ENV = HERE.parent / "pm-automation-system" / ".env"


def _fill_from(cfg: dict, keys: list, fallback_path: Path):
    missing = [k for k in keys if not cfg.get(k)]
    if missing and fallback_path.exists():
        fallback = dotenv_values(fallback_path)
        for k in missing:
            if fallback.get(k):
                cfg[k] = fallback[k]


def load_config() -> dict:
    load_dotenv(HERE / ".env")
    cfg = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "SLACK_USER_TOKEN": os.environ.get("SLACK_USER_TOKEN", ""),
        "JIRA_URL": os.environ.get("JIRA_URL", ""),
        "JIRA_EMAIL": os.environ.get("JIRA_EMAIL", ""),
        "JIRA_API_TOKEN": os.environ.get("JIRA_API_TOKEN", ""),
    }
    _fill_from(cfg, ["ANTHROPIC_API_KEY", "SLACK_USER_TOKEN"], SLACK_FALLBACK_ENV)
    _fill_from(cfg, ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"], JIRA_FALLBACK_ENV)
    return cfg
