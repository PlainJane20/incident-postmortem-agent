"""
Drafts a structured postmortem from a Slack incident thread (+ optional
linked Jira ticket). The grounding discipline here matters more than in any
other agent in this portfolio: a postmortem that INVENTS a root cause is
actively worse than one that honestly says the cause is unclear — it sends
the org fixing the wrong thing with false confidence. This system prompt is
the slack-daily-agent hallucination lesson applied to the highest-stakes
artifact in the whole series.
"""

import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent / "agent-control-tower"))
try:
    from governed_client import GovernedClient
    _GOVERNANCE_AVAILABLE = True
except ImportError:
    _GOVERNANCE_AVAILABLE = False

SYSTEM_PROMPT = """You are drafting a blameless incident postmortem from a
Slack thread and, optionally, its linked Jira ticket. Ground every single
claim in the transcript — this document gets used to decide what to fix,
so an invented root cause or an invented owner is worse than an honest gap.

Output format:

# Postmortem — {title}

## Summary
1-2 sentences: what happened, stated plainly.

## Timeline
Bulleted, timestamped, built only from message timestamps and content
actually in the thread. Do not infer timing that isn't stated or timestamped.

## Impact
What was affected, and how badly — only state impact explicitly mentioned
in the thread. If impact isn't described, say "Impact not stated in the
available thread" rather than guessing severity.

## Root Cause
Walk through as many "why" links as the thread actually supports (this may
be one link, or it may be none). If the thread does not establish a root
cause, say exactly that: "Root cause not established from the available
data — needs follow-up investigation." Do not invent a plausible-sounding
cause to fill this section.

## Contributing Factors
Only factors someone in the thread explicitly named. Empty is a valid,
correct answer — write "None mentioned in the thread."

## Action Items
Format: "- [ ] **@person**: task — due if stated". Only include an item if
someone explicitly committed to it or was assigned it with an owner who
accepted. An unresolved need with no committed owner goes in Open
Follow-ups instead, not here.

## Open Follow-ups
Questions or needs raised in the thread with no committed owner or no
resolution yet.

Rules:
- Never invent: a root cause, an owner, a severity, or a timeline detail
  not directly supported by the transcript.
- If the Jira ticket is provided, you may reference its status/summary as
  context, but do not treat it as a substitute for facts the Slack thread
  itself doesn't contain.
"""


def _make_client(api_key: str, daily_budget: float = None):
    if _GOVERNANCE_AVAILABLE:
        return GovernedClient("incident-postmortem-agent", api_key=api_key, daily_budget=daily_budget)
    return anthropic.Anthropic(api_key=api_key)


def draft_postmortem(thread_text: str, jira_context: str, model: str, api_key: str,
                      daily_budget: float = None) -> str:
    client = _make_client(api_key, daily_budget)

    user_content = f"SLACK THREAD:\n{thread_text}\n"
    if jira_context:
        user_content += f"\nLINKED JIRA TICKET:\n{jira_context}\n"

    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text_blocks = [b.text for b in msg.content if b.type == "text"]
    return "\n".join(text_blocks)
