#!/usr/bin/env python3
"""
Eval harness for the Incident Postmortem Drafting Agent — runs the real
draft_postmortem() against synthetic incident threads and grades grounding
discipline via an LLM judge.

Usage:
  python eval/run_eval.py
  python eval/run_eval.py --save
  python eval/run_eval.py --compare eval/results/run_<timestamp>.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table

load_dotenv(Path(__file__).parent.parent / ".env")

from config import load_config
from drafter import draft_postmortem
from fixtures import FIXTURES
from grader import grade_postmortem

console = Console()
RESULTS_DIR = Path(__file__).parent / "results"


def run(model: str, judge_model: str, api_key: str) -> dict:
    fixture_results = []
    for fx in FIXTURES:
        console.print(f"  [dim]running[/] {fx['id']} ...", end="\r")
        report = draft_postmortem(fx["thread"], fx.get("jira", ""), model, api_key)
        grade = grade_postmortem(fx, report, api_key=api_key, judge_model=judge_model)
        fixture_results.append({"id": fx["id"], "notes": fx.get("notes", ""), "report": report, "grade": grade})
        console.print(f"  [{'green' if grade['verdict'] == 'pass' else 'red'}]{grade['verdict'].upper():4}[/]  {fx['id']}")

    passed = sum(1 for r in fixture_results if r["grade"]["verdict"] == "pass")
    total_hallucinations = sum(len(r["grade"]["hallucinations"]) for r in fixture_results)

    return {
        "model": model,
        "judge_model": judge_model,
        "fixture_results": fixture_results,
        "summary_stats": {
            "pass_rate": passed / len(fixture_results),
            "fixtures_passed": passed,
            "fixtures_total": len(fixture_results),
            "hallucinations": total_hallucinations,
        },
    }


def print_report(report: dict):
    stats = report["summary_stats"]
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold dim")
    table.add_column("Fixture")
    table.add_column("Verdict", justify="center")
    table.add_column("Hallucinations", justify="right")
    for r in report["fixture_results"]:
        g = r["grade"]
        style = "green" if g["verdict"] == "pass" else "bold red"
        table.add_row(r["id"], f"[{style}]{g['verdict']}[/]", str(len(g["hallucinations"])))
    console.print(table)
    console.print(f"\n[bold]Pass rate:[/] {stats['fixtures_passed']}/{stats['fixtures_total']}"
                  f"  ·  [bold]Hallucinations:[/] {stats['hallucinations']}")

    for r in report["fixture_results"]:
        g = r["grade"]
        if g["verdict"] == "fail":
            console.print(f"\n[bold red]✗ {r['id']}[/] — {g['reasoning']}")
            for h in g["hallucinations"]:
                console.print(f"    [red]hallucinated:[/] {h['claim']} — {h['why_unsupported']}")
            for f in g["matched_expected"]:
                if not f["found"]:
                    console.print(f"    [yellow]missing:[/] {f['fact']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--judge-model", default="claude-sonnet-5")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--compare")
    parser.add_argument("--threshold", type=float, default=1.0)
    args = parser.parse_args()

    cfg = load_config()
    if not cfg["ANTHROPIC_API_KEY"]:
        console.print("[red]Missing ANTHROPIC_API_KEY[/]")
        sys.exit(1)

    console.print(f"[bold cyan]Running {len(FIXTURES)} fixtures against {args.model}[/]\n")
    report = run(args.model, args.judge_model, cfg["ANTHROPIC_API_KEY"])
    print_report(report)

    if args.compare:
        prior = json.loads(Path(args.compare).read_text())
        prior_by_id = {r["id"]: r["grade"]["verdict"] for r in prior["fixture_results"]}
        console.print("\n[bold]Diff vs. prior run:[/]")
        for r in report["fixture_results"]:
            prev = prior_by_id.get(r["id"])
            now = r["grade"]["verdict"]
            if prev and prev != now:
                console.print(f"  {r['id']}: {prev} -> {now}")

    if args.save:
        RESULTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        out_path = RESULTS_DIR / f"run_{ts}.json"
        out_path.write_text(json.dumps(report, indent=2))
        console.print(f"\n[green]✓[/] Saved to {out_path}")

    pass_rate = report["summary_stats"]["pass_rate"]
    if pass_rate < args.threshold:
        console.print(f"\n[bold red]FAIL[/] — pass rate {pass_rate:.0%} below threshold {args.threshold:.0%}")
        sys.exit(1)
    console.print(f"\n[bold green]PASS[/]")


if __name__ == "__main__":
    main()
