# Contributing

## Testing Locally

Before opening a pull request, it is recommended to test all changes locally.

The command below is a quick way to set up a disposable test environment for the `gha-tools` repository:

```sh
docker run \
  --pull=always \
  --rm \
  --gpus all \
  -v "${HOME}/repos/gha-tools/tools":/usr/local/bin/gha-tools:ro \
  -v $PWD:/work \
  -w /work \
  -it rapidsai/ci-conda:latest
```

This command makes the following assumptions:

- The `gha-tools` repository is checked out to `${HOME}/repos/gha-tools`
- The current working directory is a RAPIDS repository that publishes CI artifacts, like `cugraph`.
  - This is important for testing how changes to artifact download scripts will affect local invocations (see note below)

Once the container above is running, change the `PATH` variable inside of it so that the scripts in the volume mounted `gha-tools` directory take precedence:

```sh
export PATH="/usr/local/binn/gha-tools/tools:${PATH}"
```

Now, the volume mounted scripts will be run any time a `gha-tools` script is invoked.

Any changes made to the scripts on the host machine will be reflected in the container.

Here is an example test workflow:

```sh
# Set up environment variables for `gha-tools` scripts below
export RAPIDS_BUILD_TYPE=branch
export RAPIDS_REPOSITORY=rapidsai/cugraph
export RAPIDS_REF_NAME=branch-25.06

# latest commit on that branch
export RAPIDS_SHA="$(git ls-remote https://github.com/${RAPIDS_REPOSITORY}.git refs/heads/${RAPIDS_REF_NAME} | awk '{print $1}')"

# Test how the scripts will work in CI
export CI=true
rapids-download-conda-from-github python

# Test how the scripts will work locally
export CI=false
rapids-download-conda-from-github python
```

For more details on how to extend this to fully reproducing CI locally, see "Reproducing CI Locally" ([link](https://docs.rapids.ai/resources/reproducing-ci/)).

## Testing in CI

The tools here are all executable, so testing an alternative branch just requires downloading
the files and putting the `tools/` directory on `PATH`.

For example, create a script called `use_gha_tools_from_branch.sh` in the following in the project's `ci/` directory.

```shell
#!/bin/bash

# fill these in
GHA_TOOLS_BRANCH=
GHA_TOOLS_REPO_ORG=

git clone \
  --branch ${GHA_TOOLS_BRANCH} \
  https://github.com/${GHA_TOOLS_REPO_ORG}/gha-tools.git \
  /tmp/gha-tools

unset GHA_TOOLS_BRANCH GHA_TOOLS_REPO_ORG

export PATH="/tmp/gha-tools/tools":$PATH
```

Source that script in all the `ci/` scripts.

```shell
source ./ci/use_gha_tools_from_branch.sh
```
