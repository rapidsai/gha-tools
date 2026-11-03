# gha-tools

User tools for RAPIDS GitHub Actions workflows.

### Install gha-tools

This tools repo can be installed from GitHub directly with git clone or wget commands. Examples:
```yml
- name: Download gha-tools with git clone
  run: |
    git clone https://github.com/rapidsai/gha-tools.git -b main /tmp/gha-tools
    echo "/tmp/gha-tools/tools" >> "${GITHUB_PATH}"

- name: Download gha-tools release tarball with wget
  run: |
    wget https://github.com/rapidsai/gha-tools/releases/latest/download/tools.tar.gz -O - | tar -xz -C /usr/local/bin
```

### Environment variables and variable naming conventions

Scripts here get much of their configuration from environment variables.

Those tend to follow these conventions:

* Environment variables should be capitalized, local variables should be lower-case
* RAPIDS-specific environment variables should be named `RAPIDS_*`
    * This distinguishes them from external environment variables e.g. `GITHUB_*` that are defined by GitHub Actions

In GitHub Actions, the [default secret GITHUB_TOKEN](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow) can be used by setting:

```yaml
env:
  RAPIDS_GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Managing CI artifacts

This project contains some scripts for managing CI artifacts.

* `rapids-download-{conda,wheels}-from-github`: download conda packages and wheels from the GitHub Actions artifact store
* `rapids-get-pr-artifact`: downloads conda packages or wheels produced by pull rquest CI in another repo
* `rapids-upload-to-anaconda-github`: downloads conda packages from GitHub Actions artifact store and uploads conda channels on anaconda.org
* `rapids-wheels-anaconda-github`: downloads wheels from GitHub Actions artifact store and uploads them to the RAPIDS nightly index at https://pypi.anaconda.org/rapidsai-wheels-nightly/simple/
* `rapids-artifact-name`: takes a package type and generates an artifact name (e.g. `conda_cpp librmm rmm --cuda 12.8` -> `rmm_conda_cpp_librmm_amd64_cu12`)

It also contains some scripts for working with CI artifacts on `downloads.rapids.ai`.

* `rapids-upload-to-s3`: upload arbitrary files to the `downloads.rapids.ai` S3 bucket

For more details, see the RAPIDS maintain docs:

* "GitHub Actions" ([link](https://docs.rapids.ai/resources/github-actions/))
* "Reproducing CI Locally" ([link](https://docs.rapids.ai/resources/reproducing-ci/))

### Testing Scripts Locally

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to test these scripts locally.

### Opting in to uv

Wheel CI images provide standalone uv (minimum 0.12.0 for RAPIDS nightly prereleases).
Existing pip helpers and installer defaults are unchanged. For an opt-in job:

```sh
source rapids-init-uv
rapids-uv-pip install -r requirements.txt
rapids-python-build-retry --wheel --installer uv .
```

`rapids-init-uv` configures uv without downloading it. Missing or older uv fails with
an actionable message. Explicit `UV_*` settings take precedence; otherwise the
initializer maps `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`, and the runner's nightly
proxy to uv, with the public PyPI and RAPIDS nightly indexes as fallbacks. It uses
`unsafe-best-match` to preserve version selection across indexes, ten HTTP retries,
and copy linking. It does not translate arbitrary `pip.conf` settings or pip flags.

The initializer uses the same constraint-file convention as `rapids-init-pip`, and defaults
`UV_CONSTRAINT` to that same file, without changing pip configuration. Existing generators and local-wheel references
continue working. An explicit `UV_CONSTRAINT` is preserved. For isolated wheel
builds, pass build dependency constraints explicitly and unset installer constraint
variables in a subshell when they should not apply to the frontend.

`rapids-uv-pip` passes arguments to `uv pip`, defaults to the current Python's
`sys.executable` on each invocation, and honors `--python`/`-p` or `UV_PYTHON`.
Its interpreter selection stays in the child process; it does not pin the Python
used by later isolated builds. Activated virtual environments work through their
selected `python`. After installing console scripts into pyenv, callers must run
`pyenv rehash` before invoking the new commands. No helper rehashes automatically.

uv performs HTTP retries natively. The helper forwards failures without retrying
entire builds or dependency-resolution failures, and does not emulate pip's
specialized hash-mismatch retry logic.

The default cache is `${GITHUB_WORKSPACE:-${PWD}}/.cache/uv`, shared by installations
within the job. Set `UV_CACHE_DIR` to override it. No cross-job cache restoration is
configured here. `--no-cache` uses a temporary cache for one invocation; use
`uv cache clean` to remove persistent uv cache contents after all consumers finish.
This does not replace `pip cache purge`, which cleans pip's separate cache.
