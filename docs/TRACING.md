# Tracing (optional)

The postmortem agent can emit [OpenTelemetry](https://opentelemetry.io/) spans for
the draft call and for the eval grader. It is **off by default and changes no
behaviour**: with `opentelemetry-api` absent, or present with no SDK configured,
every span is a no-op. The API is imported lazily (`tracing.py`), so the base
install does not need it.

## What is traced

```
postmortem.draft              one per draft_postmortem() call
postmortem.grade              one per grade_postmortem() call (eval grader)
  postmortem.grade.attempt    one per judge call (1, or 2 after a retry on an empty verdict)
```

| Span | Attribute | Values |
|---|---|---|
| `draft` | `model` | model name |
| `draft` | `input_chars` | length in characters of the prompt payload (thread + Jira) |
| `draft` | `jira_included` | bool |
| `draft` | `section_count` | number of `## ` headings in the draft |
| `draft` | `output_chars` | length of the draft in characters |
| `draft` | `duration_ms` | wall time of the model call |
| `draft` | `success` | true / false |
| `grade` | `fixture_id`, `judge_model` | eval fixture id, judge model name |
| `grade` | `attempts`, `retried` | 1 or 2, bool |
| `grade` | `defaulted_to_fail` | true only if both attempts returned no verdict |
| `grade` | `verdict`, `hallucination_count` | `pass`/`fail`, int |
| `grade.attempt` | `attempt`, `verdict` | 1-based attempt number, `pass`/`fail`/`empty` |

Any failing span is marked `ERROR` with `error.type` set to the exception class name.
Span duration is also available from the span itself.

`draft_postmortem` has no grounding check of its own: grounding is judged by the eval
grader, so its outcome appears on the `grade` span (`verdict`, `hallucination_count`),
not on `draft`.

## What is deliberately NOT recorded

- Slack thread text, Jira ticket content, the draft postmortem
- Prompts, the grader rubric, grader reasoning, hallucination claims
- API keys or any config values
- Exception messages (type name only; they can echo thread content)

String attributes are also truncated to 120 characters. `tests/test_tracing.py::test_no_sensitive_strings_in_any_span`
runs the draft and grader (including a failure) on sample strings that look like
thread text, Jira content, a draft and a key, and asserts none appear in any span
name, attribute, status or event.

## Enabling

```bash
pip install opentelemetry-api opentelemetry-sdk   # SDK is what actually records
```

Set a global tracer provider before calling the agent. Console exporter:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

from drafter import draft_postmortem   # spans are emitted from here on
```

OTLP (needs `pip install opentelemetry-exporter-otlp`):

```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")))
```

`run_postmortem.py` and `eval/run_eval.py` do not configure a provider themselves.
Wrap them with `opentelemetry-instrument` and the standard `OTEL_*` environment
variables, or add the provider setup above. (Not verified, see below.)

## Limits, honestly

- Verified only with an in-memory exporter and stub clients (no live model calls).
  Not tested against a real collector, an OTLP endpoint or `opentelemetry-instrument`.
- Token usage and cost are not recorded.
- The drafter does not yet trace Slack or Jira fetching.
- Spans are per-process.
