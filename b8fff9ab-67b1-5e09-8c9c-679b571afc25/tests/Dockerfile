# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
#
# Separate verifier image for the sympy release-evolution bundle.
#
# This library keeps its tests INSIDE the package it ships, under sympy/**/tests/, so the graded
# tree and the test tree are one tree. Three separate roots are therefore baked here, and each
# exists because a sibling bundle paid for it:
#
#   /app                      base-revision tree; the declared artifact overlays its own paths here
#   /opt/authoritative/overlay  target-revision tree, from which test.sh restores all 65 tests/ dirs
#   /opt/shipped              base-revision TEST bytes only, for the no-test-edit comparison
#   /opt/pristine/sympy       base-revision package, so test.sh can produce final.diff
#
# The overlay is kept OUTSIDE /app so an uploaded artifact cannot overwrite the thing it is graded
# against. /opt/shipped is separate from /opt/pristine because the red-line comparison must read
# bytes the solver could not have touched even if it rewrote /app wholesale.
#
# Unlike the three networkx siblings there is NO conftest carve-out, and that is a measured property
# of this span: sympy/conftest.py is byte-identical between the two revisions, so a solver has no
# legitimate reason to touch it. One sibling needed the carve-out because its release edits conftest
# as part of the work, and counting that edit as a violation zeroed a rollout that had resolved 161
# of 187 nodes. That failure mode cannot arise here.
#
# This project is NOT installed as a distribution, for the reason the agent image states: every
# sympy version on an index is the target revision or later.
#
# Python is 3.13 on Debian trixie, pinned by digest, matching the siblings.

ARG DEBIAN_SNAPSHOT=20261025T000000Z
ARG GIT_VERSION=1:2.47.3-0+deb13u1
ARG CA_CERTIFICATES_VERSION=20250419+deb13u1
ARG BASE_COMMIT=c870d17c2638f5061800e344b72ff80086a0b41d
ARG TARGET_COMMIT=fe935ceb303891d1f8bea4c03b19fd9ec9464b02
ARG HARBOR_COMMIT=fdba28fc411e47e8765420a1a063b4918fce3def
ARG VERIFIER_UID=10002
ARG VERIFIER_GID=10002

# ------------------------------------------------------------------------------------------------
# Stage 1: fetch. Produces the base tree, the target-revision test overlay, and the shipped test
# bytes used by the red-line comparison.
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
 && git remote add origin https://github.com/sympy/sympy.git \
 && git fetch -q --depth 1 origin "${BASE_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && rm -rf .git .github .gitignore .gitattributes .mailmap

# The base-revision TEST bytes, copied before anything else touches them. test.sh compares the
# submitted tree against these to detect a test edit; they must be bytes no artifact can reach.
RUN mkdir -p /shipped \
 && while IFS= read -r d; do \
      mkdir -p "/shipped/$(dirname "$d")" && cp -R "$d" "/shipped/$d"; \
    done < <(find sympy -type d -name tests) \
 && printf 'shipped_test_files=%s\n' "$(find /shipped -name '*.py' | wc -l)" > /shipped/.shipped-info

# The target revision's tree, fetched into a throwaway clone. Only its tests/ subtrees are kept, so
# no target-revision SOURCE file can reach the graded tree: the solver must write the implementation,
# and a stray target-revision module would hand it over.
RUN mkdir -p /fetch-target \
 && cd /fetch-target \
 && git init -q . \
 && git remote add origin https://github.com/sympy/sympy.git \
 && git fetch -q --depth 1 origin "${TARGET_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && mkdir -p /overlay \
 && while IFS= read -r d; do \
      mkdir -p "/overlay/$(dirname "$d")" && cp -R "$d" "/overlay/$d"; \
    done < <(find sympy -type d -name tests) \
 && cd / && rm -rf /fetch-target

# Fails the build rather than the grade if the overlay is empty, lost its layout, or is actually the
# base revision's. The third anchor is the strongest: qs_factor is a name the TARGET revision's
# tests import and the base revision's do not, so its absence means the fetch resolved the wrong
# commit and the grader would silently measure base tests against base source, reporting a no-op as
# a pass.
RUN test -f /overlay/sympy/ntheory/tests/test_qs.py \
 && test -f /overlay/sympy/printing/tests/test_pycode.py \
 && grep -q 'qs_factor' /overlay/sympy/ntheory/tests/test_qs.py \
 && test "$(find /overlay -type d -name tests | wc -l)" -ge 65 \
 && ! grep -rq --include='*.py' 'DefinedFunction' /src/sympy \
 && printf 'overlay_dirs=%s\noverlay_test_files=%s\n' \
      "$(find /overlay -type d -name tests | wc -l)" \
      "$(find /overlay -name '*.py' | wc -l)" > /overlay/.overlay-info

RUN printf 'base_commit=%s\ntarget_commit=%s\nbuild_platform=%s\ntarget_platform=%s\n' \
      "${BASE_COMMIT}" "${TARGET_COMMIT}" "${BUILDPLATFORM}" "${TARGETPLATFORM}" \
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
#
# hypothesis is present for the reason the agent lock states: this project's conftest refuses to
# collect without it.
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

# The target-revision test overlay. tests/test.sh restores all 65 tests/ dirs from this before any
# test runs. Kept outside /app so an uploaded artifact cannot overwrite it.
COPY --from=fetch /overlay /opt/authoritative/overlay

# The base-revision test bytes, for the no-test-edit comparison.
COPY --from=fetch /shipped /opt/shipped

# The base-revision package tree, kept so test.sh can produce final.diff. Every criterion in
# judge.toml declares that diff as its evidence, and a rubric whose evidence has no producer is
# documentation rather than a channel.
RUN mkdir -p /opt/pristine \
 && cp -R /app/sympy /opt/pristine/sympy

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

LABEL org.opencontainers.image.title="scout release-evolution verifier (sympy)" \
      org.opencontainers.image.description="Separate verifier image: base-revision tree, target-revision test overlay, shipped test bytes and the pinned Harbor Reward Kit." \
      org.opencontainers.image.source="https://github.com/sympy/sympy" \
      org.opencontainers.image.revision="${BASE_COMMIT}" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.base.name="python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb" \
      org.opencontainers.image.base.digest="sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb"

# The image ends as root because validation sandboxes can hang at startup on a non-root final
# user. Privilege is still dropped where it matters: Harbor runs test.sh as task.toml
# [verifier].user = "10002:10002", so the grader cannot write outside its closure.
USER root
