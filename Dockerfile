FROM ubuntu

RUN apt-get update && \
    apt-get install -y jq ripgrep curl lynx procps iputils-ping python3-pip git diffutils && \
    mkdir -p /root/.config/pip && \
    printf "[global]\nbreak-system-packages = true\n" > /root/.config/pip/pip.conf && \
    pip install trafilatura requests && \
    pip cache purge && \
    rm -rf /var/lib/apt/lists/*
