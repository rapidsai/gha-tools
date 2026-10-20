import os
import stat
import subprocess
import tempfile
from os import path

import pytest

TOOLS_DIR = path.join(path.dirname(path.realpath(__file__)), "..", "tools")

FAKE_CONDA = """#!/bin/bash
count=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
echo $((count + 1)) > "$COUNT_FILE"
if (( count < FAIL_TIMES )); then
    echo "$FAIL_OUTPUT"
    exit 1
fi
exit 0
"""


def run_rapids_conda_retry(fail_output, fail_times):
    with tempfile.TemporaryDirectory() as d:
        fake_conda = path.join(d, "fake-conda")
        count_file = path.join(d, "count")
        with open(fake_conda, "w") as f:
            f.write(FAKE_CONDA)
        os.chmod(fake_conda, os.stat(fake_conda).st_mode | stat.S_IXUSR)

        env = {
            **os.environ,
            "PATH": f"{TOOLS_DIR}:{os.environ['PATH']}",
            "RAPIDS_CONDA_EXE": fake_conda,
            "RAPIDS_CONDA_RETRY_MAX": "2",
            "RAPIDS_CONDA_RETRY_SLEEP": "0",
            "COUNT_FILE": count_file,
            "FAIL_TIMES": str(fail_times),
            "FAIL_OUTPUT": fail_output,
        }
        process = subprocess.run(
            [path.join(TOOLS_DIR, "rapids-conda-retry"), "install", "pkg"],
            env=env,
            text=True,
            capture_output=True,
        )
        with open(count_file) as f:
            return process, int(f.read())


@pytest.mark.parametrize(
    "fail_output",
    [
        "requests.exceptions.HTTPError: 500 Server Error: Internal Server Error for url: https://conda.anaconda.org/x",
        "requests.exceptions.HTTPError: 502 Server Error: Bad Gateway for url: https://conda.anaconda.org/x",
        "requests.exceptions.HTTPError: 503 Server Error: Service Unavailable for url: https://conda.anaconda.org/x",
    ],
)
def test_retries_on_5xx_http_error(fail_output):
    process, calls = run_rapids_conda_retry(fail_output, fail_times=1)
    assert process.returncode == 0
    assert calls == 2
    assert "Retrying, found 'HTTPError:' in output..." in process.stderr


def test_gives_up_after_max_retries_on_http_error():
    output = "requests.exceptions.HTTPError: 502 Server Error: Bad Gateway for url: https://conda.anaconda.org/x"
    process, calls = run_rapids_conda_retry(output, fail_times=100)
    assert process.returncode == 1
    assert calls == 3
    assert "reached max retries" in process.stderr


@pytest.mark.parametrize("status", ["404 Client Error: Not Found", "429 Client Error: Too Many Requests"])
def test_retries_on_4xx_http_error(status):
    output = f"requests.exceptions.HTTPError: {status} for url: https://conda.anaconda.org/x"
    process, calls = run_rapids_conda_retry(output, fail_times=1)
    assert process.returncode == 0
    assert calls == 2


def test_does_not_retry_on_unrelated_error():
    process, calls = run_rapids_conda_retry("PackagesNotFoundError: pkg", fail_times=1)
    assert process.returncode == 1
    assert calls == 1
    assert "no retryable" in process.stderr
