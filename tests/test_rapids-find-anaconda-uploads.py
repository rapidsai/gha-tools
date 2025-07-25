import importlib
import sys
from os import environ, path
from unittest import mock

import pytest

tools_dir = path.join(path.dirname(path.realpath(__file__)), "..", "tools")
sys.path.insert(0, tools_dir)

# import module w/ invalid characters (hyphens)
mod = importlib.import_module("rapids-find-anaconda-uploads")


@pytest.mark.parametrize(
    "filename, pkg_name",
    [
        (
            "custreamz-23.02.00a230103-py312_g1deec38683_209.tar.bz2",
            "custreamz",
        ),
        (
            "strings_udf-23.02.00a230103-cuda_12_py312_g1deec38683_209.tar.bz2",
            "strings_udf",
        ),
        (
            "dask-cudf-23.02.00a230103-cuda_12_py312_g1deec38683_209.tar.bz2",
            "dask-cudf",
        ),
        (
            "some-random-long-pkg-name-23.02.00a230103-cuda_12_py312_g1deec38683_209.tar.bz2",
            "some-random-long-pkg-name",
        ),
    ],
)
def test_get_pkg_name_from_filename(filename, pkg_name):
    assert mod.get_pkg_name_from_filename(filename) == pkg_name


@pytest.mark.parametrize(
    "env_var, pkg_name, result",
    [
        ("", "custreamz", False),
        ("libcudf-example cuml", "strings_udf", False),
        ("cudf dask-cuda ", "dask-cudf", False),
        ("libcudf-tests some-other-pkg", "libcudf-tests", True),
        ("some-pkg-private", "some-pkg-private", True),
        ("", "some-pkg-private", False),
        ("some-pkg", "some-pkg-private", False),
        ("some-pkg-private", "some-pkg", False),
    ],
)
def test_is_skip_pkg(env_var, pkg_name, result):
    with mock.patch.dict(environ, {"SKIP_UPLOAD_PKGS": env_var}):
        assert mod.is_skip_pkg(pkg_name) == result


TEST_FILES = [
    "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-private-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-private-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-tests-23.02.00a-cuda12_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-tests-23.02.00a-cuda12_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
]


def test_file_filter_fn():
    file_filter_fn = mod.file_filter_fn

    # w/ env var
    with mock.patch.dict(environ, {"SKIP_UPLOAD_PKGS": "some-pkg-private libcudf-tests"}):
        filtered_list = list(filter(file_filter_fn, TEST_FILES))
        assert filtered_list == [
            "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
        ]

    # w/ empty env var
    with mock.patch.dict(environ, {"SKIP_UPLOAD_PKGS": ""}):
        filtered_list = list(filter(file_filter_fn, TEST_FILES))
        assert filtered_list == [
            "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-private-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-private-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-tests-23.02.00a-cuda12_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-tests-23.02.00a-cuda12_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
        ]

    # w/ no env var
    filtered_list = list(filter(file_filter_fn, TEST_FILES))
    assert filtered_list == [
        "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-private-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_39_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-private-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_38_x86_64/linux-64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py312_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda12_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda12_py313_g10bab945_72.tar.bz2",
        "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-tests-23.02.00a-cuda12_g10bab945_72.tar.bz2",
        "./cudf_conda_cpp_cuda12_aarch64/linux-aarch64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
        "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-tests-23.02.00a-cuda12_g10bab945_72.tar.bz2",
        "./cudf_conda_cpp_cuda12_x86_64/linux-64/libcudf-23.02.00a-cuda12_g10bab945_72.tar.bz2",
    ]
