import sys
from os import environ, path
import importlib
import pytest
from unittest import mock

tools_dir = path.join(path.dirname(path.realpath(__file__)), "..", "tools")
sys.path.insert(0, tools_dir)

# import module w/ invalid characters (hyphens)
mod = importlib.import_module("rapids-find-anaconda-uploads")


@pytest.mark.parametrize(
    "filename, pkg_name",
    [
        (
            "custreamz-23.02.00a230103-py39_g1deec38683_209.tar.bz2",
            "custreamz",
        ),
        (
            "strings_udf-23.02.00a230103-cuda_11_py39_g1deec38683_209.tar.bz2",
            "strings_udf",
        ),
        (
            "dask-cudf-23.02.00a230103-cuda_11_py39_g1deec38683_209.tar.bz2",
            "dask-cudf",
        ),
        (
            "some-random-long-pkg-name-23.02.00a230103-cuda_11_py39_g1deec38683_209.tar.bz2",
            "some-random-long-pkg-name",
        ),
    ],
)
def test_get_pkg_name_from_filename(filename, pkg_name):
    assert mod.get_pkg_name_from_filename(filename) == pkg_name


@pytest.mark.parametrize(
    "pkg_name, result",
    [
        ("custreamz", False),
        ("strings_udf", False),
        ("dask-cudf", False),
        ("", False),
        ("libcudf-tests", True),
    ],
)
def test_is_test_pkg(pkg_name, result):
    assert mod.is_test_pkg(pkg_name) == result


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
    "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-private-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-private-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
    "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda11_aarch64/linux-aarch64/libcudf-tests-23.02.00a-cuda11_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda11_aarch64/linux-aarch64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda11_x86_64/linux-64/libcudf-tests-23.02.00a-cuda11_g10bab945_72.tar.bz2",
    "./cudf_conda_cpp_cuda11_x86_64/linux-64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
]


def test_file_filter_fn():
    file_filter_fn = mod.file_filter_fn

    # w/ env var
    with mock.patch.dict(
        environ, {"SKIP_UPLOAD_PKGS": "some-pkg-private libcudf-tests"}
    ):
        filtered_list = list(filter(file_filter_fn, TEST_FILES))
        assert filtered_list == [
            "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda11_aarch64/linux-aarch64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda11_x86_64/linux-64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
        ]

    # w/ empty env var
    with mock.patch.dict(environ, {"SKIP_UPLOAD_PKGS": ""}):
        filtered_list = list(filter(file_filter_fn, TEST_FILES))
        assert filtered_list == [
            "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-private-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-private-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
            "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda11_aarch64/linux-aarch64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
            "./cudf_conda_cpp_cuda11_x86_64/linux-64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
        ]

    # w/ no env var
    filtered_list = list(filter(file_filter_fn, TEST_FILES))
    assert filtered_list == [
        "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-private-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_39_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-private-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_38_x86_64/linux-64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_39_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py39_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-private-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
        "./cudf_conda_python_cuda11_38_aarch64/linux-aarch64/some-pkg-23.02.00a-cuda11_py38_g10bab945_72.tar.bz2",
        "./cudf_conda_cpp_cuda11_aarch64/linux-aarch64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
        "./cudf_conda_cpp_cuda11_x86_64/linux-64/libcudf-23.02.00a-cuda11_g10bab945_72.tar.bz2",
    ]
