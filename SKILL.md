---
name: send-to-instinct
description: Send the final decisions and necessary context from the current conversation to the user's pinned Instinct iMessage contact. Use only when the user explicitly invokes this skill to hand work off to Instinct.
---

# Send to Instinct

Turn the useful conclusion of the current conversation into one ordinary natural-language message and send it to the configured Instinct recipient.

## Set up once

When the user explicitly invokes this skill and no recipient is configured, resolve `scripts/instinct_send.py` relative to this file and search Contacts:

```text
python3 <skill-directory>/scripts/instinct_send.py detect --json
```

Detection only returns phone numbers and email addresses from contacts whose exact name is `Instinct`. It does not configure a recipient or send a message.

Show the user each candidate with its handle masked, and ask them to confirm the correct one. A contact name alone is never proof: if there is more than one candidate, let the user choose. After explicit confirmation, pin that candidate's exact handle:

```text
python3 <skill-directory>/scripts/instinct_send.py configure --handle <phone-or-apple-id>
```

If no candidate is found, ask the user for the phone number or Apple ID shown in their Instinct iMessage conversation and configure that exact handle. This pins one recipient in a local user-only configuration shared by the user's coding agents. Configuring does not send a message.

## Prepare the handoff

- Preserve the action the user requested: research, contact, add to cart, buy, book, or another task. Do not weaken or expand it.
- Include final selections, quantities, links, files, limits, deadlines, and other constraints Instinct actually needs.
- Omit rejected alternatives, deliberation, implementation commentary, and unrelated conversation history.
- Never include passwords, API keys, card numbers, repository secrets, or unrelated personal information.
- Prefer a short self-contained message. Do not add task IDs, YAML, status protocols, or demands for completion reporting unless the user requested them.

Explicit invocation authorizes sending one message to the pinned Instinct recipient. When the request is sufficiently clear, do not add another confirmation step. Never send a second copy automatically after an error or timeout.

## Send

Resolve `scripts/instinct_send.py` relative to this file. Pass the prepared message through process standard input, not by interpolating it into AppleScript or shell source:

```text
python3 <skill-directory>/scripts/instinct_send.py send --stdin
```

If the helper reports that Instinct is not configured, stop without sending and run the one-time detection and confirmation flow above. Never select a candidate merely because its contact name is `Instinct`.

After success, report the exact message that was sent and say only that it was sent to Instinct. Do not claim that Instinct accepted, started, or completed the task.
