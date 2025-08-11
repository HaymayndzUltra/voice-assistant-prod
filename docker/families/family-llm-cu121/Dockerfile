# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN python -m pip install --no-cache-dir \
      transformers>=4.41.0 \
      accelerate \
      sentencepiece \
      tiktoken

WORKDIR /app

USER appuser
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "-lc", "python -c 'import transformers, tiktoken, sentencepiece; print(\"llm base ready\")'"]


