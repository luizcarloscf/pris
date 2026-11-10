FROM ubuntu:24.04 AS build

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates git python3 python3-venv && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_PYTHON=/usr/bin/python3 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/pris-aruco-detector/.venv

WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY README.md LICENSE ./
COPY src src
RUN uv sync --frozen --no-dev --no-editable

FROM ubuntu:24.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/pris-aruco-detector/.venv /opt/pris-aruco-detector/.venv
COPY etc/conf/options.json /etc/pris-aruco-detector/options.json
ENV PATH="/opt/pris-aruco-detector/.venv/bin:$PATH"

CMD ["pris-aruco-detector", "/etc/pris-aruco-detector/options.json"]
