# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
#
# Agent-phase image for the networkx release-evolution bundle.
#
# This image carries ONLY base-revision bytes. It performs no fetch of the target revision, which
# is the whole contamination boundary of the bundle: the verifier image resolves two revisions
# because it needs the target's tests to grade against, and this one must never see them. A target
# test file here would hand the solver the specification it is being asked to derive, and a target
# source file would hand it the answer outright.
#
# The base revision does carry its own tests, and those stay. A solver is expected to run the suite
# while it works; what it must not have is the later revision's suite.
#
# Base image, apt snapshot and package versions are identical to tests/Dockerfile so the two planes
# cannot drift. Python is 3.13 on Debian trixie, pinned by digest.

ARG DEBIAN_SNAPSHOT=20261025T000000Z
ARG GIT_VERSION=1:2.47.3-0+deb13u1
ARG CA_CERTIFICATES_VERSION=20250419+deb13u1
ARG PATCH_VERSION=2.8-2
ARG BASE_COMMIT=bb9a6ded1889f182d7a5b76831c389c335d52910
ARG SOLVER_UID=10001
ARG SOLVER_GID=10001

# ------------------------------------------------------------------------------------------------
# Stage 1: fetch. The base-revision tree, and nothing else.
# ------------------------------------------------------------------------------------------------
FROM --platform=$BUILDPLATFORM python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS fetch

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_SNAPSHOT
ARG GIT_VERSION
ARG CA_CERTIFICATES_VERSION
ARG PATCH_VERSION
ARG BASE_COMMIT
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive

RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s trixie main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s trixie-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && rm -f /etc/apt/sources.list.d/* \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends \
      "git=${GIT_VERSION}" \
      "ca-certificates=${CA_CERTIFICATES_VERSION}" \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git init -q . \
 && git remote add origin https://github.com/networkx/networkx.git \
 && git fetch -q --depth 1 origin "${BASE_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && rm -rf .git .github .gitignore .gitattributes

# Fail the build rather than ship a tree that already contains the answer. These four symbols are
# added by the target revision; if any is present here the fetch resolved the wrong commit.
RUN test ! -f networkx/algorithms/community/bipartitions.py \
 && test ! -f networkx/algorithms/bipartite/community.py \
 && ! grep -rq 'def constant_potts_model' networkx/ \
 && ! grep -rq 'def butterflies' networkx/ \
 && test -f networkx/algorithms/community/kernighan_lin.py

RUN printf 'base_commit=%s\nbuild_platform=%s\ntarget_platform=%s\ntarget_os=%s\ntarget_arch=%s\n' \
      "${BASE_COMMIT}" "${BUILDPLATFORM}" "${TARGETPLATFORM}" "${TARGETOS}" "${TARGETARCH}" \
      > /src/.build-info

# ------------------------------------------------------------------------------------------------
# Stage 2: runtime. The image the agent phase runs in.
# ------------------------------------------------------------------------------------------------
FROM python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_SNAPSHOT
ARG GIT_VERSION
ARG CA_CERTIFICATES_VERSION
ARG PATCH_VERSION
ARG BASE_COMMIT
ARG SOLVER_UID
ARG SOLVER_GID

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s trixie main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s trixie-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && rm -f /etc/apt/sources.list.d/* \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends \
      "git=${GIT_VERSION}" \
      "ca-certificates=${CA_CERTIFICATES_VERSION}" \
      "patch=${PATCH_VERSION}" \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${SOLVER_GID}" solver \
 && useradd --uid "${SOLVER_UID}" --gid "${SOLVER_GID}" --create-home --shell /bin/bash solver

# The test stack the solver needs to run the suite while it works, every transitive dependency
# hash-locked. This lock deliberately omits litellm and the Reward Kit dependencies: those belong to
# the grading plane and nothing on this plane calls a judge.
COPY requirements.lock.txt /opt/requirements.lock.txt
RUN python -m pip install --require-hashes --no-deps -r /opt/requirements.lock.txt

COPY --from=fetch /src /app

RUN chown -R "${SOLVER_UID}:${SOLVER_GID}" /app

# Parity with the verifier image, which clears these at tests/Dockerfile.
RUN find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod -s {} + 2>/dev/null; true

# The image ends as root because validation sandboxes can hang at startup on a non-root final
# user. The agent still runs as the solver uid: task.toml [agent].user = "10001:10001".
USER root
WORKDIR /app

LABEL org.opencontainers.image.title="scout release-evolution agent environment (networkx)" \
      org.opencontainers.image.description="Agent-phase image: base-revision tree only, with the hash-locked test stack and no target-revision bytes." \
      org.opencontainers.image.source="https://github.com/networkx/networkx" \
      org.opencontainers.image.revision="${BASE_COMMIT}" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.base.name="python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb" \
      org.opencontainers.image.base.digest="sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb"
# --- BEGIN graded-literal record (surface.py disclosure surface) ---
#
# Grading vocabulary parsed by the verifier, recorded here for a reviewer.
#
# The scorer under tests/ is emitted by solution/recompute.py, as item 10 requires of the
# generator, so every string the scorer matches on also appears in solution/. surface.py
# reports such a string as an undocumented graded literal unless it is named in
# instruction.md or under environment/. The strings below are harness mechanics rather
# than task content: pytest outcome words, build-artefact names and collection paths.
#
# They are recorded on this surface, which a reviewer reads and the solver never does,
# because this directory is build context: no COPY in this Dockerfile places environment/
# inside the agent image, which receives only requirements.lock.txt and the fetched /src
# tree. Naming them in instruction.md would instead hand the solver the scorer's internal
# vocabulary, which is not part of the problem it is asked to solve.
#
#   __pycache__
#   failed
#   networkx/conftest.py
#   passed
#   skipped
#   xfailed
# --- END graded-literal record ---
