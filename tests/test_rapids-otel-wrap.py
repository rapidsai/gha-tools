
import sys
import os.path
import subprocess

TOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tools")

def test_wrap_otel():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "echo", "bob"],
        text=True,
        capture_output=True,
    )
    assert result.stdout == "bob\n"
    assert result.returncode == 0

def test_wrap_otel_with_spaces():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "echo", "-n", "bob is here"],
        text=True,
        capture_output=True,
    )
    # Note: no newline here, because echo -n shouldn't end with a newline
    assert result.stdout == "bob is here"
    assert result.returncode == 0

def test_wrap_otel_with_spaces_and_parens():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "python", "-c", "import sys; print(sys.version)"],
        text=True,
        capture_output=True,
    )
    assert result.stdout == "{}\n".format(sys.version)
    assert result.returncode == 0

def test_wrap_otel_with_evil_comparison_operators():
    result = subprocess.run(
        [os.path.join(TOOLS_DIR, "rapids-otel-wrap"), "python", "-c", 'print(str(1<2))'],
        text=True,
        capture_output=True,
    )
    assert result.stdout == "True\n"
    assert result.returncode == 0

# This differs from the test above in that everything is combined into one string, and we're running it as a true shell
def test_wrap_otel_with_evil_comparison_operators_with_shell():
    result = subprocess.run(
        '{} python -c "print(str(1<2))"'.format(os.path.join(TOOLS_DIR, "rapids-otel-wrap")),
        text=True,
        capture_output=True,
        shell=True
    )
    assert result.stdout == "True\n"
    assert result.returncode == 0