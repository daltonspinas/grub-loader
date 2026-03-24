from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Response

from app.models import OneShotRequest, StateResponse
from app.state_store import ConfigStore

DATA_DIR = os.getenv("DATA_DIR", "./data")
FALLBACK_ALIAS = os.getenv("FALLBACK_ALIAS", "ubuntu")

app = FastAPI(title="grub-loader", version="0.1.0")
store = ConfigStore(data_dir=DATA_DIR, fallback_alias=FALLBACK_ALIAS)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/boot.cfg")
def boot_cfg() -> Response:
    try:
        alias, target, consumed = store.consume_alias_or_fallback()
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    marker = "consumed-oneshot" if consumed else "fallback"
    cfg = "\n".join(
        [
            f"# alias={alias}",
            f"# mode={marker}",
            f"set default=\"{target}\"",
            "# Prefer local GRUB prefix path; fall back to absolute path.",
            "if [ -s ${prefix}/grub.cfg ]; then",
            "  configfile ${prefix}/grub.cfg",
            "else",
            "  configfile /boot/grub/grub.cfg",
            "fi",
            "",
        ]
    )
    return Response(content=cfg, media_type="text/plain")


@app.get("/state", response_model=StateResponse)
def get_state() -> StateResponse:
    aliases = store.get_aliases()
    state = store.get_state()

    pending_alias = state["pending_alias"]
    pending_target = aliases.get(pending_alias) if pending_alias else None

    fallback_target = aliases.get(FALLBACK_ALIAS)
    if not fallback_target:
        raise HTTPException(
            status_code=500,
            detail=f"Fallback alias '{FALLBACK_ALIAS}' missing in aliases.json",
        )

    return StateResponse(
        fallback_alias=FALLBACK_ALIAS,
        fallback_target=fallback_target,
        pending_alias=pending_alias,
        pending_target=pending_target,
        updated_at=state["updated_at"],
    )


@app.post("/oneshot")
def set_oneshot(payload: OneShotRequest) -> dict[str, str]:
    alias = payload.alias.strip().lower()
    try:
        store.set_pending_alias(alias)
    except KeyError as exc:
        aliases = sorted(store.get_aliases().keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown alias '{alias}'. Allowed aliases: {', '.join(aliases)}",
        ) from exc

    return {
        "status": "queued",
        "alias": alias,
        "message": "One-shot boot target queued and will be consumed by next /boot.cfg read",
    }
