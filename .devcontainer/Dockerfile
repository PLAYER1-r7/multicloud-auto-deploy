FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install additional tools and PDF generation dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
  jq \
  httpie \
  tree \
  vim \
  poppler-utils \
  imagemagick \
  pandoc \
  texlive-xetex \
  texlive-fonts-extra \
  texlive-lang-cjk \
  fonts-noto-cjk \
  librsvg2-bin \
  chromium \
  bind9-dnsutils \
  iproute2 \
  iputils-ping \
  && apt-get autoremove -y && apt-get clean -y

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
  && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
  && apt-get update && apt-get install -y google-cloud-cli \
  && apt-get autoremove -y && apt-get clean -y

# Set up bash aliases for convenience
RUN echo 'alias k="kubectl"' >> /home/vscode/.bashrc \
  && echo 'alias ll="ls -lah"' >> /home/vscode/.bashrc \
  && echo 'alias gs="git status"' >> /home/vscode/.bashrc \
  && echo 'alias gp="git pull"' >> /home/vscode/.bashrc

# Add helpful functions
RUN echo 'test-all() { ./scripts/test-endpoints.sh; }' >> /home/vscode/.bashrc \
  && echo 'deploy-aws() { cd infrastructure/pulumi/aws && pulumi up; }' >> /home/vscode/.bashrc \
  && echo 'deploy-azure() { cd infrastructure/pulumi/azure && pulumi up; }' >> /home/vscode/.bashrc \
  && echo 'deploy-gcp() { cd infrastructure/pulumi/gcp && pulumi up; }' >> /home/vscode/.bashrc

WORKDIR /workspace
