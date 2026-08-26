# Postmortem — Payment Webhook Failures Due to Stripe Signing Key Rotation

## Summary
Payment webhooks failed for 14 orders around 3am UTC after Stripe rotated their signing key, which the team's webhook signature validation did not accept. The orders were manually reprocessed and validation was reverted to accept both key formats.

## Timeline
- **~3am UTC**: Payment webhook failed for 14 orders (Karma).
- (sequence, exact time not stated) Karma manually reprocessed all 14 orders and confirmed success.
- (sequence, exact time not stated) Karma identified that webhook signature validation began rejecting Stripe's new signing key format following a key rotation "last night," and reverted validation to accept both formats.
- (sequence, exact time not stated) A teammate asked for a monitor on webhook rejection rate to catch similar issues faster.
- (sequence, exact time not stated) Karma agreed to set up the monitor "today."

Note: The thread's message timestamps are sequential but closely spaced; no explicit elapsed-time gaps between steps are given beyond "around 3am UTC" and "last night."

## Impact
14 orders had failed payment webhooks. All 14 were manually reprocessed and confirmed successful. No further impact (e.g., customer-facing effects, revenue loss, duration of outage) is stated in the thread.

## Root Cause
- Webhook signature validation rejected Stripe's new signing key format.
- This was caused by Stripe rotating their signing key the night before the incident, and the team's validation logic not yet supporting the new key format.

The thread does not go further into why the validation logic wasn't updated ahead of the rotation (e.g., no advance notice, no monitoring for deprecation warnings, etc.), so the chain stops here.

## Contributing Factors
None mentioned in the thread.

## Action Items
- [ ] **Karma**: Add a monitor for webhook rejection rate to catch similar issues faster — due today.

## Open Follow-ups
- No discussion of whether Stripe's key rotation was announced in advance or whether there's a process to track/react to such rotations proactively — not addressed in the thread.
- The linked Jira ticket (PGMAUTO-4, "Automated Inventory Reconciliation System") does not appear related to this payment webhook incident, so it provides no additional context here.