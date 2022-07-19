# gha-tools

CI/CD tools and scripts for use in GitHub Actions workflows for the RAPIDS organization.

This repo builds from, and intends to replace, the existing [rapidsai/gpuci-tools](https://github.com/rapidsai/gpuci-tools) repo, with some changes to reflect new GitHub Actions CI directions for RAPIDS projects.

### Install gha-tools

Files related to packaging the tools repo itself as a conda package have been removed. It can be installed from GitHub directly with git clone or wget commands.

Example of GitHub Actions syntax to install and set up `gha-tools`:
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

Diverging from gpuci-tools, in gha-tools we want to start prepending `RAPIDS_*` to our own RAPIDS-specific environment variables, to distinguish them from external environment variables such as `GITHUB_*` ones that are set by GHA (GitHub Actions):

* `BUILD_TYPE` -> `RAPIDS_BUILD_TYPE`
* `PY_VER` -> `RAPIDS_PY_VER`
* `GH_TOKEN` -> `RAPIDS_GH_TOKEN`

In GitHub Actions, the [default secret GITHUB_TOKEN](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow) can be used by setting:
```
env:
  RAPIDS_GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Exceptions are:
1. The variable `MAMBA_BIN`, which remain as-is to maintain backwards-compatiblity
2. Variables named `GPUCI_*`, which are re-exported to their `RAPIDS_*` equivalents during the gpuci deprecation
3. Variables named `CONDA_*`, which already have a prefix indicating their functional purpose

Variables local to the script should be in lowercase to not mix them up with environment variables (although it's still legal shell syntax).

### gpuci deprecation

All scripts called `gpuci_*`, configured with `GPUCI_*` env vars, are now called `rapids-*` with the equivalent `RAPIDS_*` env vars

The `gpuci_*` tools in this project are wrappers around the new tools for backwards compatibility:
1. They print a deprecation warning to use the `rapids-*` equivalents
2. They re-export `GPUCI_*` env vars to the new `RAPIDS_*` equivalents

#### rapids-mamba-retry

This tool has been refactored to call `rapids-conda-retry` with `CONDA_EXE=mamba`.

The `--mamba*` command-line options and `MAMBA*` env vars are re-exported to their `--conda*` and `CONDA*` counterparts respectively.

### S3 tools for downloads.rapids.ai

Some enhancements have been made to the S3 tools for interacting with [downloads.rapids.ai](https://github.com/rapidsai/downloads):
* Added support for uploading and downloading wheel tarballs (built with cibuildwheel) using `rapids-upload-wheels-to-s3` and `rapids-download-wheels-from-s3`
* Added support for misc one-off file uploads (**not directory! single files only**) by calling `rapids-upload-to-s3` directly
* Print the human-browsable `https://downloads.rapids.ai/...` URL in the logs for convenience
* `rapids-package-name` takes a package type and generates the name (e.g. `conda_cpp` -> `rmm_conda_cpp_x86_64.tar.gz`)
