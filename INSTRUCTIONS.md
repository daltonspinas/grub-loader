# grub-loader Build, Deploy, and Test Instructions

This guide covers local build/test, TrueNAS docker deployment, GRUB discovery, and installing the network loader menu entry on Ubuntu.

## 1. Prerequisites

- Ubuntu machine with GRUB controlling boot.
- TrueNAS host reachable from Ubuntu at `192.168.1.128`.
- Docker with compose support on the deployment host.
- Access to edit GRUB files on Ubuntu with sudo.

## 2. Get your current GRUB setup details

Run these commands on Ubuntu and save output for alias mapping:

```bash
sudo cp /boot/grub/grub.cfg /tmp/grub.cfg.backup.$(date +%F-%H%M%S)
grep "^menuentry " /boot/grub/grub.cfg
sudo awk -F\' '/menuentry / {print $2}' /boot/grub/grub.cfg
sudo grep -E '^(GRUB_DEFAULT|GRUB_TIMEOUT|GRUB_TIMEOUT_STYLE)=' /etc/default/grub
```

Or use the helper script in this repo to inspect entries and generate a suggested aliases file:

```bash
bash scripts/generate_aliases_from_grub.sh
bash scripts/generate_aliases_from_grub.sh --write data/aliases.json
```

What you need from this step:

- Exact menu entry labels, for example Ubuntu, Windows Boot Manager, Bazzite.
- Current default and timeout values before changes.

## 3. Configure alias mapping in this project

Edit [data/aliases.json](data/aliases.json) so values exactly match the GRUB menu labels you collected:

```json
{
  "ubuntu": "Ubuntu",
  "windows": "Windows Boot Manager (on /dev/nvme0n1p1)",
  "bazzite": "Bazzite"
}
```

Notes:

- Keys are your stable API aliases.
- Values must match GRUB menu labels exactly.
- Review helper output before writing, especially if you have multiple Ubuntu or Windows entries.

## 4. Build and run locally (developer test)

From project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8086
```

In another shell, test endpoints:

```bash
curl -sS http://127.0.0.1:8086/healthz
curl -sS http://127.0.0.1:8086/state
curl -sS -X POST http://127.0.0.1:8086/oneshot -H 'Content-Type: application/json' -d '{"alias":"windows"}'
curl -sS http://127.0.0.1:8086/boot.cfg
curl -sS http://127.0.0.1:8086/boot.cfg
```

Expected one-shot behavior:

1. First `GET /boot.cfg` after posting `windows` returns windows target.
2. Second `GET /boot.cfg` returns ubuntu fallback.

## 5. Deploy service with docker compose

From project root:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=100 grub-loader
```

Endpoint checks from Ubuntu (or any LAN host):

```bash
curl -sS http://192.168.1.128:8086/healthz
curl -sS http://192.168.1.128:8086/state
```

## 6. Install network loader entry into GRUB on Ubuntu

Edit `/etc/grub.d/40_custom` and append:

```bash
menuentry "Network-controlled boot (auto)" {
    insmod net
    insmod http
    insmod efinet

    if dhcp; then
        configfile (http,192.168.1.128:8086)/boot.cfg
    else
        configfile /boot/grub/grub.cfg
    fi
}
```

If BIOS boot is used, replace `efinet` with `biosnet`.

Update `/etc/default/grub` and set:

```bash
GRUB_DEFAULT="Network-controlled boot (auto)"
GRUB_TIMEOUT=2
```

Apply changes:

```bash
sudo update-grub
```

Verify the new menu entry is present:

```bash
grep -n "Network-controlled boot (auto)" /boot/grub/grub.cfg
```

## 7. End-to-end functional test (no reboot yet)

Queue one-shot windows and inspect returned cfg:

```bash
curl -sS -X POST http://192.168.1.128:8086/oneshot -H 'Content-Type: application/json' -d '{"alias":"windows"}'
curl -sS http://192.168.1.128:8086/boot.cfg
curl -sS http://192.168.1.128:8086/boot.cfg
```

Confirm:

- First read includes `set default="<windows label>"`.
- Second read includes `set default="<ubuntu label>"`.

## 8. Reboot test

1. Queue one-shot target.
2. Reboot Ubuntu host once.
3. Confirm it boots into requested one-shot target.
4. Reboot again without posting a target.
5. Confirm fallback is Ubuntu.

## 9. Troubleshooting

- GRUB cannot fetch remote cfg:
  - Confirm service reachable: `curl http://192.168.1.128:8086/healthz`.
  - Confirm DHCP works in GRUB environment.
  - Try changing `efinet` to `biosnet` if system is BIOS mode.
- Wrong boot target chosen:
  - Re-check exact labels in `/boot/grub/grub.cfg`.
  - Update [data/aliases.json](data/aliases.json) and restart container.
- Need rollback:
  - Restore original `GRUB_DEFAULT` in `/etc/default/grub`.
  - Run `sudo update-grub`.

## 10. Home Assistant writer example

Use [examples/home_assistant.yaml](examples/home_assistant.yaml) as template. It posts alias names (for example `windows`) to `/oneshot`.
