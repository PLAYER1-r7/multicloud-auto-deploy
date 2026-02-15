FROM mcr.microsoft.com/devcontainers/python:2-3.12-bookworm

# Fix Yarn repository signature issue by removing the repository
# This prevents apt-get update failures during feature installation
RUN rm -f /etc/apt/sources.list.d/yarn.list && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Install Python 3.11 alongside 3.12 for compatibility
RUN apt-get update && \
  apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Install utilities for troubleshooting and PDF generation
RUN apt-get update && \
  apt-get install -y \
  zip \
  unzip \
  tree \
  htop \
  ncdu \
  netcat-openbsd \
  poppler-utils \
  imagemagick \
  pandoc \
  texlive-xetex \
  texlive-fonts-extra \
  texlive-lang-cjk \
  fonts-noto-cjk \
  librsvg2-bin \
  && apt-get clean && \
  rm -rf /var/lib/apt/lists/*
