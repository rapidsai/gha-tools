"""Regression tests for the opt-in stdout-only quiet mode."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"

FAKE_CONDA = """#!/usr/bin/env bash
if [[ "$1" == "clean" ]]; then
    echo "cache cleaned"
    echo "cache stderr" >&2
    exit 0
fi
count=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
echo $((count + 1)) > "$COUNT_FILE"
if (( count < FAIL_TIMES )); then
    printf '%s' "$FAIL_STDOUT"
    printf '%s' "$FAIL_STDERR" >&2
    exit 1
fi
printf '%s' "$SUCCESS_STDOUT"
printf '%s' "$SUCCESS_STDERR" >&2
exit 0
"""


def run_quiet(
    tmp_path,
    *,
    quiet=True,
    fail_times=1,
    fail_stdout='{"error":',
    fail_stderr="CondaHTTPError: temporary failure\n",
    success_stdout='{"success":true}\n',
    success_stderr="",
):
    fake_conda = tmp_path / "fake-conda"
    fake_conda.write_text(FAKE_CONDA)
    fake_conda.chmod(fake_conda.stat().st_mode | stat.S_IXUSR)
    count_file = tmp_path / "count"
    env = {
        **os.environ,
        "PATH": f"{TOOLS_DIR}:{os.environ['PATH']}",
        "RAPIDS_CONDA_EXE": str(fake_conda),
        "RAPIDS_CONDA_RETRY_MAX": "2",
        "RAPIDS_CONDA_RETRY_SLEEP": "0",
        "RAPIDS_CONDA_RETRY_TIMEOUT": "5s",
        "COUNT_FILE": str(count_file),
        "FAIL_TIMES": str(fail_times),
        "FAIL_STDOUT": fail_stdout,
        "FAIL_STDERR": fail_stderr,
        "SUCCESS_STDOUT": success_stdout,
        "SUCCESS_STDERR": success_stderr,
        "RAPIDS_CONDA_RETRY_QUIET": "1" if quiet else "0",
    }
    process = subprocess.run(
        [str(TOOLS_DIR / "rapids-conda-retry"), "create", "--dry-run", "--json"],
        env=env,
        text=True,
        capture_output=True,
    )
    return process, int(count_file.read_text())


def test_failed_attempt_discarded_from_stdout(tmp_path):
    result, attempts = run_quiet(tmp_path)
    assert result.returncode == 0
    assert attempts == 2
    assert result.stdout == '{"success":true}\n'
    assert '{"error":' in result.stderr
    assert "CondaHTTPError" in result.stderr


def test_successful_stderr_remains_separate(tmp_path):
    result, attempts = run_quiet(tmp_path, fail_times=0, success_stderr="conda warning\n")
    assert result.returncode == 0
    assert attempts == 1
    assert result.stdout == '{"success":true}\n'
    assert "conda warning" in result.stderr


def test_nonretryable_failure_has_empty_stdout(tmp_path):
    result, attempts = run_quiet(tmp_path, fail_stderr="PackagesNotFoundError: pkg\n")
    assert result.returncode == 1
    assert attempts == 1
    assert result.stdout == ""
    assert "PackagesNotFoundError" in result.stderr
    assert "no retryable" in result.stderr


def test_exhausted_retries_have_empty_stdout(tmp_path):
    result, attempts = run_quiet(tmp_path, fail_times=100)
    assert result.returncode == 1
    assert attempts == 3
    assert result.stdout == ""
    assert "reached max retries" in result.stderr


def test_cache_cleaning_does_not_contaminate_stdout(tmp_path):
    result, attempts = run_quiet(tmp_path, fail_stderr="CondaMultiError: corrupt tarball\n")
    assert result.returncode == 0
    assert attempts == 2
    assert result.stdout == '{"success":true}\n'
    assert "cache cleaned" in result.stderr
    assert "cache stderr" in result.stderr


def test_legacy_streaming_is_unchanged(tmp_path):
    result, attempts = run_quiet(tmp_path, quiet=False)
    assert result.returncode == 0
    assert attempts == 2
    assert '{"error":' in result.stdout
    assert '{"success":true}' in result.stdout
    assert "CondaHTTPError" in result.stdout


@pytest.mark.parametrize("error", ["CondaHTTPError:", "JSONDecodeError:", "ChecksumMismatchError:"])
def test_retry_classification_checks_stderr_in_quiet_mode(tmp_path, error):
    result, attempts = run_quiet(tmp_path, fail_stdout="", fail_stderr=error)
    assert result.returncode == 0
    assert attempts == 2
    assert result.stdout == '{"success":true}\n'
