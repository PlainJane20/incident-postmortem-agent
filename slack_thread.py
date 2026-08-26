"""Fetches a single Slack thread — the root message plus every reply."""

from slack_sdk import WebClient


def fetch_thread(token: str, channel_name: str, thread_ts: str, user_cache: dict = None) -> list:
    client = WebClient(token=token)
    user_cache = user_cache if user_cache is not None else {}

    resp = client.conversations_list(types="public_channel,private_channel", limit=200)
    channel = next((c for c in resp["channels"] if c["name"] == channel_name), None)
    if not channel:
        raise ValueError(f"#{channel_name} not found or you're not a member")

    replies = client.conversations_replies(channel=channel["id"], ts=thread_ts)

    def resolve_user(uid):
        if uid not in user_cache:
            try:
                info = client.users_info(user=uid)
                p = info["user"].get("profile", {})
                user_cache[uid] = p.get("display_name") or p.get("real_name") or uid
            except Exception:
                user_cache[uid] = uid
        return user_cache[uid]

    messages = []
    for m in replies["messages"]:
        messages.append({
            "ts": m["ts"],
            "user": resolve_user(m.get("user", "?")),
            "text": m.get("text", ""),
        })
    return messages


def format_thread_for_prompt(messages: list) -> str:
    lines = []
    for m in messages:
        lines.append(f"[{m['ts']}] {m['user']}: {m['text']}")
    return "\n".join(lines)
