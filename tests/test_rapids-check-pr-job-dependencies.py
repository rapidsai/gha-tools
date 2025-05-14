import os.path
import subprocess
from textwrap import dedent

import pytest

TOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tools")


@pytest.mark.parametrize(
    ["contents", "ignored_jobs", "output", "exit_code"],
    [
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                    job1:
                    job2:
                """
            ),
            None,
            "pr-builder depends on all other jobs.\n",
            0,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                    job1:
                    job2:
                """
            ),
            [],
            "pr-builder depends on all other jobs.\n",
            0,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                    job1:
                    job2:
                    job3:
                """
            ),
            ["job3"],
            "pr-builder depends on all other jobs.\n",
            0,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                    job1:
                    job2:
                    job3:
                """
            ),
            None,
            dedent(
                """\
                'pr-builder' job is missing the following dependent jobs:
                  - job3

                Update '{filename}' to include these missing jobs for 'pr-builder'.
                Alternatively, you may ignore these jobs by passing them as an argument to this script.
                """
            ),
            1,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                        if: true
                    job1:
                    job2:
                """
            ),
            None,
            dedent(
                """\
                If 'pr-builder' job has an 'if' condition, it must be set to 'always()'.

                Update '{filename}' to set the correct 'if' condition.
                """
            ),
            1,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                        if: always()
                    job1:
                    job2:
                """
            ),
            None,
            dedent(
                """\
                If 'pr-builder' job has an 'if' condition, it must also set the 'needs' input to '${{{{ toJSON(needs) }}}}'.

                Update '{filename}' to add the following:

                with:
                  needs: ${{{{ toJSON(needs) }}}}
                """
            ),
            1,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                        if: always()
                        with:
                    job1:
                    job2:
                """
            ),
            None,
            dedent(
                """\
                If 'pr-builder' job has an 'if' condition, it must also set the 'needs' input to '${{{{ toJSON(needs) }}}}'.

                Update '{filename}' to add the following:

                with:
                  needs: ${{{{ toJSON(needs) }}}}
                """
            ),
            1,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                        if: always()
                        with:
                            needs: invalid
                    job1:
                    job2:
                """
            ),
            None,
            dedent(
                """\
                If 'pr-builder' job has an 'if' condition, it must also set the 'needs' input to '${{{{ toJSON(needs) }}}}'.

                Update '{filename}' to add the following:

                with:
                  needs: ${{{{ toJSON(needs) }}}}
                """
            ),
            1,
        ),
        (
            dedent(
                """\
                jobs:
                    pr-builder:
                        needs:
                            - job1
                            - job2
                        if: always()
                        with:
                            needs: ${{ toJSON(needs) }}
                    job1:
                    job2:
                """
            ),
            None,
            "pr-builder depends on all other jobs.\n",
            0,
        ),
    ],
)
def test_rapids_check_pr_job_dependencies(
    tmp_path: os.PathLike,
    contents: str,
    ignored_jobs: list[str],
    output: str,
    exit_code: int,
):
    filename = os.path.join(tmp_path, "pr.yaml")
    with open(filename, "w") as f:
        f.write(contents)
    result = subprocess.run(
        [
            os.path.join(TOOLS_DIR, "rapids-check-pr-job-dependencies"),
            *([] if ignored_jobs is None else [" ".join(ignored_jobs)]),
        ],
        env={
            **os.environ,
            "WORKFLOW_FILE": filename,
        },
        text=True,
        capture_output=True,
    )
    assert result.stdout == output.format(filename=filename)
    assert result.stderr == ""
    assert result.returncode == exit_code
