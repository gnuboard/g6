#!/bin/bash
set -e
apt-get update -qq
apt-get install -y -qq \
  wget gnupg fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
  libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 \
  libnss3 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 xdg-utils
wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y /tmp/chrome.deb
pip install -r requirements.txt
