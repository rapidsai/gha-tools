import os
import subprocess
from pathlib import Path

import pytest

TOOLS_DIRECTORY = Path(__file__).resolve().parents[1] / "tools"


def _generate_version(
    tmp_path: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["RAPIDS_BUILD_TYPE"] = "release-candidate"
    return subprocess.run(
        [TOOLS_DIRECTORY / "rapids-generate-version"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize("source_version", ["26.10.00", "0.3.0", "0.52", "00.52", "00.52.01"])
def test_release_candidate_version_returns_source_version(tmp_path, source_version):
    tmp_path.joinpath("VERSION").write_text(f"{source_version}\n")

    result = _generate_version(tmp_path)

    assert result.returncode == 0
    assert result.stdout == source_version
    assert result.stderr == ""


@pytest.mark.parametrize("source_version", ["v26.10.00", "26", "26.10.00.1", "26.10.00rc0"])
def test_release_candidate_version_rejects_non_final_formats(tmp_path, source_version):
    tmp_path.joinpath("VERSION").write_text(f"{source_version}\n")

    result = _generate_version(tmp_path)

    assert result.returncode == 1
    assert "VERSION file must use a numeric YY.MM or YY.MM.XX format" in result.stderr


def test_release_candidate_version_uses_committed_version_when_output_redirect_truncates_file(tmp_path):
    tmp_path.joinpath("VERSION").write_text("26.10.00\n")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "VERSION"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "Add version",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    environment = os.environ.copy()
    environment["RAPIDS_BUILD_TYPE"] = "release-candidate"

    result = subprocess.run(
        ["bash", "-c", f'"{TOOLS_DIRECTORY / "rapids-generate-version"}" > VERSION'],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert tmp_path.joinpath("VERSION").read_text() == "26.10.00"


def test_release_candidate_version_requires_version_file(tmp_path):
    result = _generate_version(tmp_path)

    assert result.returncode == 1
    assert "require a non-empty VERSION file in the working tree or at HEAD" in result.stderr
