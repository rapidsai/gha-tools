import os
import subprocess
from pathlib import Path

TOOLS_DIRECTORY = Path(__file__).resolve().parents[1] / "tools"


def _environment(**updates: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PATH"] = f"{TOOLS_DIRECTORY}:{environment['PATH']}"
    environment.update(updates)
    return environment


def test_release_candidate_is_a_release_build():
    result = subprocess.run(
        [TOOLS_DIRECTORY / "rapids-is-release-build"],
        env=_environment(RAPIDS_BUILD_TYPE="release-candidate", GITHUB_REF="refs/heads/main"),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "is release build" in result.stderr


def test_release_candidate_rattler_channels_exclude_public_rapids_channels():
    command = f'source "{TOOLS_DIRECTORY / "rapids-rattler-channel-string"}"; printf "%s\\n" "${{RATTLER_CHANNELS[*]}}"'
    result = subprocess.run(
        ["bash", "-c", command],
        env=_environment(
            RAPIDS_BUILD_TYPE="release-candidate",
            GITHUB_REF="refs/heads/main",
            RAPIDS_CONDA_BLD_OUTPUT_DIR="/tmp/conda-output",
        ),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines()[-1] == "--channel conda-forge"
    assert "rapidsai" not in result.stdout
