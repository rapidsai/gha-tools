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
* `rapids-upload-to-anaconda-github`: downloads conda packages from GitHub Actions artifact store and uploads conda channels on anaconda.org
* `rapids-wheels-anaconda-github`: downloads wheels from GitHub Actions artifact store and uploads them to the RAPIDS nightly index at https://pypi.anaconda.org/rapidsai-wheels-nightly/simple/
* `rapids-package-name`: takes a package type and generate the artifact name (e.g. `conda_cpp` -> `rmm_conda_cpp_x86_64.tar.gz`)

It also contains some scripts for working with CI artifacts on `downloads.rapids.ai`.

* `rapids-upload-to-s3`: upload arbitrary files to the `downloads.rapids.ai` S3 bucket

For more details, see the RAPIDS maintain docs:

* "GitHub Actions" ([link](https://docs.rapids.ai/resources/github-actions/))
* "Reproducing CI Locally" ([link](https://docs.rapids.ai/resources/reproducing-ci/))

#### (deprecated) Storing conda packages and wheels on `downloads.rapids.ai`

Support for storing conda packages and wheels on `downloads.rapids.ai` is considered **deprecated**.
Switch those workloads to using the the GitHub Actions artifact store.
But for backwards-compatibility, this project still contains some tools for doing that:

* `rapids-download-{conda,wheels}-from-s3`: download conda packages and wheels from the `downloads.rapids.ai` S3 bucket
* `rapids-upload-{conda,wheels}-to-s3`: upload conda packages and wheels to the `downloads.rapids.ai` S3 bucket

### Testing Scripts Locally

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to test these scripts locally.
