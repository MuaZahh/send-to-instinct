#!/usr/bin/env python3
"""Send one text message to a single configured Instinct iMessage recipient."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable, Sequence


DEFAULT_CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "SendToInstinct" / "config.json"
)
MAX_MESSAGE_CHARACTERS = 12_000

APPLESCRIPT = r'''
on run argv
    if (count of argv) is not 2 then error "Expected a participant handle and message"
    set participantHandle to item 1 of argv
    set messageText to item 2 of argv
    set messagesWasRunning to application "Messages" is running

    try
        tell application "Messages"
            set targetAccount to first account whose service type is iMessage
            set targetParticipant to participant participantHandle of targetAccount
            if (handle of targetParticipant) is not participantHandle then error "Configured participant mismatch"
            send messageText to targetParticipant
        end tell
    on error errorMessage number errorNumber
        if not messagesWasRunning then quit application "Messages"
        error errorMessage number errorNumber
    end try

    if not messagesWasRunning then quit application "Messages"

    return "SENT"
end run
'''.strip()

DETECT_APPLESCRIPT = r'''
set contactsWasRunning to application "Contacts" is running

try
    tell application "Contacts"
        set outputRows to {}
        set matchingPeople to every person whose name is "Instinct"

        repeat with matchingPerson in matchingPeople
            set contactID to id of matchingPerson
            set contactName to name of matchingPerson

            repeat with phoneEntry in phones of matchingPerson
                set end of outputRows to contactID & tab & contactName & tab & "phone" & tab & (value of phoneEntry)
            end repeat

            repeat with emailEntry in emails of matchingPerson
                set end of outputRows to contactID & tab & contactName & tab & "email" & tab & (value of emailEntry)
            end repeat
        end repeat

        set previousDelimiters to AppleScript's text item delimiters
        set AppleScript's text item delimiters to linefeed
        set renderedOutput to outputRows as text
        set AppleScript's text item delimiters to previousDelimiters
    end tell
on error errorMessage number errorNumber
    if not contactsWasRunning then quit application "Contacts"
    error errorMessage number errorNumber
end try

if not contactsWasRunning then quit application "Contacts"
return renderedOutput
'''.strip()


class InstinctSendError(Exception):
    """Base error for expected helper failures."""


class ConfigurationError(InstinctSendError):
    """The pinned recipient configuration is missing or invalid."""


class DetectionError(InstinctSendError):
    """Contacts could not be searched safely."""


class MessageError(InstinctSendError):
    """The outgoing message is invalid."""


class SendError(InstinctSendError):
    """Messages did not confirm that the send command completed."""


def validate_handle(value: str) -> str:
    handle = value.strip()
    email = re.fullmatch(r"[^@\s]{2,}@[^@\s]{2,}\.[^@\s]{2,}", handle)
    phone = re.fullmatch(r"\+?[0-9][0-9 ()-]{5,}[0-9]", handle)
    if email:
        return handle
    if not phone:
        raise ConfigurationError(
            "Instinct handle must be a complete phone number or Apple ID email address"
        )
    prefix = "+" if handle.startswith("+") else ""
    digits = "".join(character for character in handle if character.isdigit())
    return prefix + digits


def validate_message(value: str) -> str:
    if not value.strip():
        raise MessageError("Message cannot be blank")
    if len(value) > MAX_MESSAGE_CHARACTERS:
        raise MessageError(
            f"Message exceeds the {MAX_MESSAGE_CHARACTERS}-character safety limit"
        )
    return value


def friendly_automation_error(detail: str, target: str) -> str:
    normalized = detail.casefold()
    permission_markers = (
        "-1743",
        "not authorized to send apple events",
        "not authorised to send apple events",
        "not permitted to send apple events",
        "a privilege violation",
    )
    if not any(marker in normalized for marker in permission_markers):
        return detail
    if target == "Contacts":
        return (
            "macOS blocked Contacts access. In System Settings > Privacy & Security, "
            "allow your coding agent or terminal under Contacts and Automation, then try again."
        )
    return (
        f"macOS blocked {target} automation. Open System Settings > Privacy & Security > "
        f"Automation, allow your coding agent or terminal to control {target}, then try again."
    )


def parse_detected_contacts(output: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        contact_id, name, kind, handle = (part.strip() for part in parts)
        if not contact_id or name.casefold() != "instinct" or kind not in {"phone", "email"}:
            continue
        try:
            validated = validate_handle(handle)
        except ConfigurationError:
            continue
        key = (contact_id, kind, validated)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "contact_id": contact_id,
                "name": name,
                "kind": kind,
                "handle": validated,
            }
        )

    return candidates


def detect_instinct_candidates(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[dict[str, str]]:
    command = ["/usr/bin/osascript", "-e", DETECT_APPLESCRIPT]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise DetectionError("Contacts search timed out; no recipient was selected") from error
    except OSError as error:
        raise DetectionError(f"Could not start Contacts automation: {error}") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "Contacts search failed"
        raise DetectionError(friendly_automation_error(detail, "Contacts"))
    return parse_detected_contacts(completed.stdout)


def mask_handle(handle: str) -> str:
    validated = validate_handle(handle)
    if "@" in validated:
        local, domain = validated.split("@", 1)
        return f"{local[0]}{'•' * max(4, len(local) - 1)}@{domain}"

    digits = "".join(character for character in validated if character.isdigit())
    suffix = digits[-4:]
    if validated.startswith("+") and len(digits) == 11 and digits.startswith("1"):
        return f"+1 ••• ••• {suffix}"
    prefix = "+" if validated.startswith("+") else ""
    return f"{prefix}••• ••• {suffix}"


def write_config(path: Path, handle: str) -> None:
    validated = validate_handle(handle)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    payload = json.dumps({"participant_handle": validated}, indent=2) + "\n"

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".config-", suffix=".json", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, str]:
    if not path.is_file():
        raise ConfigurationError(
            f"Instinct is not configured. Run configure first; expected {path}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigurationError(f"Could not read Instinct configuration: {error}") from error

    if not isinstance(payload, dict):
        raise ConfigurationError("Instinct configuration must be a JSON object")
    unexpected = set(payload) - {"participant_handle"}
    if unexpected:
        raise ConfigurationError(
            "Instinct configuration has unexpected fields: " + ", ".join(sorted(unexpected))
        )
    if "participant_handle" not in payload or not isinstance(payload["participant_handle"], str):
        raise ConfigurationError("Instinct configuration is missing participant_handle")

    return {"participant_handle": validate_handle(payload["participant_handle"])}


def build_osascript_command(handle: str, message: str) -> list[str]:
    return [
        "/usr/bin/osascript",
        "-e",
        APPLESCRIPT,
        "--",
        validate_handle(handle),
        validate_message(message),
    ]


def send_message(
    handle: str,
    message: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    command = build_osascript_command(handle, message)
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise SendError(
            "Messages send timed out. The result is unknown; do not retry automatically."
        ) from error
    except OSError as error:
        raise SendError(f"Could not start Messages automation: {error}") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "Messages automation failed"
        raise SendError(friendly_automation_error(detail, "Messages"))
    if completed.stdout.strip() != "SENT":
        raise SendError(
            "Messages returned an unexpected response. The result is unknown; "
            "do not retry automatically."
        )
    return "SENT"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a message only to the configured Instinct iMessage recipient."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    configure = commands.add_parser("configure", help="Pin Instinct's phone or Apple ID")
    configure.add_argument("--handle", required=True)

    detect = commands.add_parser(
        "detect", help="Find exact-name Instinct contacts without selecting or sending"
    )
    detect.add_argument("--json", action="store_true", help="Print machine-readable candidates")

    commands.add_parser("status", help="Show the configured recipient")

    send = commands.add_parser("send", help="Send one message to the pinned recipient")
    source = send.add_mutually_exclusive_group(required=True)
    source.add_argument("--message")
    source.add_argument("--stdin", action="store_true")
    send.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the pinned recipient and message without opening Messages",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "detect":
            candidates = detect_instinct_candidates()
            if arguments.json:
                print(json.dumps(candidates))
            elif not candidates:
                print("No exact-name Instinct contacts found.")
            else:
                for index, candidate in enumerate(candidates, start=1):
                    print(
                        f"{index}. {candidate['name']} — {candidate['kind']} "
                        f"{mask_handle(candidate['handle'])}"
                    )
                print("No recipient was selected or configured.")
            return 0

        if arguments.command == "configure":
            write_config(DEFAULT_CONFIG_PATH, arguments.handle)
            print(f"Configured Instinct recipient: {validate_handle(arguments.handle)}")
            print(f"Configuration: {DEFAULT_CONFIG_PATH}")
            return 0

        config = load_config(DEFAULT_CONFIG_PATH)
        handle = config["participant_handle"]

        if arguments.command == "status":
            print(f"Configured Instinct recipient: {handle}")
            return 0

        message = sys.stdin.read() if arguments.stdin else arguments.message
        message = validate_message(message)
        if arguments.dry_run:
            print(f"Would send to Instinct ({handle}):")
            print(message)
            return 0

        send_message(handle, message)
        print(f"Sent to Instinct ({handle}).")
        return 0
    except InstinctSendError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
