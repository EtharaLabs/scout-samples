# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
#
# Separate verifier image for the celery release-evolution bundle.
#
# Structurally SIMPLER than the three networkx siblings, and the simplification is the point. Those
# bundles grade a project that keeps its tests INSIDE the package, so the graded tree and the test
# tree are one tree: their fetch stage had to extract every networkx/**/tests/ subtree into an
# overlay, lay it back down at verify time, and separately compare the shipped test bytes to catch
# an edit. Both mechanisms produced grading defects. One nested the overlay and scored a correct
# oracle at 0.0 with phantom regressions, indistinguishable from a no-op. Another counted a conftest
# edit the release itself makes as a red-line violation and zeroed a rollout that had resolved 161
# of 187 nodes.
#
# This project keeps its tests in a separate top-level t/ tree, so the fetch stage takes that one
# directory whole, test.sh replaces it with a single cp, and task.toml declares only /app/celery as
# an artifact. The solver's test bytes therefore never reach this image at all, which makes the
# no-test-edit red line structurally unreachable rather than enforced. Neither sibling failure mode
# can occur here.
#
# This project is NOT installed as a distribution, for the reason the agent image states: every
# celery version on an index is the target revision or later. That has one consequence the grader
# must handle explicitly, and tests/test.sh does: the `celery` pytest marker is normally registered
# by an installed distribution's pytest11 entry point, and pyproject.toml runs with
# --strict-markers, so without that entry point t/unit/backends/test_base.py dies at collection and
# takes 103 required nodes with it. test.sh loads the plugin from the graded tree instead.
#
# Python is 3.13 on Debian trixie, pinned by digest, matching the siblings.

ARG DEBIAN_SNAPSHOT=20261025T000000Z
ARG GIT_VERSION=1:2.47.3-0+deb13u1
ARG CA_CERTIFICATES_VERSION=20250419+deb13u1
ARG BASE_COMMIT=088c39c0f78b23a9cdf8d1c9e265ea64d02cfd86
ARG TARGET_COMMIT=cca11164860a1bee6ad8626c27a683b482f741eb
ARG HARBOR_COMMIT=fdba28fc411e47e8765420a1a063b4918fce3def
ARG VERIFIER_UID=10002
ARG VERIFIER_GID=10002

# ------------------------------------------------------------------------------------------------
# Stage 1: fetch. Produces the base-revision tree and the target-revision test tree.
# ------------------------------------------------------------------------------------------------
FROM --platform=$BUILDPLATFORM python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS fetch

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_SNAPSHOT
ARG GIT_VERSION
ARG CA_CERTIFICATES_VERSION
ARG BASE_COMMIT
ARG TARGET_COMMIT
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
 && git remote add origin https://github.com/celery/celery.git \
 && git fetch -q --depth 1 origin "${BASE_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && rm -rf .git .github .gitignore .gitattributes

# The target revision's t/ tree, and nothing else from that revision. Fetched into a throwaway
# clone so no target-revision SOURCE file can reach the graded tree: the solver must write the
# implementation, and a stray target-revision module would hand it over.
RUN mkdir -p /fetch-target \
 && cd /fetch-target \
 && git init -q . \
 && git remote add origin https://github.com/celery/celery.git \
 && git fetch -q --depth 1 origin "${TARGET_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && cp -R t /authoritative-t \
 && cd / && rm -rf /fetch-target

# Fails the build rather than the grade if the test tree is empty, lost its layout, or is actually
# the base revision's. The first two anchors are modules the graded sets draw required nodes from;
# the third is a name that exists ONLY in the target revision's tests, so its absence means the
# fetch resolved the wrong commit and the grader would silently measure base tests against base
# source and report a no-op as a pass.
RUN test -f /authoritative-t/unit/backends/test_base.py \
 && test -f /authoritative-t/unit/worker/test_native_delayed_delivery.py \
 && grep -rq '_create_chord_error_with_cause' /authoritative-t/unit/backends/test_base.py \
 && printf 'authoritative_test_files=%s\n' "$(find /authoritative-t -name 'test_*.py' | wc -l)" > /authoritative-t/.tree-info

RUN printf 'base_commit=%s\ntarget_commit=%s\nbuild_platform=%s\ntarget_platform=%s\ntarget_os=%s\ntarget_arch=%s\n' \
      "${BASE_COMMIT}" "${TARGET_COMMIT}" "${BUILDPLATFORM}" "${TARGETPLATFORM}" "${TARGETOS}" "${TARGETARCH}" \
      > /src/.build-info

