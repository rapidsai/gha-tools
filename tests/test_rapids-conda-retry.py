import os
import subprocess
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"


def run_retry_wrapper(tmp_path, output):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    call_file = tmp_path / "calls"
    fake_conda = fake_bin / "conda"
    fake_conda.write_text(
        "#!/bin/bash\n"
        'calls=$(cat "${FAKE_CONDA_CALLS}" 2>/dev/null || printf 0)\n'
        "calls=$((calls + 1))\n"
        'printf "%s\\n" "${calls}" > "${FAKE_CONDA_CALLS}"\n'
        "if (( calls == 1 )); then\n"
        '  printf "%s\\n" "${FAKE_CONDA_OUTPUT}"\n'
        "  exit 1\n"
        "fi\n"
        "exit 0\n"
    )
    fake_conda.chmod(0o755)
    fake_echo = fake_bin / "rapids-echo-stderr"
    fake_echo.write_text("#!/bin/bash\nprintf '%s\\n' \"$*\" >&2\n")
    fake_echo.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "RAPIDS_CONDA_EXE": str(fake_conda),
        "RAPIDS_CONDA_RETRY_MAX": "1",
        "RAPIDS_CONDA_RETRY_SLEEP": "0",
        "FAKE_CONDA_CALLS": str(call_file),
        "FAKE_CONDA_OUTPUT": output,
    }
    result = subprocess.run(
        [str(TOOLS_DIR / "rapids-conda-retry"), "install", "example-package"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    calls = int(call_file.read_text())
    return result, calls


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_retry_wrapper_retries_transient_requests_http_errors(tmp_path, status):
    output = (
        "requests.exceptions.HTTPError: 502 Server Error: Bad Gateway for url: "
        "https://conda.anaconda.org/conda-forge/noarch/"
        "91a21f1daadc77692805e364f6b73d7579967053e21eee7ca6d67889a254b17e.msgpack.zst"
        if status == 502
        else f"requests.exceptions.HTTPError: {status} Server Error: transient response"
    )
    result, calls = run_retry_wrapper(tmp_path, output)

    assert result.returncode == 0
    assert calls == 2
    assert "transient requests HTTP status" in result.stderr


@pytest.mark.parametrize("status", [401, 403, 404])
def test_retry_wrapper_does_not_retry_permanent_requests_http_errors(tmp_path, status):
    result, calls = run_retry_wrapper(
        tmp_path,
        f"requests.exceptions.HTTPError: {status} Client Error: permanent response",
    )

    assert result.returncode == 1
    assert calls == 1
    assert "Exiting, no retryable " in result.stderr


def test_retry_wrapper_does_not_retry_unsatisfiable_environment(tmp_path):
    result, calls = run_retry_wrapper(tmp_path, "PackagesNotFoundError: the requested package does not exist")

    assert result.returncode == 1
    assert calls == 1
    assert "Exiting, no retryable " in result.stderr
