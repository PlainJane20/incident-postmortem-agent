"""
LLM-as-judge grader — adapted from slack-daily-agent's eval/grader.py, with
the type-safety lesson learned there (and re-learned in exec-status-rollup
and spec-review-agent) built in from the start this time: never trust a
forced-schema field to be the type it's supposed to be just because the
schema said so.
"""

import anthropic

GRADE_TOOL = {
    "name": "record_grade",
    "description": "Record the grading result for one postmortem eval fixture.",
    "input_schema": {
        "type": "object",
        "properties": {
            "matched_expected": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "fact": {"type": "string"},
                        "found": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["fact", "found", "evidence"],
                },
            },
            "hallucinations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "why_unsupported": {"type": "string"},
                    },
                    "required": ["claim", "why_unsupported"],
                },
            },
            "verdict": {"type": "string", "enum": ["pass", "fail"]},
            "reasoning": {"type": "string"},
        },
        "required": ["matched_expected", "hallucinations", "verdict", "reasoning"],
    },
}

GRADER_SYSTEM = """You are a strict eval grader for an incident postmortem
drafting agent. The highest-priority failure mode is an INVENTED root
cause, owner, or impact severity not supported by the source thread — this
is worse than an honest "not established," because it sends the reader
fixing the wrong thing with false confidence.

You'll get: the source Slack thread, an optional linked Jira ticket, a
rubric of expected facts, a list of things that must NOT appear, and the
agent's postmortem to grade.

Rules:
- "found: true" only if the fact is substantively and correctly present.
- Flag ANY claim in the postmortem not directly supported by the thread as
  a hallucination — a specific root cause, owner, or severity that the
  thread doesn't actually establish, even if it sounds plausible.
- Flag anything from must_not_mention that appears, even in a softened form.
- verdict is "pass" only if all expected facts are found AND there are
  zero hallucinations. Otherwise "fail". Be strict — plausible-sounding
  inference is still a hallucination if the thread doesn't state it.
"""


def grade_postmortem(fixture: dict, report: str, api_key: str, judge_model: str = "claude-sonnet-5") -> dict:
    """
    api_key is passed explicitly, not read from os.environ — this repo's
    config.py resolves credentials via a sibling-repo fallback chain into a
    plain dict that's never exported back into the process environment.
    Reading os.environ here directly reproduced the exact bug already found
    and fixed in exec-status-rollup's narrator.py: copying a pattern from
    slack-daily-agent (where os.environ IS populated directly, no fallback
    chain) without checking whether the same assumption held here.
    """
    client = anthropic.Anthropic(api_key=api_key)

    expects = fixture["expects"]
    rubric_lines = []
    for key, value in expects.items():
        rubric_lines.append(f"- {key}: {value}")
    rubric = "\n".join(rubric_lines)
    forbidden = "\n".join(f"- {f}" for f in fixture.get("must_not_mention", [])) or "(none specified)"

    user_msg = f"""SOURCE SLACK THREAD:
{fixture['thread']}

LINKED JIRA TICKET:
{fixture.get('jira') or '(none)'}

EXPECTED FACTS (rubric):
{rubric}

MUST NOT MENTION:
{forbidden}

AGENT'S POSTMORTEM TO GRADE:
{report}
"""

    resp = client.messages.create(
        model=judge_model,
        max_tokens=2048,
        system=GRADER_SYSTEM,
        tools=[GRADE_TOOL],
        tool_choice={"type": "tool", "name": "record_grade"},
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_grade":
            return _normalize(block.input)
    raise RuntimeError("Grader did not return a tool_use block")


def _normalize(grade: dict) -> dict:
    """Defensive coercion — see module docstring. A required field is not
    guaranteed to be present, or to be the type the schema promised."""
    def clean_list(items, required_key):
        if not isinstance(items, list):
            return []
        return [it for it in items if isinstance(it, dict) and required_key in it]

    grade = dict(grade)
    grade["matched_expected"] = clean_list(grade.get("matched_expected"), "fact")
    grade["hallucinations"] = clean_list(grade.get("hallucinations"), "claim")
    grade.setdefault("verdict", "fail")
    grade.setdefault("reasoning", "(missing from grader output)")
    return grade
