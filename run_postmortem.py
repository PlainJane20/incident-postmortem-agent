#!/usr/bin/env python3
"""
Incident Postmortem Drafting Agent

Usage:
  python run_postmortem.py --channel got-a-sec --thread-ts 1787693769.284229
  python run_postmortem.py --channel got-a-sec --thread-ts <ts> --jira PGMAUTO-4
  python run_postmortem.py --channel got-a-sec --thread-ts <ts> --out postmortem.md
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

load_dotenv(Path(__file__).parent / ".env")

from config import load_config
from slack_thread import fetch_thread, format_thread_for_prompt
from jira_issue import fetch_issue
from drafter import draft_postmortem

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Incident Postmortem Drafting Agent")
    parser.add_argument("--channel", required=True)
    parser.add_argument("--thread-ts", required=True)
    parser.add_argument("--jira", help="Linked Jira ticket key, e.g. PGMAUTO-4")
    parser.add_argument("--out")
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--daily-budget", type=float, default=None)
    args = parser.parse_args()

    cfg = load_config()
    if not cfg["SLACK_USER_TOKEN"] or not cfg["ANTHROPIC_API_KEY"]:
        console.print("[red]Missing SLACK_USER_TOKEN or ANTHROPIC_API_KEY[/]")
        sys.exit(1)

    console.print(f"[bold cyan]Fetching thread from #{args.channel}...[/]")
    messages = fetch_thread(cfg["SLACK_USER_TOKEN"], args.channel, args.thread_ts)
    console.print(f"  {len(messages)} messages in thread")
    thread_text = format_thread_for_prompt(messages)

    jira_context = ""
    if args.jira:
        if not cfg["JIRA_URL"]:
            console.print("[yellow]--jira given but no Jira credentials configured — skipping.[/]")
        else:
            console.print(f"[bold cyan]Fetching {args.jira}...[/]")
            issue = fetch_issue(cfg, args.jira)
            jira_context = f"{issue['key']} ({issue['type']}, {issue['status']}, priority {issue['priority']}): {issue['summary']}"

    console.print("[bold cyan]Drafting postmortem...[/]")
    report = draft_postmortem(thread_text, jira_context, args.model, cfg["ANTHROPIC_API_KEY"], args.daily_budget)

    console.print()
    console.print(Markdown(report))

    if args.out:
        Path(args.out).write_text(report)
        console.print(f"\n[green]✓[/] Saved to {args.out}")


if __name__ == "__main__":
    main()
