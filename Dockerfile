FROM ubuntu

RUN apt-get update && \
    apt-get install -y jq ripgrep curl lynx procps iputils-ping python3-pip git diffutils && \
    mkdir -p /root/.config/pip && \
# Create pip.conf to allow breaking system packages
    cat <<'EOF' > /root/.config/pip/pip.conf
[global]
break-system-packages = true
EOF
    