# grub-loader MVP

Minimal one-shot GRUB target service for a homelab.

## What this does

- Home Assistant writes one-shot target aliases such as `windows`.
- GRUB reads `/boot.cfg` from this service over LAN HTTP.
- The service returns the queued target once, then resets to fallback `ubuntu`.

## API

- `GET /healthz`: liveness endpoint.
- `GET /state`: current pending alias and fallback details.
- `GET /boot.cfg`: returns a plain GRUB fragment and consumes pending one-shot alias.
- `POST /oneshot`: queue one-shot alias.

### Set one-shot target example

```bash
curl -sS -X POST http://192.168.1.128:8086/oneshot \
  -H 'Content-Type: application/json' \
  -d '{"alias":"windows"}'
```

### Read boot config example

```bash
curl -sS http://192.168.1.128:8086/boot.cfg
```

## Alias map and state

- `data/aliases.json`: alias to exact GRUB menu entry string.
- `data/state.json`: pending one-shot alias and timestamp.

Helper script to detect menu entries and suggest alias mapping:

```bash
bash scripts/generate_aliases_from_grub.sh
bash scripts/generate_aliases_from_grub.sh --write data/aliases.json
```

Update aliases to match your exact local GRUB menu strings, for example:

```json
{
  "ubuntu": "Ubuntu",
  "windows": "Windows Boot Manager (on /dev/nvme0n1p1)",
  "bazzite": "Bazzite"
}
```

## Deploy with docker compose

```bash
cd /home/dalton/repos/grub-loader
docker compose up -d --build
```

## Ubuntu GRUB integration

1. Add a menu entry in `/etc/grub.d/40_custom`:

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

2. Set this entry as default path in `/etc/default/grub`:

```bash
GRUB_DEFAULT="Network-controlled boot (auto)"
GRUB_TIMEOUT=2
```

3. Rebuild config:

```bash
sudo update-grub
```

## Verify one-shot behavior

1. Queue alias `windows` with `POST /oneshot`.
2. First `GET /boot.cfg` should return `set default="...windows..."`.
3. Second `GET /boot.cfg` should return fallback `ubuntu`.

## Notes

- This MVP uses plain HTTP on LAN with no API auth.
- Hardening later can add TLS, authentication, per-host state, and audit logs.
