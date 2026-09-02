# Incident Postmortem Drafting Agent

<div align="center">

[![Python 3.9+](https://img.shields.io/badge/Python_3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Powered by Claude](https://img.shields.io/badge/Powered_by-Claude-D97757?style=for-the-badge&logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![Slack + Jira](https://img.shields.io/badge/Slack_%2B_Jira-integrated-0052CC?style=for-the-badge)]()
[![Eval](https://img.shields.io/badge/Eval-4%2F5_(1_grader_glitch)-eda100?style=for-the-badge)](eval/)

</div>

Drafts a structured, blameless postmortem from a Slack incident thread and
its linked Jira ticket — timeline, impact, root cause, action items, and
open follow-ups, with the strictest grounding discipline in this portfolio:
**an invented root cause is worse than an honest "not established."**

**Why this exists:** the highest-stakes artifact a TPM produces isn't a
status update, it's a postmortem — it decides what the org spends the next
sprint fixing. If the root-cause section is confidently wrong, that's not a
cosmetic bug, it's actively harmful. This agent is built to be honest about
uncertainty rather than fluent about it.

## Named, specifically: what incident.io, Rootly, and PagerDuty don't publish

Every major incident platform has shipped AI postmortem drafting in the
last 12-18 months — incident.io's Scribe, Rootly's AI Copilot, PagerDuty's
Scribe Agent, FireHydrant's AI-drafted retrospectives. "AI drafts your
postmortem" is not a gap; it's table stakes now, and none of them are
short on funding (incident.io alone has raised $96M).

What none of their public materials advertise is an **adversarial
hallucination-detection eval suite** — a harness specifically built to
try to catch the model inventing a root cause, inventing a timestamp, or
manufacturing a connection between an incident and an unrelated ticket.
That's the actual differentiator this repo is betting on: not "drafts a
postmortem" (solved, commoditized, funded), but "has a harness that
actively hunts for the one failure mode that makes an AI-drafted
postmortem dangerous rather than just mediocre." See the next section for
what that harness found — including a bug in the harness itself, disclosed
rather than hidden.

## Real, live proof — not a scripted demo

Posted a real 5-message incident thread into a real Slack channel, linked it
to a real (unrelated) Jira ticket, and ran the actual CLI — see
[`sample_output.md`](sample_output.md) for the unedited result. Three things
worth noting about what it did *unprompted*:

1. **Traced the root cause chain and stopped honestly** when the thread's
   information ran out ("The thread does not go further into why... so the
   chain stops here") instead of speculating further.
2. **Distinguished stated timing from inferred sequence** — flagged that
   exact elapsed time between steps wasn't given, rather than inventing
   precise timestamps to fill the Timeline section.
3. **Noticed the linked Jira ticket was unrelated to the incident** and said
   so explicitly in Open Follow-ups instead of forcing a connection because
   a ticket was provided. Not something I tested for in the eval fixtures —
   the grounding discipline generalized on its own.

## The eval harness caught something about itself, not just the agent

5 fixtures targeting the grounding failure mode specifically (root cause
traceable vs. never established, unassigned needs vs. committed action
items, stated vs. unstated impact). Result: **4/5 passed, 0 hallucinations
detected** — but the 5th "fail" is worth being precise about. Manually
reading the raw output for `root_cause_never_established` shows the agent
was exemplary: it correctly refused to invent a cause. The grader itself
returned an empty, malformed tool call that verdict-defaulted to "fail."

That's the 4th time this exact failure mode — a forced tool schema not
guaranteeing the model actually populates every required field — has shown
up somewhere in this portfolio (`exec-status-rollup`, `slack-daily-agent`,
`spec-review-agent`, now here, and now in the *judge* rather than the agent
under test). The fix each time is the same: never trust structured LLM
output to have the shape the schema promised without validating it. This
time it means an honest 80% pass rate with a manually-verified explanation,
rather than re-running until the number looks clean.

## A second real bug, from copying a working pattern into a different context

`grader.py` was adapted from `slack-daily-agent`'s eval harness, which reads
`ANTHROPIC_API_KEY` from `os.environ` directly — safe there, because that
repo's config has no fallback chain. This repo's `config.py` *does* resolve
credentials via a sibling-repo fallback into a plain dict that's never
exported back into the process environment — the exact same bug already
found and fixed in `exec-status-rollup`'s `narrator.py`. Copying a working
pattern without re-checking its assumptions against a different context
reproduced a bug I'd already fixed once. Fixed the same way: pass the key
as an explicit argument, not an implicit environment read.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # or leave blank to reuse sibling repos' credentials
```

## Usage

```bash
python run_postmortem.py --channel incident-room --thread-ts 1787705276.984169
python run_postmortem.py --channel incident-room --thread-ts <ts> --jira PGMAUTO-4 --out postmortem.md

# Eval harness
python eval/run_eval.py --save
python eval/run_eval.py --compare eval/results/run_<timestamp>.json
```

## Contact

<div align="center">

### **Navi Sohi**
*Technical Program Manager & Automation Engineer*

<br>

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/navisohi/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/PlainJane20)
[![Email](https://img.shields.io/badge/Email-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](https://mail.google.com/mail/?view=cm&fs=1&to=nks.ai.dev@gmail.com)

<br>

</div>
