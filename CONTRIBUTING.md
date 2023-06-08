# Contributing

## Testing Scripts Locally

Before opening a pull-request, it is recommended to test all changes locally.

The command below is a quick way to set up a disposable test environment for the `gha-tools` repository:

```sh
docker run \
  --pull=always \
  --rm -it \
  --gpus all \
  -v $HOME/.aws:/root/.aws:ro \
  -v /home/user/gha-tools/tools:/root/.local/bin:ro \
  -v $PWD:/work \
  -w /work \
  rapidsai/ci:latest
```

This command makes the following assumptions:

- The `gha-tools` repository is checked out to `/home/user/gha-tools`
- The current working directory is a RAPIDS repository that has artifacts on [downloads.rapids.ai](https://downloads.rapids.ai) (NVIDIA VPN connectivity is required to access this site), like `cugraph`.
  - This is important for testing how changes to artifact download scripts will affect local invocations (see note below)
- The AWS credentials in `/home/user/.aws` have access to the `rapids-downloads` bucket
  - This is important for testing how changes to artifact download scripts will affect CI (see note below)

> **Note:** CI interacts with S3 directly, whereas local `gha-tools` script invocations get artifacts through [downloads.rapids.ai](https://downloads.rapids.ai).

Once the container above is running, change the `PATH` variable inside of it so that the scripts in the volume mounted `gha-tools` directory take precedence:

```sh
export PATH=/root/.local/bin:$PATH
```

Now, the volume mounted scripts will be run any time a `gha-tools` script is invoked.

Any changes made to the scripts on the host machine will be reflected in the container.

Here is an example test workflow:

```sh
# Set up environment variables for `gha-tools` scripts below
export RAPIDS_BUILD_TYPE=branch
export RAPIDS_REPOSITORY=rapidsai/cugraph
export RAPIDS_REF_NAME=branch-23.08
export RAPIDS_SHA=3f66966ec6beb678d531ec01713292e67ca1b290

# Test how the scripts will work in CI
# These invocations will interact with S3 directly and therefore use the AWS credentials that were volume mounted in
export CI=true
rapids-download-conda-from-s3 python
rapids-get-artifact ci/cugraph/branch/branch-23.08/3f66966/cugraph_conda_python_cuda11_310_aarch64.tar.gz

# Test how the scripts will work locally
export CI=false
rapids-download-conda-from-s3 python
rapids-get-artifact ci/cugraph/branch/branch-23.08/3f66966/cugraph_conda_python_cuda11_310_aarch64.tar.gz
```

Since the current working directory is a standard RAPIDS repository, the CI scripts can also be run directly to test the changes:

```sh
./ci/test_python.sh
```
