# Existing NAS image, pinned by content; no existing container or volume reused.
FROM sha256:4936a2d16430a6c58977a5a0755cc42190e45e92ee03c5fe66a47efbf4b209d0
USER root
ENV PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONUNBUFFERED=1
WORKDIR /tmp
RUN curl -fsSLO https://nodejs.org/dist/v24.19.0/node-v24.19.0-linux-x64.tar.xz \
 && curl -fsSLO https://nodejs.org/dist/v24.19.0/SHASUMS256.txt \
 && grep ' node-v24.19.0-linux-x64.tar.xz$' SHASUMS256.txt | sha256sum -c - \
 && tar -xJf node-v24.19.0-linux-x64.tar.xz --strip-components=1 -C /usr/local \
 && rm node-v24.19.0-linux-x64.tar.xz SHASUMS256.txt \
 && npm install -g --ignore-scripts @openai/codex@0.166.0
RUN apt-get update && apt-get install -y --no-install-recommends chromium python3-venv git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT []
CMD ["python3", "--version"]
