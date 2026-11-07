"""Exercise failed release downloads with the real retry helper and tar."""

import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1] / "tools"
VERSION = "0.17.0-rapids.4"


@pytest.fixture
def installer(tmp_path):
    binaries = tmp_path / "bin"
    binaries.mkdir()
    tar = shutil.which("gtar") or shutil.which("tar")
    if tar is None:
        pytest.fail("GNU tar is required for the Linux installer fixture")
    (binaries / "tar").symlink_to(tar)
    archive = tmp_path / "asset.tar.gz"
    script = f"#!/bin/sh\necho 'sccache {VERSION}'\n".encode()
    with tarfile.open(archive, "w:gz") as output:
        entry = tarfile.TarInfo("sccache/sccache")
        entry.size = len(script)
        entry.mode = 0o755
        output.addfile(entry, io.BytesIO(script))
    for name, content in {
        "sccache": "#!/bin/sh\necho 'sccache 0.0.0'\n",
        "rapids-prompt-local-github-auth": "#!/bin/sh\nexit 0\n",
        "sleep": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_SLEEPS"\n',
        "wget": """#!/bin/bash
if [[ "$*" == *--method=HEAD* ]]; then exit 0; fi
exec gh --clobber "$@"
""",
        "gh": """#!/bin/bash
set -euo pipefail
if [[ "${1:-}" == release && "${2:-}" == view ]]; then echo "$TEST_VERSION"; exit 0; fi
count=0
if [[ -f "$TEST_CALLS" ]]; then count=$(cat "$TEST_CALLS"); fi
count=$((count + 1))
printf '%s' "$count" > "$TEST_CALLS"
destination=-
clobber=false
while (( $# )); do
    case "$1" in
        --output|-O) destination=$2; shift ;;
        --clobber) clobber=true ;;
    esac
    shift
done
printf '%s\\n' "$destination" >> "$TEST_OUTPUTS"
if [[ "$destination" != - && -e "$destination" && "$clobber" != true ]]; then
    echo 'asset already exists' >&2
    exit 1
fi
if (( count <= TEST_FAILURES )); then
    echo 'HTTP 500 (https://api.github.com/repos/rapidsai/sccache/releases/assets/532853490)' >&2
    if [[ "$destination" == - ]]; then printf 'partial download'; else printf 'partial download' > "$destination"; fi
    exit 1
fi
if [[ "$destination" == - ]]; then cat "$TEST_ARCHIVE"; else cp "$TEST_ARCHIVE" "$destination"; fi
""",
    }.items():
        path = binaries / name
        path.write_text(content)
        path.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{binaries}:{TOOLS}:{os.environ['PATH']}",
        "SCCACHE_VERSION": VERSION,
        "RAPIDS_RETRY_MAX": "2",
        "RAPIDS_RETRY_SLEEP": "10",
        "TEST_ARCHIVE": str(archive),
        "TEST_VERSION": VERSION,
        "TEST_CALLS": str(tmp_path / "calls"),
        "TEST_OUTPUTS": str(tmp_path / "outputs"),
        "TEST_SLEEPS": str(tmp_path / "sleeps"),
    }
    return binaries, tmp_path, environment


@pytest.mark.parametrize("requested_version", [VERSION, "latest"])
@pytest.mark.parametrize("failures", [0, 1, 2])
def test_release_download_retries_without_corrupting_archive(installer, failures, requested_version):
    binaries, directory, environment = installer
    result = subprocess.run(
        [str(TOOLS / "rapids-install-sccache")],
        env={**environment, "TEST_FAILURES": str(failures), "SCCACHE_VERSION": requested_version},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (directory / "calls").read_text() == str(failures + 1)
    assert subprocess.check_output([str(binaries / "sccache"), "--version"], text=True).strip() == f"sccache {VERSION}"
    downloads = (directory / "outputs").read_text().splitlines()
    assert all(path != "-" and not Path(path).exists() for path in downloads)
    if failures:
        assert (directory / "sleeps").read_text().splitlines() == ["10"] * failures


@pytest.mark.parametrize("requested_version", [VERSION, "latest"])
def test_exhausted_release_download_does_not_extract_partial_bytes(installer, requested_version):
    binaries, directory, environment = installer
    result = subprocess.run(
        [str(TOOLS / "rapids-install-sccache")],
        env={**environment, "TEST_FAILURES": "10", "SCCACHE_VERSION": requested_version},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode != 0
    assert (directory / "calls").read_text() == ("3" if requested_version == VERSION else "6")
    assert subprocess.check_output([str(binaries / "sccache"), "--version"], text=True).strip() == "sccache 0.0.0"
    assert "not in gzip format" not in result.stderr
    assert all(not Path(path).exists() for path in (directory / "outputs").read_text().splitlines())


def test_latest_api_fallback_overwrites_exhausted_stable_download(installer):
    binaries, directory, environment = installer
    result = subprocess.run(
        [str(TOOLS / "rapids-install-sccache")],
        env={**environment, "TEST_FAILURES": "3", "SCCACHE_VERSION": "latest"},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (directory / "calls").read_text() == "4"
    assert subprocess.check_output([str(binaries / "sccache"), "--version"], text=True).strip() == f"sccache {VERSION}"
    assert all(not Path(path).exists() for path in (directory / "outputs").read_text().splitlines())
