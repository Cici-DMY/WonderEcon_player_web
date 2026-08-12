from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_EMPLOYMENT = "employment"
WAGE_FLOOR = 1000.0
WAGE_REF_FALLBACK = 5000.0

WAGE_BANDS = {
    1: (0.90, 0.95),
    2: (0.95, 0.99),
    3: (0.99, 1.04),
    4: (1.04, 1.12),
    5: (1.12, 1.25),
}

def _load_json(p):
    if isinstance(p, dict):
        return p
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _market_avg_wage(env, selected_tick):
    data = _load_json(env)
    snap = data
    if "ticks" in data:
        t0 = selected_tick - 1
        snap = next((r["tick_start"] for r in data.get("ticks", []) if r.get("tick") == t0), None)
        if snap is None:
            raise KeyError(f"Environment data has no record for tick={t0}")
    return snap.get("last_avg_household_wage")

def assign_desired_wage(wage_level: int, ref_wage: float, seed: int | None = None) -> float:
    if wage_level not in WAGE_BANDS:
        raise ValueError(f"wage_level must be 1~5, got {wage_level}")
    lo, hi = WAGE_BANDS[wage_level]
    rng = random.Random(seed) if seed is not None else random
    return max(WAGE_FLOOR, round(rng.uniform(lo * ref_wage, hi * ref_wage), 2))

def apply_employment_decision(
    wage_level: int,
    quit: bool = False,
    player_path: str = DEFAULT_PLAYER_PATH,
    env_path: str = DEFAULT_ENV_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    if not os.path.isfile(player_path):
        raise FileNotFoundError(f"Player JSON not found: {player_path}")
    player = _load_json(player_path)
    if TASK_EMPLOYMENT not in player.get("available_tasks", []):
        raise ValueError("This player does not have an employment decision task.")

    attrs = player.setdefault("attributes", {})
    selected_tick = player.get("selected_tick", 1)
    last_wage = attrs.get("last_wage", 0.0) or 0.0
    ref_wage = last_wage if last_wage > 0 else (_market_avg_wage(env_path, selected_tick) or WAGE_REF_FALLBACK)

    desired_wage = assign_desired_wage(wage_level, ref_wage, seed=seed)
    attrs["desired_wage"] = desired_wage

    was_employed = bool(attrs.get("is_employed"))
    quit_applicable = was_employed
    quit_effective = bool(quit) and was_employed
    if quit_effective:
        attrs["is_employed"] = False
        attrs["employer_id"] = None

    player["employment_decision"] = {
        "wage_level": wage_level,
        "ref_wage": round(ref_wage, 2),
        "desired_wage": desired_wage,
        "quit_applicable": quit_applicable,
        "quit": (bool(quit) if quit_applicable else None),
        "quit_effective": quit_effective,
        "was_employed": was_employed,
    }

    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return player

def _pbool(s):
    return str(s).strip().lower() in ("1", "true", "t", "yes", "y", "resign", "yes")

def main():
    ap = argparse.ArgumentParser(description="Employment decision -> write back to player.json")
    ap.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4, 5], help="Desired wage level")
    ap.add_argument("--quit", type=str, default="no",
                    help="Whether to resign voluntarily: yes/no (unemployed players skip this, optional)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    player = apply_employment_decision(a.level, _pbool(a.quit), a.player, a.env, a.seed)
    d = player["employment_decision"]
    if not d["quit_applicable"]:
        quit_str = "Unemployed player (no resignation question, entering labor market directly)"
    else:
        quit_str = "Voluntary resignation" if d["quit"] else "Not resigning"
        if d["quit_effective"]:
            quit_str += " (set to unemployed, will enter labor market)"
    print(f"Desired wage level {d['wage_level']} | Ref wage {d['ref_wage']:,.0f} -> Desired monthly salary {d['desired_wage']:,.0f} yuan | {quit_str}")
    print(f"Written back to {a.player}")

if __name__ == "__main__":
    main()
