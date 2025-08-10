ARG ORG
ARG BASE_TAG
FROM ghcr.io/${ORG}/base-cpu-pydeps:${BASE_TAG}

COPY docker/base/requirements.family-web.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

USER appuser