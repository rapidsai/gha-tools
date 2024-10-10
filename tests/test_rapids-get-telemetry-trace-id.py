import os.path
import subprocess

TOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tools")

def test_rapids_compute_trace_id():
    result = subprocess.run(
        os.path.join(TOOLS_DIR, "rapids-get-telemetry-trace-id"),
        env={
            "GITHUB_REPOSITORY": "rapidsai/gha-tools",
            "GITHUB_RUN_ID": "1123123",
            "RUN_ATTEMPT": "1"
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "22ab4ec60f37f446b4a95917e86660df"
    assert result.stderr == ""
    assert result.returncode == 0

def test_rapids_get_traceparent():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-get-telemetry-traceparent"), "my_job"],
        env={
            "GITHUB_REPOSITORY": "rapidsai/gha-tools",
            "GITHUB_RUN_ID": "1123123",
            "RUN_ATTEMPT": "1"
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "00-22ab4ec60f37f446b4a95917e86660df-5f57388b5b07a3e8-01"
    assert result.stderr == ""
    assert result.returncode == 0

def test_rapids_get_traceparent_with_step():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-get-telemetry-traceparent"), "my_job", "my step"],
        env={
            "GITHUB_REPOSITORY": "rapidsai/gha-tools",
            "GITHUB_RUN_ID": "1123123",
            "RUN_ATTEMPT": "1"
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "00-22ab4ec60f37f446b4a95917e86660df-a6e5bc57fad91889-01"
    assert result.stderr == ""
    assert result.returncode == 0