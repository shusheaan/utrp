"""Run the real launcher against fake commands: never control user services."""
import os
import subprocess
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "ops/portal"


def invoke(tmp_path: Path, action: str, failure: str = "", *,
           stream: bool = True) -> tuple[int, list[str]]:
    home = tmp_path / "home with spaces"
    commands = tmp_path / "commands"
    commands.mkdir(exist_ok=True)
    (home / ".local/bin").mkdir(parents=True, exist_ok=True)
    log = tmp_path / "commands.log"
    log.write_text("")
    config = home / "storage/home/UserData/.config/portal/config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("[stream]\n" if stream else "")
    auth = home / ".local/bin/ytmusic"
    auth.write_text('''#!/bin/bash
[[ $# == 1 && $1 == --auth ]] || exit 9
printf 'refresh-auth\\n' >> "$TEST_LOG"
if [[ "$FAIL_AT" == auth ]]; then exit 17; fi
''')
    auth.chmod(0o755)
    systemctl = commands / "systemctl"
    systemctl.write_text('''#!/bin/bash
printf 'systemctl %s\\n' "$*" >> "$TEST_LOG"
if [[ "$*" == "--user stop portal.service" && "$FAIL_AT" == web ]]; then exit 1; fi
if [[ "$*" == "--user stop portal-stream.service portal-cmus.service" && "$FAIL_AT" == players ]]; then exit 1; fi
''')
    helper = home / ".local/bin/utrp-portal"
    helper.write_text('''#!/bin/bash
[[ $# == 2 && $1 == stop-playback && $2 == "$HOME/storage/home/UserData/.config/portal/config.toml" ]] || exit 9
printf 'stop-playback\\n' >> "$TEST_LOG"
[[ "$FAIL_AT" != helper ]]
''')
    systemctl.chmod(0o755)
    helper.chmod(0o755)
    env = dict(os.environ, HOME=str(home), PATH=f"{commands}:/usr/bin:/bin",
               TEST_LOG=str(log), FAIL_AT=failure)
    arguments = ["bash", str(LAUNCHER)] + ([action] if action else [])
    result = subprocess.run(arguments, env=env, capture_output=True,
                            text=True, check=False, timeout=5)
    return result.returncode, log.read_text().splitlines()


@pytest.mark.parametrize("failure", ["", "web", "players", "helper"])
def test_stop_attempts_all_steps_and_reports_failures(tmp_path: Path, failure: str) -> None:
    code, calls = invoke(tmp_path, "stop", failure)
    assert code == (1 if failure else 0)
    assert calls == [
        "systemctl --user stop portal.service",
        "systemctl --user stop portal-stream.service portal-cmus.service",
        "stop-playback",
    ]


@pytest.mark.parametrize("action", ["", "start", "restart", "enable"])
def test_start_and_restart_do_not_stop_players(tmp_path: Path, action: str) -> None:
    code, calls = invoke(tmp_path, action)
    assert code == 0
    command = "enable --now" if action == "enable" else action or "start"
    assert calls == ["refresh-auth", f"systemctl --user {command} portal.service"]


@pytest.mark.parametrize("action", ["", "start", "restart", "enable"])
def test_auth_failure_keeps_services_unchanged(tmp_path: Path, action: str) -> None:
    code, calls = invoke(tmp_path, action, "auth")
    assert code == 17
    assert calls == ["refresh-auth"]


@pytest.mark.parametrize("action", ["start", "restart"])
def test_local_only_needs_no_auth(tmp_path: Path, action: str) -> None:
    code, calls = invoke(tmp_path, action, stream=False)
    assert code == 0
    assert calls == [f"systemctl --user {action} portal.service"]


def test_every_start_refreshes_even_if_service_already_running(tmp_path: Path) -> None:
    for _ in range(2):
        code, calls = invoke(tmp_path, "start")
        assert code == 0
        assert calls == ["refresh-auth", "systemctl --user start portal.service"]


def test_repeated_stop_is_safe(tmp_path: Path) -> None:
    assert invoke(tmp_path, "stop")[0] == 0
    assert invoke(tmp_path, "stop")[0] == 0
