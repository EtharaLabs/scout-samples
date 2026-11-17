# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
#
# Separate verifier image for the networkx release-evolution bundle.
#
# Differs structurally from the sibling dvc and conan bundles in one way, and it is forced rather
# than chosen: networkx keeps its tests INSIDE the package, at networkx/<area>/tests/test_*.py.
# conan grades from a separate test/unittests tree copied out of the build context, which cannot
# work here because the graded tree and the test tree are one tree. The fetch stage therefore
# resolves TWO revisions: the base revision becomes /app, and the target revision's test subtrees
# are extracted alone into an overlay that test.sh lays back down before any test runs. That single
# overlay does two jobs: it supplies the required tests, which do not exist at the base revision,
# and it overwrites any test the solver edited, so a test edit cannot change a grade.
#
# The base image is pinned by digest and is Debian trixie, not the bookworm the siblings pin. The
# apt package versions and the snapshot suite below are therefore trixie's and are not copied from
# conan, where they would resolve to nothing.
#
# Python is 3.13 rather than the siblings' 3.12, and that is deliberate. The required set for this
# bundle was derived and twice stabilised on 3.13; grading on 3.12 would score against a set that
# was never measured there. The base suite was re-run inside this image and reproduces the
# measurement exactly: 6955 passed, 78 skipped, 1 xfailed.

ARG DEBIAN_SNAPSHOT=20261025T000000Z
ARG GIT_VERSION=1:2.47.3-0+deb13u1
ARG CA_CERTIFICATES_VERSION=20250419+deb13u1
ARG BASE_COMMIT=bb9a6ded1889f182d7a5b76831c389c335d52910
ARG TARGET_COMMIT=49ca2290b80c1389eb4d8d8e49dcba73f8fec016
ARG HARBOR_COMMIT=fdba28fc411e47e8765420a1a063b4918fce3def
ARG VERIFIER_UID=10002
ARG VERIFIER_GID=10002

# ------------------------------------------------------------------------------------------------
# Stage 1: fetch. Produces the base-revision tree and the target-revision test overlay.
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
 && git remote add origin https://github.com/networkx/networkx.git \
 && git fetch -q --depth 1 origin "${BASE_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && rm -rf .git .github .gitignore .gitattributes

# The target revision's test subtrees, and nothing else from that revision. Fetched into a throwaway
# clone so no target-revision source file can reach the graded tree: the solver must write the
# implementation, and a stray target-revision module would hand it over.
RUN mkdir -p /fetch-target /overlay \
 && cd /fetch-target \
 && git init -q . \
 && git remote add origin https://github.com/networkx/networkx.git \
 && git fetch -q --depth 1 origin "${TARGET_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && while IFS= read -r d; do \
      mkdir -p "/overlay/$(dirname "${d}")"; \
      cp -R "${d}" "/overlay/${d}"; \
    done < <(find networkx -type d -name tests) \
 && cp networkx/conftest.py /overlay/networkx/conftest.py \
 && cd / && rm -rf /fetch-target

# Fails the build rather than the grade if the overlay is empty or lost its layout.
RUN test -f /overlay/networkx/algorithms/community/tests/test_leiden.py \
 && test -f /overlay/networkx/algorithms/bipartite/tests/test_community.py \
 && test -f /overlay/networkx/conftest.py \
 && printf 'overlay_test_dirs=%s\n' "$(find /overlay -type d -name tests | wc -l)" > /overlay/.overlay-info

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
    MPLBACKEND=Agg \
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

# The target-revision test overlay. test.sh lays this over /app before any test runs.
COPY --from=fetch /overlay /opt/authoritative/overlay

# The test tree exactly as the agent received it, kept out of /app so an uploaded artifact cannot
# overwrite the thing it is compared against. Because networkx's tests live inside the package, this
# is a copy of the base-revision test subtrees rather than a separate directory.
RUN mkdir -p /opt/shipped \
 && while IFS= read -r d; do \
      mkdir -p "/opt/shipped/$(dirname "${d#/app/}")"; \
      cp -R "${d}" "/opt/shipped/${d#/app/}"; \
    done < <(find /app/networkx -type d -name tests) \
 && cp /app/networkx/conftest.py /opt/shipped/networkx/conftest.py

# The base-revision package tree, kept so test.sh can produce final.diff. Every criterion in
# judge.toml declares that diff as its evidence, and a rubric whose evidence has no producer is
# documentation rather than a channel. The diff is the submitted tree against these bytes.
RUN mkdir -p /opt/pristine \
 && cp -R /app/networkx /opt/pristine/networkx

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

LABEL org.opencontainers.image.title="scout release-evolution verifier (networkx)" \
      org.opencontainers.image.description="Separate verifier image: base-revision tree, target-revision test overlay, and the pinned Harbor Reward Kit." \
      org.opencontainers.image.source="https://github.com/networkx/networkx" \
      org.opencontainers.image.revision="${BASE_COMMIT}" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.base.name="python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb" \
      org.opencontainers.image.base.digest="sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb"

# The image ends as root because validation sandboxes can hang at startup on a non-root final
# user. Privilege is still dropped where it matters: Harbor runs test.sh as task.toml
# [verifier].user = "10002:10002", so the grader cannot write outside its closure.
USER root
