#!/usr/bin/env bash
set -euo pipefail

GRUB_CFG="/boot/grub/grub.cfg"
OUT_FILE=""

usage() {
  cat <<'EOF'
Usage:
  scripts/generate_aliases_from_grub.sh [--grub-cfg /path/to/grub.cfg] [--write data/aliases.json]

Description:
  - Reads GRUB menuentry labels from grub.cfg
  - Prints detected labels with indexes
  - Prints suggested aliases.json content
  - Optionally writes the suggested JSON to a file

Options:
  --grub-cfg PATH   Path to grub.cfg (default: /boot/grub/grub.cfg)
  --write PATH      Write suggested aliases JSON to PATH
  -h, --help        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --grub-cfg)
      GRUB_CFG="${2:-}"
      shift 2
      ;;
    --write)
      OUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$GRUB_CFG" ]]; then
  echo "grub.cfg not found: $GRUB_CFG" >&2
  exit 1
fi

mapfile -t ENTRIES < <(awk -F"'" '/^[[:space:]]*menuentry / {print $2}' "$GRUB_CFG")

if [[ ${#ENTRIES[@]} -eq 0 ]]; then
  echo "No menuentry labels found in: $GRUB_CFG" >&2
  exit 1
fi

echo "Detected GRUB menu entries from $GRUB_CFG:"
for i in "${!ENTRIES[@]}"; do
  printf '  [%02d] %s\n' "$((i + 1))" "${ENTRIES[$i]}"
done

find_first_match() {
  local pattern="$1"
  local entry
  for entry in "${ENTRIES[@]}"; do
    if [[ "$entry" =~ $pattern ]]; then
      printf '%s' "$entry"
      return 0
    fi
  done
  return 1
}

ubuntu_label=""
windows_label=""
bazzite_label=""

ubuntu_label="$(find_first_match '[Uu]buntu' || true)"
windows_label="$(find_first_match '([Ww]indows|[Ww]indows Boot Manager)' || true)"
bazzite_label="$(find_first_match '[Bb]azzite' || true)"

if [[ -z "$ubuntu_label" ]]; then
  ubuntu_label="Ubuntu"
fi

if [[ -z "$windows_label" ]]; then
  windows_label="Windows Boot Manager"
fi

if [[ -z "$bazzite_label" ]]; then
  bazzite_label="Bazzite"
fi

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

SUGGESTED_JSON="{\n"
SUGGESTED_JSON+="  \"ubuntu\": \"$(json_escape "$ubuntu_label")\",\n"
SUGGESTED_JSON+="  \"windows\": \"$(json_escape "$windows_label")\",\n"
SUGGESTED_JSON+="  \"bazzite\": \"$(json_escape "$bazzite_label")\"\n"
SUGGESTED_JSON+="}"

echo
echo "Suggested aliases.json:"
printf '%b\n' "$SUGGESTED_JSON"

if [[ -n "$OUT_FILE" ]]; then
  mkdir -p "$(dirname "$OUT_FILE")"
  printf '%b\n' "$SUGGESTED_JSON" > "$OUT_FILE"
  echo
  echo "Wrote suggested aliases to $OUT_FILE"
fi
