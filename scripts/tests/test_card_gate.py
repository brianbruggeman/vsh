import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.card_gate import failed_count, passed_count, result_is_green, run_card


def test_pytest_summary_requires_nonzero_passes():
    assert passed_count("================ 2 passed, 1 deselected in 1s ================") == 2
    assert passed_count("================ 0 passed, 3 deselected in 1s ================") == 0


def test_cargo_summary_is_counted():
    output = "test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out"
    assert passed_count(output) == 7
    assert result_is_green(0, output)


def test_missing_or_unrelated_result_line_is_not_green():
    assert passed_count("log: 12 passed previously\nno tests collected") == 0
    assert not result_is_green(0, "log: 12 passed previously\nno tests collected")
    assert not result_is_green(0, "")


def test_failed_result_or_command_is_red():
    output = "================ 2 passed, 1 failed in 1s ================"
    assert failed_count(output) == 1
    assert not result_is_green(0, output)
    assert not result_is_green(1, "================ 2 passed in 1s ================")


def test_cargo_failed_status_is_red_even_if_counts_claim_zero_failures():
    output = "test result: FAILED. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out"
    assert not result_is_green(0, output)


def test_run_card_captures_and_logs_a_real_result(tmp_path, capsys):
    log_path = tmp_path / "card.log"
    command = [sys.executable, "-c", "print('================ 3 passed in 0.1s ================')"]

    assert run_card("C01", command, log_path) == 0
    assert "GREEN C01" in capsys.readouterr().out
    assert "3 passed" in log_path.read_text()


def test_run_card_rejects_zero_tests_and_saves_output(tmp_path):
    log_path = tmp_path / "card.log"
    command = [sys.executable, "-c", "print('no tests collected')"]

    assert run_card("C01", command, log_path) == 1
    assert log_path.read_text() == "no tests collected\n"


def test_run_card_returns_nonzero_child_status_with_passing_output(tmp_path):
    log_path = tmp_path / "card.log"
    command = [sys.executable, "-c", "print('================ 3 passed in 0.1s ================'); raise SystemExit(7)"]

    assert run_card("C01", command, log_path) == 7
    assert "3 passed" in log_path.read_text()


def test_progress_events_have_utc_timestamps_and_eta_fields():
    repo_root = Path(__file__).parents[2]
    events = [json.loads(line) for line in (repo_root / "docs/cards/progress.jsonl").read_text().splitlines()]

    assert events
    for event in events:
        timestamp = datetime.fromisoformat(event["at"].replace("Z", "+00:00"))
        assert timestamp.utcoffset() == timezone.utc.utcoffset(timestamp)
        assert {"event", "done", "todo", "eta_minutes"} <= event.keys()
        assert isinstance(event["eta_minutes"], int) and event["eta_minutes"] > 0

    c01 = [event for event in events if event.get("card") == "C01"]
    started = next(event for event in c01 if event["event"] == "start")
    ready = next(event for event in c01 if event["event"] == "ready_to_land")
    assert started["at"] < ready["at"]
    assert ready["elapsed_minutes"] > 0
    assert ready["done"] == []
    assert ready["todo"] == ["C01-C28"]
