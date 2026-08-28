import os
import subprocess
from pathlib import Path

import pytest


TOOLS_DIRECTORY = Path(__file__).resolve().parents[1] / "tools"


def _generate_version(tmp_path: Path, candidate_version: str | None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if candidate_version is None:
        environment.pop("RAPIDS_RELEASE_CANDIDATE_VERSION", None)
    else:
        environment["RAPIDS_RELEASE_CANDIDATE_VERSION"] = candidate_version
    return subprocess.run(
        [TOOLS_DIRECTORY / "rapids-generate-version"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_candidate_version_returns_exact_final_version_without_git_tag(tmp_path):
    tmp_path.joinpath("VERSION").write_text("26.10.00\n")

    result = _generate_version(tmp_path, "26.10.00")

    assert result.returncode == 0
    assert result.stdout == "26.10.00"
    assert result.stderr == ""


@pytest.mark.parametrize("candidate_version", ["v26.10.00", "26.10", "26.10.0", "26.10.00rc0"])
def test_release_candidate_version_rejects_non_final_formats(tmp_path, candidate_version):
    tmp_path.joinpath("VERSION").write_text("26.10.00\n")

    result = _generate_version(tmp_path, candidate_version)

    assert result.returncode == 1
    assert "must use YY.MM.PP format" in result.stderr


def test_release_candidate_version_rejects_different_source_major_minor(tmp_path):
    tmp_path.joinpath("VERSION").write_text("26.12.00a0\n")

    result = _generate_version(tmp_path, "26.10.00")

    assert result.returncode == 1
    assert "does not match VERSION major/minor '26.12'" in result.stderr


def test_release_candidate_version_requires_version_file(tmp_path):
    result = _generate_version(tmp_path, "26.10.00")

    assert result.returncode == 1
    assert "requires a VERSION file" in result.stderr
