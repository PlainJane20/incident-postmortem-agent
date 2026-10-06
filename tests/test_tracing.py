"""Tracing tests: in-memory exporter, stub clients, no network, no API keys."""

import builtins
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: E402
    InMemorySpanExporter,
)

import drafter  # noqa: E402
import tracing  # noqa: E402
from grader import grade_postmortem  # noqa: E402

SECRET_THREAD = "SECRET-THREAD alice pushed the bad config at 02:14, password=hunter2"
SECRET_JIRA = "SECRET-JIRA PAY-123 customer Acme Corp lost $50k"
SECRET_DRAFT = "SECRET-DRAFT root cause was Bob's typo"
SECRET_KEY = "sk-ant-api03-SECRETKEY"
DRAFT = f"# Postmortem\n\n## Summary\n{SECRET_DRAFT}\n\n## Timeline\n- x\n\n## Impact\nnone\n"
GOOD = {"matched_expected": [], "hallucinations": [], "verdict": "pass", "reasoning": SECRET_DRAFT}
FIXTURE = {"id": "fx-1", "thread": SECRET_THREAD, "jira": SECRET_JIRA, "expects": {"x": SECRET_DRAFT}}


@pytest.fixture
def spans():
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    tracing.configure(provider)
    yield exp
    tracing.configure(None)


def by_name(exp, name):
    return [s for s in exp.get_finished_spans() if s.name == f"postmortem.{name}"]


class DraftClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = self

    def create(self, **kw):
        if self.fail:
            raise RuntimeError(f"upstream said: {SECRET_THREAD}")
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=DRAFT)])


def tool_resp(payload):
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="record_grade", input=payload)])


class GradeClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        return tool_resp(self.payloads.pop(0))


@pytest.fixture
def stub_draft(monkeypatch):
    monkeypatch.setattr(drafter, "_make_client", lambda *a, **k: DraftClient())


def test_draft_span_attributes(spans, stub_draft):
    out = drafter.draft_postmortem(SECRET_THREAD, SECRET_JIRA, "claude-test-model", SECRET_KEY)
    assert out == DRAFT
    [s] = by_name(spans, "draft")
    a = s.attributes
    assert a["model"] == "claude-test-model"
    assert a["input_chars"] == len(f"SLACK THREAD:\n{SECRET_THREAD}\n\nLINKED JIRA TICKET:\n{SECRET_JIRA}\n")
    assert a["jira_included"] is True
    assert a["section_count"] == 3
    assert a["success"] is True
    assert a["duration_ms"] >= 0
    assert a["output_chars"] == len(DRAFT)


def test_draft_failure_recorded_without_message(spans, monkeypatch):
    monkeypatch.setattr(drafter, "_make_client", lambda *a, **k: DraftClient(fail=True))
    with pytest.raises(RuntimeError):
        drafter.draft_postmortem(SECRET_THREAD, "", "m", SECRET_KEY)
    [s] = by_name(spans, "draft")
    assert s.attributes["success"] is False
    assert s.attributes["jira_included"] is False
    assert s.attributes["error.type"] == "RuntimeError"
    assert s.status.status_code.name == "ERROR"
    assert not s.events
    assert "SECRET" not in json.dumps(dict(s.attributes)) + str(s.status.description)


def test_grade_no_retry(spans):
    c = GradeClient([GOOD])
    assert grade_postmortem(FIXTURE, "r", api_key="x", client=c)["verdict"] == "pass"
    [root] = by_name(spans, "grade")
    [att] = by_name(spans, "grade.attempt")
    assert att.parent.span_id == root.context.span_id
    assert att.attributes["attempt"] == 1 and att.attributes["verdict"] == "pass"
    assert root.attributes["attempts"] == 1 and root.attributes["retried"] is False
    assert root.attributes["verdict"] == "pass"
    assert root.attributes["fixture_id"] == "fx-1"


def test_grade_retry_on_empty_verdict(spans):
    c = GradeClient([{}, GOOD])
    assert grade_postmortem(FIXTURE, "r", api_key="x", client=c)["verdict"] == "pass"
    atts = sorted(by_name(spans, "grade.attempt"), key=lambda s: s.attributes["attempt"])
    assert [(s.attributes["attempt"], s.attributes["verdict"]) for s in atts] == [(1, "empty"), (2, "pass")]
    [root] = by_name(spans, "grade")
    assert root.attributes["retried"] is True and root.attributes["attempts"] == 2


def test_grade_two_empty_defaults_to_fail(spans):
    c = GradeClient([{}, {}])
    assert grade_postmortem(FIXTURE, "r", api_key="x", client=c)["verdict"] == "fail"
    [root] = by_name(spans, "grade")
    assert root.attributes["defaulted_to_fail"] is True
    assert root.attributes["verdict"] == "fail"
    assert [s.attributes["verdict"] for s in by_name(spans, "grade.attempt")] == ["empty", "empty"]


def test_no_sensitive_strings_in_any_span(spans, monkeypatch):
    monkeypatch.setattr(drafter, "_make_client", lambda *a, **k: DraftClient())
    drafter.draft_postmortem(SECRET_THREAD, SECRET_JIRA, "m", SECRET_KEY)
    monkeypatch.setattr(drafter, "_make_client", lambda *a, **k: DraftClient(fail=True))
    with pytest.raises(RuntimeError):
        drafter.draft_postmortem(SECRET_THREAD, SECRET_JIRA, "m", SECRET_KEY)
    grade_postmortem(FIXTURE, DRAFT, api_key=SECRET_KEY, client=GradeClient([{}, GOOD]))
    finished = spans.get_finished_spans()
    assert len(finished) == 5
    blob = json.dumps(
        [[s.name, dict(s.attributes), s.status.description,
          [(e.name, dict(e.attributes)) for e in s.events]] for s in finished],
        default=str,
    )
    for secret in (SECRET_THREAD, SECRET_JIRA, SECRET_DRAFT, SECRET_KEY, "SECRET", "hunter2", "Acme"):
        assert secret not in blob


def test_noop_by_default():
    tracing.configure(None)
    with tracing.span("x", a=1) as s:
        s.set_attribute("k", "v")
        assert not s.is_recording()


def test_noop_when_otel_api_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "opentelemetry" or name.startswith("opentelemetry."):
            raise ImportError("simulated: opentelemetry not installed")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(drafter, "_make_client", lambda *a, **k: DraftClient())
    assert drafter.draft_postmortem("t", "", "m", "k") == DRAFT
    c = GradeClient([{}, GOOD])
    assert grade_postmortem(FIXTURE, "r", api_key="x", client=c)["verdict"] == "pass"
    assert c.calls == 2


def test_importing_modules_does_not_import_opentelemetry():
    code = (
        "import sys; sys.path[:0] = [%r, %r];"
        "import drafter, tracing; from grader import grade_postmortem;"
        "assert not any(m.startswith('opentelemetry') for m in sys.modules), 'eager import'"
    ) % (str(ROOT), str(ROOT / "eval"))
    subprocess.run([sys.executable, "-c", code], check=True)


def test_tracing_does_not_change_outputs(monkeypatch):
    def run(enabled):
        monkeypatch.setattr(drafter, "_make_client", lambda *a, **k: DraftClient())
        if enabled:
            p = TracerProvider()
            p.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
            tracing.configure(p)
        else:
            tracing.configure(None)
        try:
            d = drafter.draft_postmortem("t", "j", "m", "k")
            g = grade_postmortem(FIXTURE, d, api_key="x", client=GradeClient([{}, GOOD]))
        finally:
            tracing.configure(None)
        return d, g

    assert run(False) == run(True)
