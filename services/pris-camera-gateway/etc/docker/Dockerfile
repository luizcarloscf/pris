FROM ubuntu:24.04 AS build

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates git python3 python3-venv && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_PYTHON=/usr/bin/python3 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/pris-camera-gateway/.venv

WORKDIR /src
COPY pyproject.toml uv.lock ./
COPY etc/spinnaker/spinnaker_python-*.whl etc/spinnaker/
RUN uv sync --frozen --no-dev --no-install-project
COPY README.md LICENSE ./
COPY src src
RUN uv sync --frozen --no-dev --no-editable

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
COPY etc/spinnaker /tmp/spinnaker
RUN set -eux; \
    echo "libspinnaker libspinnaker/accepted-flir-eula boolean true" | debconf-set-selections; \
    echo "libspinnaker libspinnaker/analytics-consent boolean false" | debconf-set-selections; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 libturbojpeg libusb-1.0-0 libgomp1 zlib1g \
        libavcodec60 libavformat60 libavutil58 libswscale7 \
        $(ls /tmp/spinnaker/*.deb | grep -v spinview); \
    rm -rf /tmp/spinnaker /var/lib/apt/lists/*

COPY --from=build /opt/pris-camera-gateway/.venv /opt/pris-camera-gateway/.venv
COPY etc/conf/options.json /etc/pris-camera-gateway/options.json
ENV PATH="/opt/pris-camera-gateway/.venv/bin:$PATH" \
    SPINNAKER_GENTL64_CTI="/opt/spinnaker/lib/spinnaker-gentl/Spinnaker_GenTL.cti"

RUN python3 -c "import PySpin, turbojpeg; turbojpeg.TurboJPEG(); PySpin.System.GetInstance().ReleaseInstance()"

CMD ["pris-camera-gateway", "/etc/pris-camera-gateway/options.json"]
