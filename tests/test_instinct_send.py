import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "instinct_send.py"
SPEC = importlib.util.spec_from_file_location("instinct_send", SCRIPT_PATH)
instinct_send = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(instinct_send)


class ConfigTests(unittest.TestCase):
    def test_write_and_load_config_locks_file_to_current_user(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"

            instinct_send.write_config(path, "+1 415 555 0100")

            self.assertEqual(
                instinct_send.load_config(path),
                {"participant_handle": "+1 415 555 0100"},
            )
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_load_config_rejects_a_missing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"

            with self.assertRaisesRegex(instinct_send.ConfigurationError, "not configured"):
                instinct_send.load_config(path)

    def test_load_config_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "participant_handle": "+14155550100",
                        "allow_arbitrary_recipients": True,
                    }
                )
            )

            with self.assertRaisesRegex(instinct_send.ConfigurationError, "unexpected"):
                instinct_send.load_config(path)

    def test_validate_handle_accepts_phone_or_email_only(self):
        self.assertEqual(instinct_send.validate_handle("+94 77 123 4567"), "+94 77 123 4567")
        self.assertEqual(instinct_send.validate_handle("agent@example.com"), "agent@example.com")

        for invalid in ("", "Instinct", "hello\nworld", "a@b"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(instinct_send.ConfigurationError):
                    instinct_send.validate_handle(invalid)


class MessageTests(unittest.TestCase):
    def test_validate_message_rejects_blank_or_oversized_text(self):
        for invalid in ("", "   ", "x" * (instinct_send.MAX_MESSAGE_CHARACTERS + 1)):
            with self.subTest(length=len(invalid)):
                with self.assertRaises(instinct_send.MessageError):
                    instinct_send.validate_message(invalid)

    def test_build_command_passes_user_values_as_arguments_not_script_source(self):
        handle = "agent@example.com"
        message = 'Buy the "final" item; $HOME must stay literal.'

        command = instinct_send.build_osascript_command(handle, message)

        self.assertEqual(command[:3], ["/usr/bin/osascript", "-e", instinct_send.APPLESCRIPT])
        self.assertEqual(command[3:], ["--", handle, message])
        self.assertNotIn(handle, instinct_send.APPLESCRIPT)
        self.assertNotIn(message, instinct_send.APPLESCRIPT)


class SendTests(unittest.TestCase):
    def test_send_reports_success_only_for_exact_sent_sentinel(self):
        completed = mock.Mock(returncode=0, stdout="SENT\n", stderr="")
        runner = mock.Mock(return_value=completed)

        result = instinct_send.send_message("agent@example.com", "Do the task", runner=runner)

        self.assertEqual(result, "SENT")
        runner.assert_called_once()

    def test_send_does_not_retry_when_messages_returns_an_error(self):
        completed = mock.Mock(returncode=1, stdout="", stderr="Messages got an error")
        runner = mock.Mock(return_value=completed)

        with self.assertRaisesRegex(instinct_send.SendError, "Messages got an error"):
            instinct_send.send_message("agent@example.com", "Do the task", runner=runner)

        runner.assert_called_once()

    def test_send_rejects_unexpected_success_output(self):
        completed = mock.Mock(returncode=0, stdout="maybe", stderr="")

        with self.assertRaisesRegex(instinct_send.SendError, "unexpected response"):
            instinct_send.send_message(
                "agent@example.com",
                "Do the task",
                runner=mock.Mock(return_value=completed),
            )


class CliTests(unittest.TestCase):
    def test_dry_run_reads_pinned_recipient_without_calling_osascript(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            instinct_send.write_config(config_path, "agent@example.com")
            with mock.patch.object(instinct_send, "DEFAULT_CONFIG_PATH", config_path):
                with mock.patch.object(instinct_send, "send_message") as send:
                    with mock.patch("builtins.print") as output:
                        code = instinct_send.main(
                            ["send", "--message", "Please handle this", "--dry-run"]
                        )

            self.assertEqual(code, 0)
            send.assert_not_called()
            rendered = " ".join(str(call.args[0]) for call in output.call_args_list)
            self.assertIn("agent@example.com", rendered)
            self.assertIn("Please handle this", rendered)

    def test_send_uses_stdin_and_configured_recipient(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            instinct_send.write_config(config_path, "+14155550100")
            with mock.patch.object(instinct_send, "DEFAULT_CONFIG_PATH", config_path):
                with mock.patch.object(instinct_send.sys, "stdin") as stdin:
                    stdin.read.return_value = "Final task brief"
                    with mock.patch.object(instinct_send, "send_message", return_value="SENT") as send:
                        code = instinct_send.main(["send", "--stdin"])

            self.assertEqual(code, 0)
            send.assert_called_once_with("+14155550100", "Final task brief")

    def test_cli_reports_configuration_failure_without_sending(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with mock.patch.object(instinct_send, "DEFAULT_CONFIG_PATH", missing):
                with mock.patch.object(instinct_send, "send_message") as send:
                    code = instinct_send.main(["send", "--message", "Task"])

            self.assertEqual(code, 2)
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
