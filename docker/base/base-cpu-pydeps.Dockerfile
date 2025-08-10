ARG ORG
ARG BASE_TAG
FROM ghcr.io/${ORG}/base-utils:${BASE_TAG}

COPY docker/base/requirements.cpu-pydeps.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt

# User will be set in family images