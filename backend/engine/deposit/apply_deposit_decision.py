from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_DEPOSIT = "deposit"
DEPOSIT_RATE_FLOOR = 0.001

RATE_BANDS = {
    1: (0.98, 1.04),
    2: (1.04, 1.09),
    3: (1.09, 1.14),
    4: (1.14, 1.19),
    5: (1.19, 1.25),
}

def _load_json(p):
    if isinstance(p, dict):
        return p
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _market_deposit_rate(env, selected_tick):
    data = _load_json(env)
    snap = data
    if "ticks" in data:
        t0 = selected_tick - 1
        snap = next((r["tick_start"] for r in data.get("ticks", []) if r.get("tick") == t0), None)
        if snap is None:
            raise KeyError(f"Environment data has no record for tick={t0}")
    return snap.get("last_avg_bank_deposit_rate") or snap.get("current_deposit_1yr") or 0.0225

def assign_deposit_rate(level: int, market_rate: float, seed: int | None = None) -> float:
    if level not in RATE_BANDS:
        raise ValueError(f"level must be 1~5, got {level}")
    lo, hi = RATE_BANDS[level]
    rng = random.Random(seed) if seed is not None else random
    return max(DEPOSIT_RATE_FLOOR, round(rng.uniform(lo * market_rate, hi * market_rate), 4))

def apply_deposit_decision(
    level: int,
    player_path: str = DEFAULT_PLAYER_PATH,
    env_path: str = DEFAULT_ENV_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    if not os.path.isfile(player_path):
        raise FileNotFoundError(f"Player JSON not found: {player_path}")
    player = _load_json(player_path)
    if TASK_DEPOSIT not in player.get("available_tasks", []):
        raise ValueError("This player has no deposit decision task.")

    attrs = player.setdefault("attributes", {})
    market_rate = _market_deposit_rate(env_path, player.get("selected_tick", 1))
    rate = assign_deposit_rate(level, market_rate, seed=seed)
    attrs["desired_deposit_rate"] = rate

    player["deposit_decision"] = {
        "level": level, "market_rate": round(market_rate, 4), "desired_deposit_rate": rate,
    }
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return player

def main():
    ap = argparse.ArgumentParser(description="Desired deposit rate question -> write back to player.json")
    ap.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    p = apply_deposit_decision(a.level, a.player, a.env, a.seed)
    d = p["deposit_decision"]
    print(f"Level {d['level']} | Last period market deposit rate {d['market_rate']*100:.2f}% -> Desired deposit rate {d['desired_deposit_rate']*100:.2f}% (written back)")

if __name__ == "__main__":
    main()
