# Security Policy

`gha-tools` is a collection of shell and Python utilities used by RAPIDS
GitHub Actions workflows. The tools live under `tools/` and are added to
the runner's `PATH`; downstream workflows call them to install sccache,
download / upload CI artifacts (GitHub Artifacts, S3, anaconda.org),
retry conda / pip / generic commands, generate versions, emit telemetry,
and similar build-plumbing tasks.

Because gha-tools runs inside CI workflows with access to repository
secrets (GitHub tokens, AWS credentials, anaconda upload tokens), its
security posture is dominated by how those secrets are passed in,
logged, and propagated to network operations — and by the supply chain
through which gha-tools itself is delivered to consumer workflows.

## Reporting a Vulnerability

Please report security vulnerabilities privately through one of the channels
below. **Do not open a public GitHub issue, PR, or discussion** for a
suspected vulnerability.

1. **NVIDIA Vulnerability Disclosure Program (preferred)**
   <https://www.nvidia.com/en-us/security/>
   Submit through the NVIDIA PSIRT web form. This is the fastest path to
   triage and tracking.

2. **Email NVIDIA PSIRT**
   psirt@nvidia.com — encrypt sensitive reports with the
   [NVIDIA PSIRT PGP key](https://www.nvidia.com/en-us/security/pgp-key).

3. **GitHub Private Vulnerability Reporting**
   Use the **Security** tab on this repository → *Report a vulnerability*.

Please include, where possible:

- Affected tool (e.g. `rapids-install-sccache`, `rapids-print-env`,
  `rapids-upload-to-s3`)
- Whether the issue is in gha-tools itself or in a downstream workflow
  that uses it
- Reproduction steps, including the env vars or arguments involved
- Impact assessment (token leak, fetch-and-exec without verification,
  shell injection, supply-chain weakness)
- Any relevant CWE / CVE identifiers

NVIDIA PSIRT will acknowledge receipt and coordinate triage, fix
development, and coordinated disclosure. More on NVIDIA's response
process: <https://www.nvidia.com/en-us/security/psirt-policies/>.

## Security Architecture & Context

**Classification:** CLI / build-tooling library. Distributed as a set of
executable scripts (shell + a few Python) that consumer GitHub Actions
workflows place on the runner's `PATH`.

**Primary security responsibility:** Provide CI plumbing primitives that
behave predictably given trusted inputs from the calling workflow, without
amplifying the workflow's trust assumptions — i.e. without leaking secrets,
silently executing unverified binaries, or interpolating untrusted strings
into shell commands.

**Components:**

- **`tools/`** — the executable scripts. Approximate roles:
  - **Artifact transport.** `rapids-download-{conda,wheels}-from-github`,
    `rapids-get-pr-artifact`, `rapids-upload-artifacts-dir`,
    `rapids-upload-docs`, `rapids-upload-to-s3`,
    `rapids-upload-to-anaconda-github`,
    `rapids-wheels-anaconda-github` — these move build outputs in and out
    of GitHub Actions artifact storage, S3 (`s3://${RAPIDS_DOWNLOADS_BUCKET}`),
    and anaconda.org.
  - **sccache management.** `rapids-install-sccache`,
    `rapids-configure-sccache`, `rapids-configure-sccache-dist` —
    download and configure the sccache compiler cache binary.
  - **Retry and logging wrappers.** `rapids-retry`, `rapids-conda-retry`,
    `rapids-mamba-retry`, `rapids-pip-retry`, `rapids-logger`,
    `rapids-echo-stderr`, `rapids-telemetry-{setup,record}`.
  - **Environment / metadata.** `rapids-print-env`, `rapids-constants`,
    `rapids-date-string`, `rapids-generate-version`, `rapids-package-name`,
    `rapids-version*`, `rapids-github-run-id`, `rapids-is-release-build`,
    `rapids-s3-path`, `rapids-artifact-name`, `rapids-init-pip`,
    `rapids-generate-pip-constraints`, `rapids-rattler-channel-string`,
    `rapids-wheel-ctk-name-gen`.
  - **Local-dev helpers.** `rapids-prompt-local-github-auth`,
    `rapids-prompt-local-repo-config`.
  - **Workflow utilities.** `rapids-check-pr-job-dependencies`,
    `rapids-size-checker`, `rapids-find-anaconda-uploads.py`,
    `rapids-extract-conda-files`.
- **`tests/`** — pytest-driven tests for the Python helpers and
  shell-script behaviors.
- **Distribution.** README documents two install paths consumer workflows
  use: `git clone -b main` and
  `wget .../releases/latest/download/tools.tar.gz`. Both resolve to a
  *mutable* reference by default.

**Inputs the tools consume:**

- Environment variables (the README codifies a `RAPIDS_*` namespacing
  convention). Secrets flow in as `RAPIDS_GH_TOKEN`, AWS standard env
  vars, `RAPIDS_AUX_TOKEN`, anaconda tokens.
- Positional CLI arguments supplied by the calling workflow step.
- The runner's network — GitHub releases, GitHub artifact API, S3,
  anaconda.org, the GitHub `gh` CLI, the `aws` CLI, conda channels, PyPI.

**Out of scope for this policy:** vulnerabilities in `gh`, `aws`, `conda`,
`mamba`, `pip`, sccache itself, GitHub Actions, the GitHub Artifacts API,
or anaconda.org. Vulnerabilities in *how gha-tools invokes them* —
argument quoting, secret handling, verification of downloaded binaries —
are in scope.

## Threat Model

The threats below trace to specific tools and patterns in this repository.
Several have already been remediated through the
[RAPIDS Security Audit](https://github.com/orgs/rapidsai/projects/207).

1. **Secret leakage into CI logs and process listings.**
   `rapids-print-env` calls `env | sort`, which prints every environment
   variable — including any `RAPIDS_GH_TOKEN`, AWS keys, or anaconda
   tokens passed by the workflow — directly to the job log. Adjacent
   tools that build command lines from env vars can also leak secrets
   into the runner's `ps`-visible process arguments. The audit produced
   fixes for the most acute cases (avoid command-line credential passing,
   redact known-sensitive var names); preserving that posture is
   ongoing.

2. **Fetch-and-execute binaries without integrity verification.**
   `rapids-install-sccache` downloads the sccache binary from the
   configured `SCCACHE_REPO`'s GitHub releases (defaulting to
   `rapidsai/sccache`, latest tag) and executes it. There is no
   checksum or signature verification at the download step. A
   compromised release asset, a hijacked repository, or in-path
   tampering yields arbitrary code execution on the runner with
   workflow secret access.

3. **Mutable distribution refs for gha-tools itself.**
   The documented install paths — `git clone -b main` and
   `wget .../releases/latest/download/tools.tar.gz` — both reference
   moving targets. A consumer workflow that follows the README
   verbatim inherits whatever `main` (or "latest") looks like at
   build time. Any compromise of this repository, or a maintainer
   account that publishes a malicious release, flows immediately into
   every consumer workflow. Consumers should pin to a commit SHA or a
   specific release tag *and* a checksum.

4. **`actions/checkout` token persistence.**
   `actions/checkout` defaults to leaving the GitHub token configured
   in `.git/config` after checkout. Tools that subsequently run from
   the workspace inherit that persisted credential through git
   operations they may not realize use it. The audit produced explicit
   `persist-credentials: false` recommendations; new workflows should
   adopt them.

5. **Over-broad workflow permissions and `secrets: inherit`.**
   gha-tools is itself called from CI workflows; in the RAPIDS audit,
   missing top-level `permissions:` blocks (defaulting to broad token
   scope) and reusable-workflow calls with `secrets: inherit` were the
   marquee CI/CD findings. Re-introduction in this repo's own workflows
   (or in callers') exposes the same blast radius.

6. **Shell-injection risk in env-var interpolation.**
   Bash scripts in `tools/` interpolate environment variables and
   positional arguments into command lines. Variables sourced from
   attacker-influenced inputs (PR titles, branch names, fork-supplied
   workflow inputs) reaching unquoted interpolation produce arbitrary
   command execution on the runner. The audit did not flag specific
   instances in gha-tools, but the risk class is structural to a
   shell-script library — new scripts should be reviewed for it and
   `shellcheck` (the repo's existing linter, per `.shellcheckrc`)
   should remain enforced.

7. **Network-trust boundary at S3, GitHub, anaconda.org.**
   Artifact upload / download tools assume TLS to AWS, GitHub, and
   anaconda.org is intact and that the workflow's credentials grant
   only the intended scope. Any compromise of those credentials
   (item 1, item 4) gives an attacker direct write access to the
   target buckets / packages.

## Critical Security Assumptions

The following are assumed of the calling workflow and the runner. These
are load-bearing — violating them turns documented behavior into a
vulnerability.

- **The calling workflow controls what reaches gha-tools' inputs.**
  Tools assume their env vars and positional arguments come from
  workflow-controlled sources. A workflow that passes PR-controlled
  text (titles, branch names, comment bodies, fork-supplied inputs)
  into a gha-tools invocation has moved the trust boundary; the
  workflow author is responsible for sanitizing or rejecting those
  inputs upstream of the tool call.

- **Secrets stay in `env:`, not on the command line.**
  Tokens passed via `env:` blocks are masked by the GitHub Actions
  runner. Tokens placed on a command line are visible in `ps` to any
  process on the runner and may appear in error traces. Callers must
  pass secrets through `env:` and tools must consume them from there.

- **`rapids-print-env` runs only when its full output is acceptable.**
  `rapids-print-env` dumps the entire environment. Use it in jobs that
  do not carry production credentials, or scope the credentials so
  they are not in the environment of the diagnostic step.

- **Consumers pin gha-tools to an immutable reference.**
  The README's two install snippets are convenience defaults; production
  workflows should replace them with a SHA-pinned `git clone` or a
  release tag plus a checksum. Treat gha-tools as a third-party
  dependency for supply-chain purposes.

- **sccache integrity is verified out-of-band, if at all.**
  `rapids-install-sccache` does not verify the downloaded binary.
  Operators concerned with build-runner integrity should add a
  checksum check around the tool's invocation, or pin
  `SCCACHE_VERSION` to a version whose binary they have separately
  verified.

- **Workflows that call gha-tools set explicit `permissions:`.**
  GitHub's default `GITHUB_TOKEN` permissions are broader than most
  jobs need. Workflows should declare a minimal top-level
  `permissions:` block and only grant per-job elevations where
  required.

- **Reusable-workflow secret passing is explicit, not inherited.**
  Callers should pass only the secrets a downstream workflow needs,
  not `secrets: inherit`. This applies to workflows that use
  gha-tools and to any workflows in this repo that call out.

- **The runner's filesystem and network are trusted.**
  gha-tools assumes the runner is not actively malicious. Self-hosted
  runners that allow forked PR workflows, or shared runners that
  retain state between jobs, violate this assumption and should not
  be used for jobs that consume RAPIDS secrets.

## Supported Versions

gha-tools follows a rolling-main model with periodic tagged releases.
Security fixes ship to `main` and the next tag. Consumers pinning to
older tags should re-pin to receive fixes; there is no formal
back-port policy.

## Dependency Security

gha-tools depends on the binaries on the runner (`bash`, `wget`, `curl`,
`tar`, `aws`, `gh`, `conda`/`mamba`, `pip`, Python) and on the network
services it calls (GitHub, AWS S3, anaconda.org). Upstream vulnerabilities
in those tools are out of scope for this repo's policy; runners should be
kept on supported, patched images.
