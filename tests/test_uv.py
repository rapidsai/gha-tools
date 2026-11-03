"""Exercise opt-in uv behavior without requiring CUDA or native compilation."""

import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


@pytest.fixture
def environment(tmp_path):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PIP_", "UV_", "NV_GHA_RUNNERS_")) and k not in ("BASH_ENV", "ENV")
    }
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python").symlink_to(sys.executable)
    uv = bin_dir / "uv"
    uv.write_text("#!/bin/bash\nprintf 'uv 0.12.0\\n'\n")
    uv.chmod(0o755)
    env.update(PATH=f"{bin_dir}:{TOOLS}:{env['PATH']}", GITHUB_WORKSPACE=str(tmp_path))
    return env


def configured(env, cwd):
    return json.loads(
        subprocess.check_output(
            [
                "bash",
                "-euo",
                "pipefail",
                "-c",
                "source rapids-init-uv; source rapids-init-uv; "
                'python -c "import json,os; print(json.dumps(dict(os.environ)))"',
            ],
            env=env,
            cwd=cwd,
            text=True,
        )
    )


@pytest.mark.parametrize("proxy", [False, True])
def test_initializer_defaults_and_idempotence(tmp_path, environment, proxy):
    if proxy:
        environment.update(
            PIP_INDEX_URL="https://pip-proxy.example/simple",
            NV_GHA_RUNNERS_PYPI_ANACONDA_CACHE_URL="https://nightly-proxy.example",
        )
    env = configured(environment, tmp_path)
    assert env["UV_INDEX_URL"] == ("https://pip-proxy.example/simple" if proxy else "https://pypi.org/simple")
    mirror = "https://nightly-proxy.example" if proxy else "https://pypi.anaconda.org"
    assert env["UV_EXTRA_INDEX_URL"] == mirror + "/rapidsai-wheels-nightly/simple"
    assert env["UV_CONSTRAINT"] == env["PIP_CONSTRAINT"]
    assert Path(env["UV_CONSTRAINT"]).is_file()
    assert env["UV_INDEX_STRATEGY"] == "unsafe-best-match"
    assert env["UV_HTTP_RETRIES"] == "10"
    assert env["UV_LINK_MODE"] == "copy"
    assert env["UV_CACHE_DIR"] == str(tmp_path / ".cache/uv")
    assert "UV_PYTHON" not in env
    assert not (tmp_path / ".cache").exists()


def test_initializer_preserves_overrides_and_constraints(tmp_path, environment):
    constraints = tmp_path / "existing constraints.txt"
    constraints.write_text("example==1\n")
    overrides = dict(
        UV_CONSTRAINT=str(constraints),
        UV_INDEX_URL="https://uv.example/simple",
        UV_EXTRA_INDEX_URL="https://uv-nightly.example/simple",
        UV_INDEX_STRATEGY="first-index",
        UV_HTTP_RETRIES="2",
        UV_LINK_MODE="hardlink",
        UV_CACHE_DIR=str(tmp_path / "custom cache"),
    )
    environment.update(overrides, PIP_CONSTRAINT=str(constraints), PIP_INDEX_URL="https://pip.example/simple")
    env = configured(environment, tmp_path)
    assert all(env[k] == v for k, v in overrides.items())
    assert env["PIP_INDEX_URL"] == environment["PIP_INDEX_URL"]
    assert constraints.read_text() == "example==1\n"


def test_pip_extra_index_and_local_cache_fallback(tmp_path, environment):
    environment.pop("GITHUB_WORKSPACE")
    environment["PIP_EXTRA_INDEX_URL"] = "https://one.example/simple https://two.example/simple"
    env = configured(environment, tmp_path)
    assert env["UV_EXTRA_INDEX_URL"] == environment["PIP_EXTRA_INDEX_URL"]
    assert env["UV_CACHE_DIR"] == str(tmp_path / ".cache/uv")


@pytest.mark.parametrize("version,success", [("0.11.9", False), ("0.12.0", True), ("0.13.6", True), ("1.0.0", True)])
def test_version_requirement(tmp_path, environment, version, success):
    uv = tmp_path / "bin/uv"
    uv.write_text(f"#!/bin/bash\necho 'uv {version}'\n")
    result = subprocess.run(["bash", "-euc", "source rapids-init-uv"], env=environment, capture_output=True, text=True)
    assert (result.returncode == 0) is success
    if not success:
        assert "requires uv>=0.12.0" in result.stderr


@pytest.mark.parametrize(
    "override", [[], ["--python", "/explicit python"], ["--python=/explicit python"], ["-p", "/explicit python"]]
)
def test_wrapper_arguments_interpreter_and_exit_status(tmp_path, environment, override):
    uv = tmp_path / "bin/uv"
    uv.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "print(json.dumps([sys.argv[1:],os.environ.get('UV_PYTHON')]))\n"
        "sys.exit(7)\n"
    )
    args = ["install", "package @ file:///a path/probe.whl", *override]
    result = subprocess.run([str(TOOLS / "rapids-uv-pip"), *args], env=environment, capture_output=True, text=True)
    assert result.returncode == 7
    actual, target = json.loads(result.stdout)
    assert actual == ["pip", *args]
    selected = subprocess.check_output(
        ["python", "-c", "import sys; print(sys.executable)"], env=environment, text=True
    ).strip()
    assert target == (None if override else selected)
    assert "UV_PYTHON" not in environment
    environment["UV_PYTHON"] = "/environment override"
    result = subprocess.run([str(TOOLS / "rapids-uv-pip"), "list"], env=environment, capture_output=True, text=True)
    assert json.loads(result.stdout)[1] == "/environment override"


