# gha-tools

User tools for use in RAPIDS GitHub Actions workflows.

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

In gha-tools we introduced some variable naming conventions:
* Environment variables should be capitalized, local variables should be lower-case
* RAPIDS-specific environment variables should be named `RAPIDS_*`
    * This distinguishes them from external environment variables e.g. `GITHUB_*` that are defined by GitHub Actions

List of variables that have had a `RAPIDS_*` prefix added, which should be reflected by consumers switching from gpuci-tools to gha-tools:
* `CONDA_EXE`, `CONDA_TOKEN`, `CONDA_UPLOAD_LABEL` -> `RAPIDS_CONDA_EXE`, `RAPIDS_CONDA_TOKEN`, `RAPIDS_CONDA_UPLOAD_LABEL`
* `MAMBA_BIN` -> `RAPIDS_MAMBA_BIN`
* `PY_VER` -> `RAPIDS_PY_VER`
* `BUILD_TYPE` -> `RAPIDS_BUILD_TYPE`
* `GH_TOKEN` -> `RAPIDS_GH_TOKEN`

In GitHub Actions, the [default secret GITHUB_TOKEN](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow) can be used by setting:
```
env:
  RAPIDS_GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### gpuci deprecation

This repo replaces [rapidsai/gpuci-tools](https://github.com/rapidsai/gpuci-tools). All scripts called `gpuci_*`, configured with `GPUCI_*` env vars, are now called `rapids-*` with the equivalent `RAPIDS_*` env vars

The `gpuci_*` tools in this project are wrappers around the new tools for backwards compatibility:
1. They print a deprecation warning to use the `rapids-*` equivalents
2. They re-export `GPUCI_*` env vars to the new `RAPIDS_*` equivalents

### S3 tools for downloads.rapids.ai

Some enhancements have been made to the S3 tools for interacting with [downloads.rapids.ai](https://github.com/rapidsai/downloads):
* Added support for uploading and downloading wheel tarballs (built with cibuildwheel) using `rapids-upload-wheels-to-s3` and `rapids-download-wheels-from-s3`
* Added support for misc one-off file or directory uploads by calling `rapids-upload-to-s3` directly
* Print the human-browsable `https://downloads.rapids.ai/...` URL in the logs for convenience
* `rapids-package-name` takes a package type and generates the name (e.g. `conda_cpp` -> `rmm_conda_cpp_x86_64.tar.gz`)
