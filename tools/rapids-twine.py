#!/usr/bin/env python3
# A utility script that uploads wheels to pip indexes with twine to support build numbers on conflict
# See:
#   - https://stackoverflow.com/a/63944201
#   - https://peps.python.org/pep-0427/, section on 'build tag'
#
# Positional Arguments:
#   1) directory containing wheels

import subprocess
import os
import sys
import shutil
import tempfile
from setuptools.extern import packaging

echo_prefix="    [rapids-twine.py] "
rapids_echo_stderr_fn=lambda x: print(x, file=sys.stderr)
twine_upload_args = ["--disable-progress-bar", "--non-interactive"]


def _twine_upload(wheel):
    print(f"{echo_prefix}Working on {wheel=}")
    twine_out = subprocess.run(
        ["twine", "upload", *twine_upload_args, wheel],
        capture_output=True
    )
    retcode, stdout = twine_out.returncode, twine_out.stdout

    print(f"{echo_prefix}Twine output: '{stdout}'")
    return retcode == 0


if __name__ == '__main__':
    wheel_dir = None
    try:
        wheel_dir = sys.argv[1]
    except IndexError:
        rapids_echo_stderr_fn(f"{echo_prefix}Must specify input argument: WHEEL_DIR")
        sys.exit(1)

    if not os.path.isdir(wheel_dir):
        rapids_echo_stderr_fn(f"{echo_prefix}Path '{wheel_dir}' is not a directory")

    wheel_base_version = os.environ["RAPIDS_PY_WHEEL_VERSIONEER_OVERRIDE"]
    build_tag = os.getenv("RAPIDS_PY_WHEEL_BUILD_TAG", default="")

    # replace override with pypi-normalized string e.g. 22.10.00a --> 22.10.0a0
    wheel_base_version_normalized = str(packaging.version.Version(wheel_base_version))

    rapids_echo_stderr_fn(f"{echo_prefix}Normalizing '{wheel_base_version}' to '{wheel_base_version_normalized} to match setuptools...")
    wheel_base_version = wheel_base_version_normalized

    for wheel_file_name in os.listdir(wheel_dir):
        wheel_file_path = os.path.join(wheel_dir, wheel_file_name)

        if build_tag == '':
            success = _twine_upload(wheel_file_path)
            if success:
                continue
            else:
                sys.exit(1)
        else:
            rapids_echo_stderr_fn(f"{echo_prefix}Using specified build tag '{build_tag}'")
            wheel_next_version = f"{wheel_base_version}-{build_tag}"

            # copy original wheels to a tempdir
            with tempfile.TemporaryDirectory() as tempdir:
                rapids_echo_stderr_fn(f"{echo_prefix}Replacing '{wheel_base_version}' with '{wheel_next_version}'")
                wheel_next_file_name = wheel_file_name.replace(wheel_base_version, wheel_next_version)
                wheel_next_file_path = os.path.join(tempdir, wheel_next_file_name)

                rapids_echo_stderr_fn(f"{echo_prefix}Copying {wheel_file_path} to {wheel_next_file_path}")
                shutil.copy(wheel_file_path, wheel_next_file_path)

                next_success = _twine_upload(wheel_next_file_path)
                if next_success:
                    continue
                else:
                    sys.exit(1)
