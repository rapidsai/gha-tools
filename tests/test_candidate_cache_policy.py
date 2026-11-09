# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Candidate cache policy must survive inherited compiler settings."""

import os
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


@pytest.mark.parametrize("policy", [None, "true", "false"])
def test_helper_configures_caching_only_when_allowed(tmp_path, policy):
    configure_dist = tmp_path / "rapids-configure-sccache-dist"
    configure_dist.write_text('touch "${DIST_MARKER}"\n')
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}:{TOOLS}:{os.environ['PATH']}",
        "DIST_MARKER": str(tmp_path / "dist-called"),
        "SCCACHE_DIST_AUTH_TOKEN": "fixture-token",
        "CMAKE_C_COMPILER_LAUNCHER": "inherited-cache",
        "CMAKE_CXX_COMPILER_LAUNCHER": "inherited-cache",
        "CMAKE_CUDA_COMPILER_LAUNCHER": "inherited-cache",
        "RUSTC_WRAPPER": "inherited-cache",
        "PARALLEL_LEVEL": "2",
        "CI": "true",
    }
    environment.pop("RAPIDS_RELEASE_CANDIDATE_SCCACHE", None)
    if policy is not None:
        environment["RAPIDS_RELEASE_CANDIDATE_SCCACHE"] = policy
    result = subprocess.run(
        [
            "bash",
            "-c",
            'set -eu; source "$1"; printf "%s\\n" "${RUSTC_WRAPPER-unset}" '
            '"${CMAKE_C_COMPILER_LAUNCHER}" "${CMAKE_CXX_COMPILER_LAUNCHER}" '
            '"${CMAKE_CUDA_COMPILER_LAUNCHER}" "${PARALLEL_LEVEL}" "${SCCACHE_S3_NO_CREDENTIALS-unset}"',
            "fixture",
            str(TOOLS / "rapids-configure-sccache"),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    exported = dict(
        zip(
            [
                "RUSTC_WRAPPER",
                "CMAKE_C_COMPILER_LAUNCHER",
                "CMAKE_CXX_COMPILER_LAUNCHER",
                "CMAKE_CUDA_COMPILER_LAUNCHER",
                "PARALLEL_LEVEL",
                "SCCACHE_S3_NO_CREDENTIALS",
            ],
            result.stdout.splitlines(),
            strict=True,
        )
    )
    assert exported["PARALLEL_LEVEL"] == "2"
    if policy == "false":
        assert not (tmp_path / "dist-called").exists()
        assert exported["RUSTC_WRAPPER"] == "unset"
        for language in ("C", "CXX", "CUDA"):
            assert exported[f"CMAKE_{language}_COMPILER_LAUNCHER"] == ""
    else:
        assert (tmp_path / "dist-called").exists()
        assert exported["RUSTC_WRAPPER"] == "sccache"
        for language in ("C", "CXX", "CUDA"):
            assert exported[f"CMAKE_{language}_COMPILER_LAUNCHER"] == "sccache"
        assert exported["SCCACHE_S3_NO_CREDENTIALS"] == "false"
