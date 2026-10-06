import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))

from grader import grade_postmortem  # noqa: E402

FIXTURE = {"thread": "t", "jira": "", "expects": {"x": True}}
GOOD = {"matched_expected": [], "hallucinations": [], "verdict": "pass", "reasoning": "ok"}


def resp(payload):
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="record_grade", input=payload)])


class StubClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        return resp(self.payloads.pop(0))


def test_empty_tool_call_is_retried_once_then_passes():
    c = StubClient([{}, GOOD])
    assert grade_postmortem(FIXTURE, "r", api_key="x", client=c)["verdict"] == "pass"
    assert c.calls == 2


def test_good_first_call_is_not_retried():
    c = StubClient([GOOD])
    assert grade_postmortem(FIXTURE, "r", api_key="x", client=c)["verdict"] == "pass"
    assert c.calls == 1


def test_two_empty_calls_still_default_to_fail_after_one_retry():
    c = StubClient([{}, {}])
    g = grade_postmortem(FIXTURE, "r", api_key="x", client=c)
    assert g["verdict"] == "fail" and g["reasoning"] == "(missing from grader output)"
    assert c.calls == 2
