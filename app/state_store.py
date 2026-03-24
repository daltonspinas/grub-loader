from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ConfigStore:
    def __init__(self, data_dir: str, fallback_alias: str = "ubuntu") -> None:
        self.data_dir = Path(data_dir)
        self.aliases_path = self.data_dir / "aliases.json"
        self.state_path = self.data_dir / "state.json"
        self.fallback_alias = fallback_alias
        self._lock = Lock()

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        if not self.aliases_path.exists():
            default_aliases = {
                "ubuntu": "Ubuntu",
                "windows": "Windows Boot Manager",
                "bazzite": "Bazzite",
            }
            self._write_json_atomic(self.aliases_path, default_aliases)

        if not self.state_path.exists():
            default_state = {
                "pending_alias": None,
                "updated_at": utc_now_iso(),
            }
            self._write_json_atomic(self.state_path, default_state)

    def _write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(path)

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def get_aliases(self) -> dict[str, str]:
        with self._lock:
            data = self._read_json(self.aliases_path)
            return {str(k): str(v) for k, v in data.items()}

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            state = self._read_json(self.state_path)
            return {
                "pending_alias": state.get("pending_alias"),
                "updated_at": str(state.get("updated_at", utc_now_iso())),
            }

    def set_pending_alias(self, alias: str) -> None:
        with self._lock:
            aliases = self._read_json(self.aliases_path)
            if alias not in aliases:
                raise KeyError(alias)

            next_state = {
                "pending_alias": alias,
                "updated_at": utc_now_iso(),
            }
            self._write_json_atomic(self.state_path, next_state)

    def consume_alias_or_fallback(self) -> tuple[str, str, bool]:
        with self._lock:
            aliases = self._read_json(self.aliases_path)
            state = self._read_json(self.state_path)

            pending_alias = state.get("pending_alias")
            if pending_alias and pending_alias in aliases:
                resolved_alias = str(pending_alias)
                was_consumed = True
            else:
                resolved_alias = self.fallback_alias
                was_consumed = False

            if resolved_alias not in aliases:
                raise KeyError(
                    f"Alias '{resolved_alias}' missing from aliases.json. Update aliases.json to include fallback alias."
                )

            if was_consumed:
                next_state = {
                    "pending_alias": None,
                    "updated_at": utc_now_iso(),
                }
                self._write_json_atomic(self.state_path, next_state)

            return resolved_alias, str(aliases[resolved_alias]), was_consumed
