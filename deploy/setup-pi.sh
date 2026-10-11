#!/bin/bash
# Set up the order dashboard on a fresh headless Raspberry Pi OS Lite (64-bit).
# See docs/raspberry-pi.md. Run as the 'scouts' user, from anywhere:
#   bash setup-pi.sh
# Safe to run again; existing files are kept unless noted.
set -euo pipefail

REPO_URL=https://github.com/MertenF/order-dashboard.git
APP_DIR=/home/scouts/order-dashboard
DEPLOY_DIR="$APP_DIR/deploy"

if [ "$(id -un)" != scouts ]; then
    echo "Run this as the 'scouts' user (the service runs as scouts)." >&2
    exit 1
fi

echo "== Packages"
sudo apt-get update
sudo apt-get install -y git python3-kivy python3-requests

echo "== Code"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "== Billy credentials (.env)"
if [ -f "$APP_DIR/.env" ]; then
    echo ".env already exists, keeping it"
else
    read -rp "Billy manager e-mail: " billy_user
    read -rsp "Billy manager password: " billy_password
    echo
    printf 'BILLY_USERNAME=%s\nBILLY_PASSWORD=%s\n' "$billy_user" "$billy_password" > "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
fi

echo "== Kivy screen settings"
mkdir -p ~/.kivy
if [ -f ~/.kivy/config.ini ]; then
    echo "~/.kivy/config.ini already exists, keeping it (compare with $DEPLOY_DIR/kivy-config.ini)"
else
    cp "$DEPLOY_DIR/kivy-config.ini" ~/.kivy/config.ini
fi

echo "== Access to screen and keyboard without a desktop"
sudo usermod -aG video,render,input scouts

echo "== Service"
sudo cp "$DEPLOY_DIR/dashboard-kivy.service" /etc/systemd/system/dashboard-kivy.service
sudo systemctl daemon-reload
sudo systemctl enable dashboard-kivy.service

echo
echo "Done. Reboot to start the dashboard: sudo reboot"
echo "Afterwards, optionally make the system read-only (see docs/raspberry-pi.md, 'Read-only overlay')."
