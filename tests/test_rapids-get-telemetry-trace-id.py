import sys
import os.path
import subprocess

TOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tools")

def test_rapids_compute_trace_id():
    result = subprocess.run(
        os.path.join(TOOLS_DIR, "rapids-get-telemetry-trace-id"),
        env={
            "GITHUB_REPOSITORY": "rapidsai/gha-tools",
            "GITHUB_RUN_ID": "1123123",
            "GITHUB_RUN_ATTEMPT": "1"
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "22ab4ec60f37f446b4a95917e86660df"
    assert result.stderr == ""
    assert result.returncode == 0

def test_rapids_get_traceparent():
        # this should raise, because OTEL_SERVICE_NAME isn't set
    try:
        result = subprocess.run(
            [os.path.join(TOOLS_DIR, "rapids-get-telemetry-traceparent"), "my_job"],
            env={
                "GITHUB_REPOSITORY": "rapidsai/gha-tools",
                "GITHUB_RUN_ID": "1123123",
                "GITHUB_RUN_ATTEMPT": "1"
            },
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        pass
    result = subprocess.run(
        os.path.join(TOOLS_DIR, "rapids-get-telemetry-traceparent"),
        env={
            "GITHUB_REPOSITORY": "rapidsai/gha-tools",
            "GITHUB_RUN_ID": "1123123",
            "GITHUB_RUN_ATTEMPT": "1",
            "OTEL_SERVICE_NAME": "my job"
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "00-22ab4ec60f37f446b4a95917e86660df-737c2f0e9d9bd9b0-01"
    assert result.stderr == ""
    assert result.returncode == 0

def test_rapids_get_traceparent_with_step():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-get-telemetry-traceparent"), "my step"],
        env={
            "GITHUB_REPOSITORY": "rapidsai/gha-tools",
            "GITHUB_RUN_ID": "1123123",
            "GITHUB_RUN_ATTEMPT": "1",
            "OTEL_SERVICE_NAME": "my_job",
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "00-22ab4ec60f37f446b4a95917e86660df-5f57388b5b07a3e8-01"
    assert result.stderr == ""
    assert result.returncode == 0


def test_wrap_otel():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "echo", "bob"],
        text=True,
        capture_output=True,
    )
    assert result.stdout == "bob\n"
    assert result.stderr == "Skipping instrumentation, running \"echo bob\"\n"
    assert result.returncode == 0

def test_wrap_otel_with_spaces():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "echo", "-n", "bob is here"],
        text=True,
        capture_output=True,
    )
    # Note: no newline here, because echo -n shouldn't end with a newline
    assert result.stdout == "bob is here"
    assert result.stderr == "Skipping instrumentation, running \"echo -n bob is here\"\n"
    assert result.returncode == 0

def test_wrap_otel_with_spaces_and_parens():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "python", "-c", "import sys; print(sys.version)"],
        text=True,
        capture_output=True,
    )
    # Note: no newline here, because echo -n shouldn't end with a newline
    assert result.stderr == "Skipping instrumentation, running \"python -c import sys; print(sys.version)\"\n"
    assert result.stdout == "{}\n".format(sys.version)
    assert result.returncode == 0