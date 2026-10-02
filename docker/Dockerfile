FROM ros:jazzy-ros-base-noble@sha256:066420e07f60aa18262f2479981def87ebcfcec42eefb0c0c57c4a46098348ca
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-venv python3-pip python3-colcon-common-extensions \
    build-essential git ffmpeg libegl1 libgl1 libgles2 libgl1-mesa-dri mesa-utils \
    libglib2.0-0t64 libsm6 libxext6 curl \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN python -m pip install --no-cache-dir uv==0.8.22
COPY requirements.lock /tmp/requirements.lock
RUN uv pip install --python /opt/venv/bin/python --no-cache --index-strategy unsafe-best-match \
    --extra-index-url https://download.pytorch.org/whl/cu128 -r /tmp/requirements.lock
COPY docker/entrypoint.sh /project-entrypoint.sh
COPY requirements.ros.txt /tmp/requirements.ros.txt
RUN uv pip install --python /opt/venv/bin/python --no-cache -r /tmp/requirements.ros.txt
RUN chmod +x /project-entrypoint.sh && mkdir -p /data /workspace \
    && dpkg-query -W > /opt/os-packages.txt
WORKDIR /workspace
ENTRYPOINT ["/project-entrypoint.sh"]
CMD ["sleep", "infinity"]
