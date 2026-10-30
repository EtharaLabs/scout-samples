# Verifier image for the release-evolution dvc task.
#
# [verifier].environment_mode is "separate", so this container is built fresh and the agent never
# touches it. Only the artifacts task.toml declares are transferred in; everything else under /app
# is pristine base-revision source baked here.
#
# What this image preserves, and why each copy exists:
#
#   /app                              the base-revision tree. Declared artifacts overlay their own
#                                     paths on top of this at verify time.
#   /opt/shipped/tests                the test tree exactly as the agent received it, kept out of
#                                     /app so an uploaded artifact cannot overwrite the thing it is
#                                     compared against by the RL-NO-TEST-EDIT assertion.
#   /opt/authoritative/tests          the test tree that GRADES, carried in this build context.
#   /opt/authoritative/dvc-testing    the TARGET-revision dvc/testing package. Seventeen graded
#                                     files import dvc.testing, and it ships inside the package
#                                     tree that artifacts admits, so an uploaded artifact could
#                                     otherwise rewrite the fixtures deciding what the graded tests
#                                     observe. Restoring it from base is not an option: the
#                                     reference needs three files there, measured as two must-keep
#                                     regressions when they are withheld. Restoring from target
#                                     closes the vector at zero oracle cost, measured at 111/111
#                                     required and 2880/2880 held.
ARG DEBIAN_SNAPSHOT=20261025T000000Z
ARG BASE_COMMIT=225bfa6a19652b3d923259c13887d6aa97ac8117
ARG VERIFIER_UID=10002
ARG VERIFIER_GID=10002

# ---------------------------------------------------------------------------------------------
# fetch: the base revision, with its git metadata destroyed in the same layer so no history,
# ref, packfile or remote survives anywhere in the image.
# ---------------------------------------------------------------------------------------------
FROM python:3.12-slim AS fetch
ARG DEBIAN_SNAPSHOT
ARG BASE_COMMIT
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update -qq \
 && apt-get install -y -qq --no-install-recommends git ca-certificates >/dev/null \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init -q . \
 && git remote add origin https://github.com/iterative/dvc \
 && git fetch -q --depth 1 origin "${BASE_COMMIT}" \
 && git checkout -q FETCH_HEAD \
 && rm -rf .git .github .gitignore .gitattributes

# ---------------------------------------------------------------------------------------------
# verifier
# ---------------------------------------------------------------------------------------------
FROM python:3.12-slim
ARG DEBIAN_SNAPSHOT
ARG VERIFIER_UID
ARG VERIFIER_GID

# pathspec is pinned because dvc/ignore.py imports _DIR_MARK from
# pathspec.patterns.gitwildmatch, which pathspec dropped after 0.12.x. Resolving it freely yields
# 649 collection errors against this revision; pinned it yields zero. A determinism claim is void
# against a build that resolves its transitive dependencies at build time.
ENV SETUPTOOLS_SCM_PRETEND_VERSION=3.63.0 \
    PIP_DEFAULT_TIMEOUT=120 \
    LITELLM_LOCAL_MODEL_COST_MAP=True \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1

RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\n' "${DEBIAN_SNAPSHOT}" > /etc/apt/sources.list \
 && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "${DEBIAN_SNAPSHOT}" >> /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update -qq \
 && apt-get install -y -qq --no-install-recommends git ca-certificates >/dev/null \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${VERIFIER_GID}" verifier \
 && useradd --uid "${VERIFIER_UID}" --gid "${VERIFIER_GID}" --create-home --shell /bin/bash verifier

COPY --from=fetch /src /app

# The test tree exactly as the agent received it, kept outside /app.
# The base-revision dvc/ package, kept so test.sh can diff the graded tree against it and hand
# the judged channel its evidence. Reward Kit builds a judge's user message only from the files
# its criteria name, and judge-TOML paths are static, so the evidence has to be produced at a
# fixed path inside the run rather than passed per submission.
RUN cp -R /app/dvc /opt/pristine-dvc
RUN cp -R /app/tests /opt/shipped-tests \
 && mkdir -p /opt/shipped \
 && mv /opt/shipped-tests /opt/shipped/tests

# The trees that grade, carried in this build context.
COPY authoritative /opt/authoritative/tests
COPY authoritative-dvc-testing /opt/authoritative/dvc-testing

COPY requirements.lock.txt /opt/requirements.lock.txt

RUN python -m pip install --no-input --quiet --retries 5 --require-hashes -r /opt/requirements.lock.txt \
 && python -m pip install --no-input --quiet --retries 5 --no-deps /app \
 && python -m pip install --no-input --quiet --retries 5 --no-deps \
      "harbor-rewardkit @ git+https://github.com/harbor-framework/harbor@fdba28fc411e47e8765420a1a063b4918fce3def#subdirectory=packages/rewardkit" \
 && python -c "import importlib.metadata as m, sys; v = m.version('harbor-rewardkit'); sys.exit(0 if v == '0.2.4' else 1)" \
 && command -v rewardkit >/dev/null \
 && python -c "import dvc, dvc_ssh, xdist, pathspec; print('verifier: dvc', dvc.__version__)"

# Reward Kit reads its criteria and scoring config from /tests, and imports every .py it finds
# there. Two consequences the layer below depends on:
#   - judge.toml is denied by .dockerignore and must stay denied: Reward Kit turns any *.toml here
#     carrying a [[criterion]] table into a live LLM judge that raises without a key and writes no
#     reward at all.
#   - the authoritative test trees arrive in this build context for the /opt copies above, but must
#     not remain under /tests: Reward Kit would import authoritative/conftest.py standalone, whose
#     first line is a relative import, and crash before scoring anything. The RUN below removes
#     them, so /tests holds only the scorer inputs.
COPY . /tests

# Reward Kit imports every .py under its scan directory. The authoritative trees are in this
# build context because the COPY lines above place them under /opt, but they must not remain
# under /tests: rewardkit would import authoritative/conftest.py standalone, whose first line is
# a relative import, and crash with "attempted relative import with no known parent package"
# before scoring anything. /opt holds the only copies that grade.
RUN rm -rf /tests/authoritative /tests/authoritative-dvc-testing /tests/requirements.lock.txt \
 && mkdir -p /graded && chown "${VERIFIER_UID}:${VERIFIER_GID}" /graded

RUN git config --system user.email verifier@localhost \
 && git config --system user.name verifier \
 && git config --system init.defaultBranch main \
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

RUN chown -R "${VERIFIER_UID}:${VERIFIER_GID}" /app /logs 2>/dev/null || true
USER ${VERIFIER_UID}:${VERIFIER_GID}
WORKDIR /app
