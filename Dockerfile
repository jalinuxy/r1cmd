# r1cmd — ArvanCloud Object Storage CLI
# https://github.com/jalinuxy/r1cmd

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim

LABEL org.opencontainers.image.title="r1cmd" \
      org.opencontainers.image.description="Simple CLI for ArvanCloud Object Storage" \
      org.opencontainers.image.source="https://github.com/jalinuxy/r1cmd" \
      org.opencontainers.image.url="https://jalinuxy.ir/r1cmd"

RUN useradd --create-home --shell /bin/bash r1 \
    && mkdir -p /config /data \
    && chown r1:r1 /config /data

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

ENV XDG_CONFIG_HOME=/config \
    HOME=/home/r1

USER r1
WORKDIR /data

VOLUME ["/config", "/data"]

ENTRYPOINT ["r1"]
CMD []
