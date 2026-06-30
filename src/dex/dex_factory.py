"""Factory for DexSession."""

from __future__ import annotations

import json
import logging

from core.account_store import AccountConfig
from core.paths import (
    AREA_INDEX_PATH,
    LOCATION_INDEX_PATH,
    LEGENDARIES_PATH,
    USERDATA,
)
from dex.dex_session import DexSession
from dex.dex_structures import CaughtStore, EncounterData

log = logging.getLogger(__name__)


def build_dex_session(account_override: str | None) -> DexSession | None:
    """Build the dex session for the active account, or None if the encounter
    data is missing. The active account is chosen manually and remembered: an
    explicit --account wins, else the last used one, else a 'default' profile."""
    if not LOCATION_INDEX_PATH.exists():
        log.info("dex: location_index.json not found (run scripts/update_data.py) — dex disabled")
        return None
    data = EncounterData.load(LOCATION_INDEX_PATH, LEGENDARIES_PATH)

    raw_idx = json.loads(AREA_INDEX_PATH.read_text("utf-8"))
    area_index = {loc: region for region, locs in raw_idx.items() for loc in locs}

    cfg = AccountConfig.load(USERDATA)
    account = cfg.resolve_active(account_override)
    if account is None:
        account = cfg.use("default")
        log.info("dex: no account set — using 'default' (pass --account NAME per character)")
    caught = CaughtStore.for_account(USERDATA, account)
    log.info(f"dex: account '{account}' — {len(caught.caught)} species marked caught")
    return DexSession(data, caught, area_index)