# ------------------------------------------------------------------------------------------------
# Stage 2: runtime. The image the verifier phase actually runs.
# ------------------------------------------------------------------------------------------------
FROM python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_SNAPSHOT
ARG GIT_VERSION
ARG CA_CERTIFICATES_VERSION
ARG BASE_COMMIT
ARG TARGET_COMMIT
ARG HARBOR_COMMIT
ARG VERIFIER_UID
ARG VERIFIER_GID

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True

# git and ca-certificates are build-time requirements of the Reward Kit install below, which
# resolves the pinned Harbor commit. They stay in the shipped layer because removing them is not
# possible within a single stage; the grading toolchain is their only user and the verifier phase
# reaches only the private host-gateway ranges task.toml allows.
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s trixie main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s trixie-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && rm -f /etc/apt/sources.list.d/* \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends \
      "git=${GIT_VERSION}" \
      "ca-certificates=${CA_CERTIFICATES_VERSION}" \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${VERIFIER_GID}" verifier \
 && useradd --uid "${VERIFIER_UID}" --gid "${VERIFIER_GID}" --create-home --shell /bin/bash verifier

# Every transitive dependency, including Reward Kit's own, comes from a hash-locked manifest. The
# lock is resolved universally rather than for one platform, because task.toml declares both
# linux/amd64 and linux/arm64 and a single-platform lock would install on only one of them.
#
# litellm is present here and absent from the agent lock. Omitting it does not fail loudly: Reward
# Kit raises inside the judged channel and suppresses the WHOLE reward.json, including the
# deterministic channel that carries nine tenths of the score, and the loss is invisible until a
# grading run.
COPY requirements.lock.txt /opt/requirements.lock.txt
RUN python -m pip install --require-hashes --no-deps -r /opt/requirements.lock.txt

# Reward Kit at exactly the version the pinned Harbor commit names. That release is not published to
# an index, so it is installed from the Harbor repository at the immutable 40-hex commit the bundle
# pins, with --no-deps because every dependency is already hash-locked above.
RUN python -m pip install --no-deps \
      "harbor-rewardkit @ git+https://github.com/harbor-framework/harbor@${HARBOR_COMMIT}#subdirectory=packages/rewardkit" \
 && python -c "import importlib.metadata as m, sys; v = m.version('harbor-rewardkit'); sys.exit(0 if v == '0.2.4' else 1)"

# The base-revision tree. The declared artifact overlays its own paths on top of this at verify
# time, so anything the solver did not produce is pristine base-revision bytes here.
COPY --from=fetch /src /app

# The target-revision test tree. test.sh replaces /app's copy with this before any test runs. It is
# kept OUTSIDE /app so an uploaded artifact cannot overwrite the thing it is graded against.
COPY --from=fetch /authoritative-t /opt/authoritative/t

# The base-revision package tree, kept so test.sh can produce final.diff. Every criterion in
# judge.toml declares that diff as its evidence, and a rubric whose evidence has no producer is
# documentation rather than a channel. The diff is the submitted tree against these bytes.
RUN mkdir -p /opt/pristine \
 && cp -R /app/celery /opt/pristine/celery

# Reward Kit reads its criteria and scoring config from /tests. Harbor does not upload this tree
# when the verifier image is built from it, so the bytes are baked here.
COPY . /tests
RUN rm -rf /tests/Dockerfile /tests/.dockerignore /tests/requirements.lock.txt

RUN mkdir -p /logs/verifier /logs/artifacts \
 && chown -R "${VERIFIER_UID}:${VERIFIER_GID}" /app /logs /tests

# Parity with the agent image. The grading plane runs agent-authored code during collection, so a
# setuid-root surface reachable by the verifier uid is an asymmetry with no upside.
RUN find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod -s {} + 2>/dev/null; true

WORKDIR /app

LABEL org.opencontainers.image.title="scout release-evolution verifier (celery)" \
      org.opencontainers.image.description="Separate verifier image: base-revision tree, target-revision t/ test tree, and the pinned Harbor Reward Kit." \
      org.opencontainers.image.source="https://github.com/celery/celery" \
      org.opencontainers.image.revision="${BASE_COMMIT}" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.base.name="python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb" \
      org.opencontainers.image.base.digest="sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb"

# The image ends as root because validation sandboxes can hang at startup on a non-root final
# user. Privilege is still dropped where it matters: Harbor runs test.sh as task.toml
# [verifier].user = "10002:10002", so the grader cannot write outside its closure.
USER root
