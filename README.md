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

### Using uv

Requires uv >=0.12.0, installed separately. Opt in with:

```sh
source rapids-init-uv
rapids-uv-pip install -r requirements.txt
rapids-python-build-retry --wheel --installer uv .
```

* `rapids-init-uv`: configures RAPIDS indexes from pip/proxy settings and defaults `UV_CONSTRAINT` to `PIP_CONSTRAINT` when supplied. Explicit `UV_*` settings take precedence.
* `rapids-uv-pip`: runs `uv pip` with the current Python, honoring `--python`/`-p` and `UV_PYTHON` without setting the interpreter for later isolated builds.

`UV_CACHE_DIR` defaults to `${GITHUB_WORKSPACE:-${PWD}}/.cache/uv`; use `uv cache clean` to clear it.
Call `pyenv rehash` after installing console scripts into pyenv.
