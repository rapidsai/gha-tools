import os
import shutil
import subprocess
from os import path

import pytest

TOOLS_DIR = path.join(path.dirname(path.realpath(__file__)), "..", "tools")

# Writes CONTENT to the -O/-o file argument (or stdout for gh), then exits with STATUS.
FAKE_TEMPLATE = """#!/bin/sh
echo "{name} $*" >> "{log}"
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    -O|-o) out="$2"; shift ;;
  esac
  shift
done
if [ -n "$out" ]; then
  printf '%s' '{content}' > "$out"
else
  printf '%s' '{content}'
fi
exit {status}
"""


@pytest.fixture
def env(tmp_path):
    util_bin = tmp_path / "util-bin"
    util_bin.mkdir()
    for util in ("bash", "cat", "mktemp", "rm"):
        os.symlink(shutil.which(util), util_bin / util)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    return {"fake_bin": fake_bin, "log": tmp_path / "calls.log", "path": f"{fake_bin}:{TOOLS_DIR}:{util_bin}"}


def add_fake(env, name, content, status):
    fake = env["fake_bin"] / name
    fake.write_text(FAKE_TEMPLATE.format(name=name, log=env["log"], content=content, status=status))
    fake.chmod(0o755)


def run_fetch(env, *args, ci=True):
    result = subprocess.run(
        [path.join(TOOLS_DIR, "rapids-github-fetch"), *args],
        env={"PATH": env["path"], **({"CI": "true"} if ci else {})},
        capture_output=True,
        text=True,
    )
    calls = env["log"].read_text().splitlines() if env["log"].exists() else []
    return result, calls


def test_gh_success(env):
    add_fake(env, "gh", "from-gh", 0)
    add_fake(env, "wget", "from-wget", 0)
    add_fake(env, "curl", "from-curl", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main")
    assert result.returncode == 0
    assert result.stdout == "from-gh"
    assert calls == [
        "gh api -H Accept: application/vnd.github.raw+json repos/rapidsai/rapids-cmake/contents/dir/file.json?ref=main"
    ]


def test_gh_authenticated_locally_checks_auth_before_fetching(env):
    add_fake(env, "gh", "from-gh", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main", ci=False)
    assert result.returncode == 0
    assert result.stdout == "from-gh"
    assert calls[0] == "gh auth status"
    assert calls[1].startswith("gh api ")
    assert len(calls) == 2


def test_gh_unauthenticated_locally_aborts_when_login_fails(env):
    add_fake(env, "gh", "", 1)
    add_fake(env, "wget", "from-wget", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main", ci=False)
    assert result.returncode == 1
    assert result.stdout == ""
    assert [" ".join(c.split()[:2]) for c in calls] == ["gh auth", "gh auth"]
    assert "GitHub authentication failed" in result.stderr


def test_auth_check_skipped_without_gh_locally(env):
    add_fake(env, "curl", "from-curl", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main", ci=False)
    assert result.returncode == 0
    assert result.stdout == "from-curl"
    assert [c.split()[0] for c in calls] == ["curl"]


def test_gh_failure_falls_back_to_wget_without_partial_output(env):
    add_fake(env, "gh", "partial-gh", 1)
    add_fake(env, "wget", "from-wget", 0)
    add_fake(env, "curl", "from-curl", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main")
    assert result.returncode == 0
    assert result.stdout == "from-wget"
    assert [c.split()[0] for c in calls] == ["gh", "wget"]
    assert calls[1].endswith("https://raw.githubusercontent.com/rapidsai/rapids-cmake/main/dir/file.json")


def test_wget_failure_falls_back_to_curl_without_partial_output(env):
    add_fake(env, "gh", "partial-gh", 1)
    add_fake(env, "wget", "partial-wget", 8)
    add_fake(env, "curl", "from-curl", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main")
    assert result.returncode == 0
    assert result.stdout == "from-curl"
    assert [c.split()[0] for c in calls] == ["gh", "wget", "curl"]
    assert calls[2].endswith("https://raw.githubusercontent.com/rapidsai/rapids-cmake/main/dir/file.json")


def test_missing_tools_are_skipped(env):
    add_fake(env, "curl", "from-curl", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main")
    assert result.returncode == 0
    assert result.stdout == "from-curl"
    assert [c.split()[0] for c in calls] == ["curl"]
    assert result.stderr == ""


def test_all_methods_fail(env):
    add_fake(env, "gh", "partial-gh", 1)
    add_fake(env, "wget", "partial-wget", 8)
    add_fake(env, "curl", "partial-curl", 22)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "dir/file.json", "main")
    assert result.returncode == 1
    assert result.stdout == ""
    assert [c.split()[0] for c in calls] == ["gh", "wget", "curl"]
    assert "Could not fetch dir/file.json from rapidsai/rapids-cmake@main" in result.stderr


def test_ref_defaults_to_head(env):
    add_fake(env, "gh", "partial-gh", 1)
    add_fake(env, "wget", "from-wget", 0)
    result, calls = run_fetch(env, "rapidsai/rapids-cmake", "file.json")
    assert result.returncode == 0
    assert calls[0].endswith("repos/rapidsai/rapids-cmake/contents/file.json?ref=HEAD")
    assert calls[1].endswith("https://raw.githubusercontent.com/rapidsai/rapids-cmake/HEAD/file.json")


@pytest.mark.parametrize("args", [[], ["rapidsai/rapids-cmake"]])
def test_missing_arguments(env, args):
    result, calls = run_fetch(env, *args)
    assert result.returncode == 1
    assert result.stdout == ""
    assert calls == []
    assert "Must specify input arguments: REPO PATH [REF]" in result.stderr
