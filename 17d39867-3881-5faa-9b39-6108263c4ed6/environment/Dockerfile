# syntax=docker/dockerfile:1
#
# Agent sandbox for the release-evolution task.
#
# Two named stages. The fetch stage runs on the build platform and produces the upstream tree at
# its base revision with every byte of version-control metadata destroyed. The runtime stage
# carries only the interpreter, the solver's own toolchain, and that tree: no clone, no remote,
# no packfile, and no credential ever reaches a shipped layer.

ARG DEBIAN_SNAPSHOT=20261025T000000Z
ARG BASE_COMMIT=225bfa6a19652b3d923259c13887d6aa97ac8117
ARG SOLVER_UID=10001
ARG SOLVER_GID=10001

# ------------------------------------------------------------------------------------------------
# Stage 1: fetch. Build-platform only. Everything this stage installs is build-only material that
# the runtime stage never inherits, because the runtime stage takes the source tree alone.
# ------------------------------------------------------------------------------------------------
FROM --platform=$BUILDPLATFORM python:3.12-slim AS fetch

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_SNAPSHOT
ARG BASE_COMMIT
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive

RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Single-commit fetch of the base revision, then every byte of git metadata is destroyed in the
# same layer. No history, tag, ref, reflog, packfile, alternate, or remote survives into the image,
# so the upstream answer is not recoverable from inside the task even if a network appeared.
RUN git init -q . \
 && git remote add origin https://github.com/iterative/dvc.git \
 && git fetch -q --depth 1 origin "${BASE_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && rm -rf .git .github .gitignore .gitattributes

RUN printf 'base_commit=%s\nbuild_platform=%s\ntarget_platform=%s\ntarget_os=%s\ntarget_arch=%s\n' \
      "${BASE_COMMIT}" "${BUILDPLATFORM}" "${TARGETPLATFORM}" "${TARGETOS}" "${TARGETARCH}" \
      > /src/.build-info

# ------------------------------------------------------------------------------------------------
# Stage 2: runtime. The image the solver actually receives.
# ------------------------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_SNAPSHOT
ARG BASE_COMMIT
ARG SOLVER_UID
ARG SOLVER_GID

# setuptools-scm derives the version from git metadata, which the fetch stage destroyed, so the
# version is pinned explicitly or the install fails with no tags to read.
ENV DEBIAN_FRONTEND=noninteractive \
    # The agent receives the BASE tree, so it reports the base release. setuptools-scm
    # would normally derive this from tags, which the fetch stage destroyed, so it is
    # pinned explicitly. Naming the target release here would hand the solver the
    # version number of the release it is being asked to implement.
    SETUPTOOLS_SCM_PRETEND_VERSION=3.62.0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

# git is the solver's own toolchain here: the recorded patch-apply contract of this task runs
# `git apply`, and the oracle executes inside this same image. No compiler, archive, package
# cache, or build-only material is installed.
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

# A fixed numeric non-root identity the image creates itself.
RUN groupadd --gid "${SOLVER_GID}" solver \
 && useradd --uid "${SOLVER_UID}" --gid "${SOLVER_GID}" --create-home --shell /bin/bash solver

# Hash-locked dependency manifest. --require-hashes refuses any distribution whose bytes differ
# from the recorded digest, so the dependency set is reproducible rather than resolved afresh.
# pathspec is pinned to 0.12.1 inside it because dvc/ignore.py imports _DIR_MARK inside class
# DvcIgnorePatterns (ignore.py:30), so the failure surfaces on first use rather than on import
# and later pathspec releases dropped it; resolving freely yields 649 collection errors.
COPY requirements.lock.txt /opt/requirements.lock.txt
# pytest and pytest-cov are in this lock on purpose: the repository's addopts carry
# --cov-config, so the command instruction.md tells the solver to run fails without them.
# They are hash-pinned here rather than installed loose at a later layer.
RUN python -m pip install --require-hashes --no-deps -r /opt/requirements.lock.txt

WORKDIR /app

# Only the source tree crosses the stage boundary.
COPY --from=fetch --chown=${SOLVER_UID}:${SOLVER_GID} /src /app

RUN python -m pip install --no-deps /app \
 && python -c "import dvc; print('agent sandbox: dvc', dvc.__version__)"

# The solver owns its working directory and nothing else. No sudo grant is added, and the base
# image's own setuid and setgid bits are cleared so the identity cannot be escalated.
RUN find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod -s {} + 2>/dev/null; \
    chown -R "${SOLVER_UID}:${SOLVER_GID}" /app

LABEL org.opencontainers.image.title="scout release-evolution agent sandbox" \
      org.opencontainers.image.description="Upstream Python source tree pinned at a release boundary with all version-control metadata destroyed." \
      org.opencontainers.image.source="https://github.com/iterative/dvc" \
      org.opencontainers.image.revision="${BASE_COMMIT}" \
      org.opencontainers.image.licenses="Apache-2.0"

USER ${SOLVER_UID}:${SOLVER_GID}

# No ENTRYPOINT. Harbor starts the main service from its own docker-compose, overriding only
# `command`, so an ENTRYPOINT here is kept and prepended: ENTRYPOINT ["/bin/bash"] turns the
# supplied `sh -c "sleep infinity"` into `/bin/bash /usr/bin/sh -c ...`, which asks bash to
# execute the sh BINARY as a shell script and exits 126. Harbor then fails the compose command
# and neither the agent nor the verifier ever starts. Authoring check: build the image and assert
# `docker run --rm <image> sh -c 'echo ok'` prints ok.
CMD ["sh", "-c", "sleep infinity"]

# ---------------------------------------------------------------------------
# Agent tooling. curl, ca-certificates and procps are the utilities an agent harness needs to
# function inside the sandbox; they are installed from the dated snapshot mirror like everything
# else, so the layer stays reproducible.
#
# NO AGENT IS BAKED IN. This bundle is agent-agnostic, and Harbor's own adapters apt-get install
# their dependencies at trial time, which the agent phase allowlist denies. The supported path is
# therefore to DERIVE an image from this one with your agent installed at build time, where
# network and root are legitimately available, and run that derived image instead. Harbor skips
# its installer when the CLI is already on PATH.
USER root
RUN apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends curl ca-certificates procps \
 && rm -rf /var/lib/apt/lists/*

RUN find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod -s {} + 2>/dev/null || true

USER ${SOLVER_UID}:${SOLVER_GID}
WORKDIR /app

# dvc's pyproject sets `addopts = -ra --cov-config pyproject.toml`, so a bare
# `python -m pytest tests/unit -q` (exactly what instruction.md:144 tells the solver to run)
WORKDIR /app