@pytest.fixture
def real_uv(environment):
    uv = os.environ.get("UV_TEST_BINARY") or shutil.which("uv")
    if uv is None:
        pytest.skip("Set UV_TEST_BINARY to uv>=0.12.0 for integration checks")
    environment["PATH"] = f"{Path(uv).resolve().parent}:{TOOLS}:{environment['PATH']}"
    return environment


def wheel(directory, name, version, requires=(), console=False):
    normalized = name.replace("-", "_")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{normalized}-{version}-py3-none-any.whl"
    dist = f"{normalized}-{version}.dist-info"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    metadata += "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{normalized}.py", "def main():\n    import sys\n    print(sys.executable)\n")
        archive.writestr(f"{dist}/METADATA", metadata)
        archive.writestr(f"{dist}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr(f"{dist}/RECORD", "")
        if console:
            archive.writestr(f"{dist}/entry_points.txt", f"[console_scripts]\nuv-probe = {normalized}:main\n")
    return path


@pytest.fixture
def index(tmp_path):
    root = tmp_path / "index"
    for name, version, requires in [("root-nightly", "1.0a1", ["leaf-nightly>=1"]), ("leaf-nightly", "2.0a1", [])]:
        directory = root / name
        package = wheel(directory, name, version, requires)
        (directory / "index.html").write_text(f'<a href="{package.name}">{package.name}</a>')
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()
    server.server_close()


def run(env, *args):
    return subprocess.run(args, env=env, check=True, capture_output=True, text=True)


@pytest.mark.parametrize("explicit", [False, True])
def test_virtual_environment_console_script_and_target(tmp_path, real_uv, explicit):
    target = tmp_path / "target environment"
    run(real_uv, "uv", "venv", "--python", sys.executable, str(target))
    probe = wheel(tmp_path, "uv-probe", "1.0", console=True)
    env = dict(real_uv, UV_NO_INDEX="1")
    args = ["--python", str(target / "bin/python")] if explicit else []
    if not explicit:
        env.update(PATH=f"{target}/bin:{env['PATH']}", VIRTUAL_ENV=str(target))
    run(env, str(TOOLS / "rapids-uv-pip"), "install", *args, str(probe))
    assert run(env, str(target / "bin/uv-probe")).stdout.strip() == str(target / "bin/python")


def test_prerelease_constraints_and_warm_cache(tmp_path, real_uv, index):
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("leaf-nightly==2.0a1\n")
    env = dict(
        real_uv,
        UV_INDEX_URL=index,
        UV_EXTRA_INDEX_URL="",
        UV_CONSTRAINT=str(constraints),
        UV_CACHE_DIR=str(tmp_path / "cache"),
        UV_LINK_MODE="copy",
    )
    for number in range(2):
        target = tmp_path / f"env-{number}"
        run(env, "uv", "venv", "--python", sys.executable, str(target))
        if number:
            env["UV_OFFLINE"] = "1"
        run(env, str(TOOLS / "rapids-uv-pip"), "install", "--python", str(target / "bin/python"), "root-nightly>=0.0a0")
        assert (
            run(
                env,
                str(target / "bin/python"),
                "-c",
                "import importlib.metadata as m; print(m.version('leaf-nightly'))",
            ).stdout.strip()
            == "2.0a1"
        )
    run(env, "uv", "cache", "clean")
    assert not (tmp_path / "cache").exists()


def test_no_cache_and_isolated_build(tmp_path, real_uv, index):
    target = tmp_path / "environment"
    run(real_uv, "uv", "venv", "--python", sys.executable, str(target))
    env = dict(real_uv, UV_CACHE_DIR=str(tmp_path / "no-persistent-cache"), UV_NO_INDEX="1")
    run(
        env,
        str(TOOLS / "rapids-uv-pip"),
        "install",
        "--no-cache",
        "--python",
        str(target / "bin/python"),
        str(wheel(tmp_path, "uv-probe", "1.0")),
    )
    assert not (tmp_path / "no-persistent-cache").exists()
    pytest.importorskip("build")
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=["root-nightly>=0.0a0"]\nbuild-backend="backend"\nbackend-path=["."]\n'
    )
    (project / "backend.py").write_text(
        "import importlib.metadata, shutil\n"
        "def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):\n"
        "    assert importlib.metadata.version('leaf-nightly') == '2.0a1'\n"
        f"    return shutil.copy({str(wheel(tmp_path, 'built-probe', '1.0'))!r}, wheel_directory).rsplit('/', 1)[-1]\n"
    )
    constraints = tmp_path / "build-constraints.txt"
    constraints.write_text("leaf-nightly==2.0a1\n")
    build_env = dict(
        real_uv,
        UV_INDEX_URL=index,
        UV_EXTRA_INDEX_URL="",
        UV_CACHE_DIR=str(tmp_path / "build-cache"),
        UV_PYTHON_DOWNLOADS="never",
    )
    run(
        build_env,
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--installer",
        "uv",
        "--outdir",
        str(tmp_path / "dist"),
        "--dependency-constraints-txt",
        str(constraints),
        str(project),
    )
    assert list((tmp_path / "dist").glob("built_probe-1.0-*.whl"))


def test_explicit_target_does_not_require_current_python(tmp_path, environment):
    python = tmp_path / "bin/python"
    python.unlink()
    python.write_text("#!/bin/bash\nexit 99\n")
    python.chmod(0o755)
    assert (
        subprocess.run([str(TOOLS / "rapids-uv-pip"), "list", "--python", "/explicit"], env=environment).returncode == 0
    )


def test_missing_uv_reports_requirement(tmp_path, environment):
    (tmp_path / "bin/uv").unlink()
    environment["PATH"] = f"{tmp_path}/bin:{TOOLS}:/usr/bin:/bin"
    result = subprocess.run(["bash", "-euc", "source rapids-init-uv"], env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert "requires uv>=0.12.0" in result.stderr
