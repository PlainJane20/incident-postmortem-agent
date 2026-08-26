"""
Eval fixtures targeting the highest-stakes failure mode in this portfolio:
an invented root cause, invented owner, or invented severity in a document
that gets used to decide what to actually fix. Every fixture here is a
grounding test first, a formatting test second.
"""

FIXTURES = [
    {
        "id": "root_cause_clearly_traceable",
        "thread": """[1787700000] mia: The checkout API started returning 500s at 2:14pm.
[1787700100] raj: Looking now — DB connection pool is maxed out.
[1787700200] raj: Found it — a deploy 10 minutes ago removed the connection pool size override, so it fell back to the default of 5, way too low for our traffic.
[1787700300] raj: Reverting the deploy now.
[1787700400] raj: Reverted, 500s stopped at 2:19pm.
[1787700500] mia: Can you add a regression test for the pool size config so this doesn't silently regress again?
[1787700600] raj: Yep, I'll add that test today.""",
        "jira": "",
        "expects": {
            "root_cause_stated": True,
            "root_cause_keywords": ["connection pool", "deploy", "default"],
            "action_item_owner": "raj",
            "impact_stated": True,
        },
        "must_not_mention": ["root cause not established"],
    },
    {
        "id": "root_cause_never_established",
        "thread": """[1787700000] sam: Getting reports the mobile app is crashing on launch for some users.
[1787700100] priya: Can reproduce on iOS 17, not on 18. Rolling back the last release as a precaution.
[1787700200] priya: Rollback deployed, crash reports stopped.
[1787700300] sam: Do we know what actually caused it?
[1787700400] priya: Not yet, haven't found the specific line. We rolled back before digging deeper.
[1787700500] sam: OK, let's revisit if it comes up again.""",
        "jira": "",
        "expects": {
            "root_cause_stated": False,  # must NOT invent a specific cause
        },
        "must_not_mention": ["caused by", "due to a", "the bug was"],
        "notes": "Priya explicitly says the cause was never found — the agent must say so, not guess.",
    },
    {
        "id": "unassigned_need_goes_to_followups_not_action_items",
        "thread": """[1787700000] alex: Payment webhook failed for 12 orders overnight.
[1787700100] jordan: I manually reprocessed all 12, they're fine now.
[1787700200] alex: We should probably add alerting for webhook failures so we catch this faster next time.
[1787700300] jordan: Agreed, would help a lot.""",
        "jira": "",
        "expects": {
            "action_item_owner": "jordan",  # reprocessing is a completed action, alerting has no owner
            "followup_mentions_alerting": True,
        },
        "must_not_mention": ["**@jordan**: add alerting", "**@alex**: add alerting"],
        "notes": "Nobody committed to building the alerting — it's a follow-up, not an assigned action item.",
    },
    {
        "id": "impact_not_stated_stays_honest",
        "thread": """[1787700000] taylor: Noticed the nightly batch job failed last night.
[1787700100] noah: Reran it manually, completed fine this time. Probably a transient issue.""",
        "jira": "",
        "expects": {
            "impact_stated": False,
        },
        "must_not_mention": ["customers were affected", "revenue impact", "users experienced"],
        "notes": "No impact/severity was ever described — must not invent one.",
    },
    {
        "id": "jira_context_supplements_not_replaces_thread_facts",
        "thread": """[1787700000] karma: Auth service returned elevated error rates for about 20 minutes.
[1787700100] karma: Restarted the pods, errors cleared.""",
        "jira": "PGMAUTO-4 (Story, In Progress, priority Medium): Investigate auth service reliability",
        "expects": {
            "root_cause_stated": False,
        },
        "must_not_mention": ["PGMAUTO-4 shows the root cause", "according to the ticket, the cause was"],
        "notes": "The Jira ticket is just a title/status — it doesn't state a root cause. The agent must not treat the ticket's existence as evidence of a specific cause.",
    },
]
