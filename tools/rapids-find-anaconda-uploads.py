#!/usr/bin/env python3
# shellcheck disable=all

import glob
import sys
from os import environ, path

"""
Script that finds all Anaconda packages that should be uploaded to Anaconda.org
within a given directory.

Positional Arguments:
  1: relative or absolute path to search for packages
  Examples:
    "/tmp/cpp_channel/", "cpp_channel", "."

Environment Variables:
  SKIP_UPLOAD_PKGS: space delimited strings of package names that should
             not be uploaded to Anaconda.org
  Example:
    export SKIP_UPLOAD_PKGS="some-private-pkg another-private-pkg"
"""


def get_pkg_name_from_filename(filename):
    """
    Returns the package name associated with a given filename.
    """
    return "-".join(filename.split("-")[:-2])


def is_skip_pkg(pkg_name):
    """
    Returns true if the package name is in the "SKIP_UPLOAD_PKGS"
    environment variable.
    """
    skip_pkgs_var = environ.get("SKIP_UPLOAD_PKGS", "")
    pkgs_to_skip = skip_pkgs_var.split(" ")
    return pkg_name in pkgs_to_skip


def file_filter_fn(file_path):
    """
    Filters out packages that shouldn't be uploaded to Anaconda.org
    """
    filename = path.basename(file_path)
    pkg_name = get_pkg_name_from_filename(filename)

    if is_skip_pkg(pkg_name):
        return False

    return True


if __name__ == "__main__":
    directory_to_search = sys.argv[1]
    conda_pkgs = (
        glob.glob(f"{directory_to_search}/**/*.conda", recursive=True) +
        glob.glob(f"{directory_to_search}/**/*.tar.bz2", recursive=True)
    )

    filtered_list = list(filter(file_filter_fn, conda_pkgs))
    print("\n".join(filtered_list))
