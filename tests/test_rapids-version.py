import subprocess
import tempfile
from os import path

import pytest

TOOLS_DIR = path.join(path.dirname(path.realpath(__file__)), "..", "tools")


def run_rapids_version(tool_name, cwd, exit_code, output):
    process = subprocess.Popen(
        [path.join(TOOLS_DIR, tool_name)], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    process.wait()
    assert process.returncode == exit_code
    assert process.stdout.read() == output
    assert process.stderr.read() == ""


@pytest.mark.parametrize(
    "version_contents, exit_code, version, version_major_minor",
    [
        ("24.00.00\n", 0, "24.00.00\n", "24.00\n"),
        ("24.02.00a1\n", 0, "24.02.00\n", "24.02\n"),
        ("invalid\n", 1, "", ""),
        ("", 1, "", ""),
        (None, 1, "", ""),
    ],
)
def test_rapids_version(version_contents, exit_code, version, version_major_minor):
    with tempfile.TemporaryDirectory() as d:
        if version_contents is not None:
            with open(path.join(d, "VERSION"), "w") as f:
                f.write(version_contents)

        run_rapids_version("rapids-version", d, exit_code, version)
        run_rapids_version("rapids-version-major-minor", d, exit_code, version_major_minor)
