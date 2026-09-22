from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_SEED_COA_PATH = Path(__file__).with_name("seed_coa.json")


@lru_cache(maxsize=1)
def load_default_coa_seed() -> dict[str, Any]:
    with _SEED_COA_PATH.open(encoding="utf-8") as seed_file:
        seed = json.load(seed_file)

    accounts = seed.get("accounts")
    if not isinstance(accounts, list):
        raise ValueError("Invalid COA seed: missing accounts list")

    codes: set[str] = set()
    for account in accounts:
        code = account.get("coa_code")
        if not code:
            raise ValueError("Invalid COA seed: account missing coa_code")
        if code in codes:
            raise ValueError(f"Invalid COA seed: duplicate coa_code {code}")
        codes.add(code)

    for account in accounts:
        parent_code = account.get("parent_code")
        if parent_code and parent_code not in codes:
            raise ValueError(f"Invalid COA seed: parent_code {parent_code} not found")

    return seed


def default_coa_templates() -> list[dict[str, Any]]:
    return list(load_default_coa_seed()["accounts"])


def default_coa_seed_version() -> str:
    return str(load_default_coa_seed().get("version") or "v1")
