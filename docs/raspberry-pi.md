# Raspberry Pi: current setup and fresh install

The dashboard runs on a headless Raspberry Pi connected to a portrait screen, with a USB keyboard to type
order numbers or times. This page records how the current Pi is set up (inspected on 2026-10-11) and how to
set up a fresh one on Raspberry Pi OS based on Debian 13 "trixie".

Files used for the setup live in [`deploy/`](../deploy):

| File | Goes to | Purpose |
|---|---|---|
| `setup-pi.sh` | run once on the Pi | installs packages, code, `.env`, Kivy settings and the service |
| `dashboard-kivy.service` | `/etc/systemd/system/` | starts the dashboard at boot and restarts it after a crash |
| `kivy-config.ini` | `~/.kivy/config.ini` | full screen, rotated to portrait, no mouse cursor |

## Current Pi

| What | Setting |
|---|---|
| Hardware | Raspberry Pi 4 Model B Rev 1.5, 2 GB RAM |
| OS | Raspberry Pi OS Lite 64-bit, Debian 12 "bookworm" (image 2023-10-10), no desktop |
| Hostname | `pi-order-monitor` (also reachable as `pi-order-monitor.local` via avahi) |
| User | `scouts`, passwordless `sudo`, SSH with password or key |
| Time | `Europe/Brussels`, NTP sync. The Pi has no clock battery, so the time is only right once it reached the internet; wait times depend on it |
| Locale | `en_GB.UTF-8`, WiFi country `BE` (`cfg80211.ieee80211_regdom=BE` in `cmdline.txt`) |
| Network | NetworkManager, WiFi on `wlan0` with saved networks `WVB` and `Hoepahoppa`; the Ethernet port is unused |
| Bluetooth | off (`dtoverlay=disable-bt` in `config.txt`) |
| Screen | 1920x1080 HDMI screen on the **second HDMI port** (`HDMI-A-2`, the one furthest from the USB-C power), turned to portrait by Kivy (`rotation = 270`) |
| Keyboard | USB keyboard "SIGMACHIP USB Keyboard" |
| Drawing | no X/Wayland: Kivy draws straight to the screen (SDL2 on KMS/DRM, `dtoverlay=vc4-kms-v3d`). The user needs the `video`, `render` and `input` groups |
| App | `~/order-dashboard`, a git clone of this repo, started by `dashboard-kivy.service` as user `scouts` with the system Python and Debian's `python3-kivy` 2.1.0, `python3-pandas` 1.5.3, `python3-requests`, `python3-openpyxl` |
| Read-only | `overlayroot` package with `overlayroot=tmpfs` in `cmdline.txt`: every change to the SD card is kept in RAM and lost at reboot; `/boot/firmware` is mounted read-only |

Leftovers that are not needed on a new Pi:

- `video=HDMI-A-1:1280x1024M@60,rotate=270` in `cmdline.txt`. It targets the unused first HDMI port; the rotation is done by Kivy.
- Many packages from earlier experiments (GPIO, camera, build tools). The dashboard only needs the ones `setup-pi.sh` installs.
- The old code version has the Billy password in `config.py`; the current code reads it from `.env`.

## Fresh install on Debian 13 (trixie)

Debian 13 ships Kivy 2.3.1 as a normal package, which the current code needs (Debian 12 only has 2.1.0).
Use a **new SD card** and keep the old one: if anything goes wrong, swap the old card back in.

### 1. Flash the SD card

In Raspberry Pi Imager choose **Raspberry Pi OS Lite (64-bit)** (the trixie-based release). Under
"Edit settings" / customisation set:

- hostname `pi-order-monitor`
- user `scouts` with a password
- WiFi: one of the networks (e.g. `WVB`) and country `BE`
- time zone `Europe/Brussels`, keyboard layout
- SSH enabled, preferably with your public key

### 2. Log in and add the other WiFi network

```bash
ssh scouts@pi-order-monitor.local
# Adding it this way works even when the network is out of range
sudo nmcli connection add type wifi con-name Hoepahoppa ssid Hoepahoppa \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk 'WIFI-PASSWORD'
```

### 3. Run the setup script

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/MertenF/order-dashboard.git ~/order-dashboard
bash ~/order-dashboard/deploy/setup-pi.sh
sudo reboot
```

The script asks for the Billy manager e-mail and password once and stores them in `~/order-dashboard/.env`
(readable only by `scouts`, never committed).

### 4. Optional extras from the old Pi

- Bluetooth off: add `dtoverlay=disable-bt` under `[all]` in `/boot/firmware/config.txt`.
- Read-only system: see [Read-only overlay](#read-only-overlay). Do this last, once everything works.

### 5. Check

| Check | How |
|---|---|
| Service runs | `systemctl status dashboard-kivy` and `journalctl -u dashboard-kivy -b` (look for `Window: Provider: sdl2` and no tracebacks) |
| Screen | full screen, portrait, no cursor; clock top left, four products, bottom line with `Update hh:mm:ss`, IP and WiFi bars |
| Billy | the bottom line shows a recent `Update` time, not red `Nog geen data` / `Offline sinds` |
| Keyboard | type an order number or a time (`1830`) and Enter: the header shows `Na #...` / `Na 18:30` |
| Network icon | WiFi bars; with a network cable plugged in the plug icon; with no network a red cross |
| Clock | `timedatectl` shows `System clock synchronized: yes` |
| Reboot | after `sudo reboot` the dashboard comes back by itself |

Debian 13 also brings Python 3.13, pandas 2 and numpy 2. The code has not been run on those yet, so watch the
journal for errors during the first test.

## Read-only overlay

The old Pi keeps the SD card read-only so a power cut can't corrupt it, with all writes going to RAM. Turn it
on with `sudo raspi-config` → *Performance Options* → *Overlay File System* (also make the boot partition
read-only when asked), then reboot. `findmnt /` shows `overlayroot` when it is active.

While it is on, **changes are lost at reboot**, including `git pull`, `.env` and settings. To change
something: turn the overlay off in the same menu, reboot, make the change, turn it on again and reboot.

## Updating the code

```bash
ssh scouts@pi-order-monitor.local
cd ~/order-dashboard && git pull
sudo cp deploy/dashboard-kivy.service /etc/systemd/system/ && sudo systemctl daemon-reload   # only if it changed
sudo systemctl restart dashboard-kivy
```

With the read-only overlay on, turn it off first (see above).

## Troubleshooting

| Problem | Look at |
|---|---|
| Black screen | `journalctl -u dashboard-kivy -b`. Only one program can use the screen at a time, so stop the service before starting `main.py` by hand. Check `id scouts` lists `video` and `render` |
| Keyboard does nothing | `scouts` must be in the `input` group; the cursor must be in the order box (it is focused at start) |
| `Nog geen data` / `Offline sinds` | network (bottom right icon), the `.env` credentials, `journalctl` for `Login has failed` |
| Wrong wait times | `timedatectl`: the clock is only right after NTP sync |
| Tiny layout in a corner | `DASHBOARD_SCALE=1` missing from the service |
