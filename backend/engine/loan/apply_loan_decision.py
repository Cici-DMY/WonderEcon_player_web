from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "match_agent", "player.json")
)
DEFAULT_ENV_PATH = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "results", "information_environment.json")
)

TASK_LOAN = "loan"
LOAN_RATE_FLOOR = 0.005

EXPECTATION_BANDS: dict[int, tuple[float, float]] = {
    1: (0.935, 0.975),
    2: (0.975, 1.015),
    3: (1.015, 1.055),
    4: (1.055, 1.095),
    5: (1.095, 1.135),
}

def _load_json(path_or_dict: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path_or_dict, dict):
        return path_or_dict
    if not os.path.isfile(path_or_dict):
        raise FileNotFoundError(f"JSON file not found: {path_or_dict}")
    with open(path_or_dict, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_market_loan_rate(env: str | dict[str, Any], selected_tick: int) -> float:
    data = _load_json(env)
    snap = data
    if "ticks" in data:
        tick_0based = selected_tick - 1
        snap = next(
            (r["tick_start"] for r in data.get("ticks", []) if r.get("tick") == tick_0based),
            None,
        )
        if snap is None:
            raise KeyError(f"Environment data has no record for tick={tick_0based}")
    rate = snap.get("last_avg_bank_loan_rate")
    if not rate or rate <= 0:
        raise ValueError("Environment snapshot is missing a valid last_avg_bank_loan_rate")
    return float(rate)

def assign_loan_rate_by_expectation(
    level: int, market_rate: float, seed: int | None = None
) -> float:
    if level not in EXPECTATION_BANDS:
        raise ValueError(f"level must be 1~5, got {level}")
    if not market_rate or market_rate <= 0:
        raise ValueError(f"market_rate must be positive, got {market_rate}")
    lo_mult, hi_mult = EXPECTATION_BANDS[level]
    rng = random.Random(seed) if seed is not None else random
    raw = rng.uniform(lo_mult * market_rate, hi_mult * market_rate)
    return max(LOAN_RATE_FLOOR, round(raw, 4))

def apply_loan_decision(
    rate_level: int,
    decide_loan: bool,
    player_path: str = DEFAULT_PLAYER_PATH,
    env_path: str = DEFAULT_ENV_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    if not os.path.isfile(player_path):
        raise FileNotFoundError(f"Player JSON not found: {player_path}")
    player = _load_json(player_path)

    if TASK_LOAN not in player.get("available_tasks", []):
        raise ValueError("This player is not eligible for a loan; loan decision should not be applied.")

    selected_tick = player.get("selected_tick", 1)
    market_rate = _get_market_loan_rate(env_path, selected_tick)
    desired_rate = assign_loan_rate_by_expectation(rate_level, market_rate, seed=seed)

    attrs = player.setdefault("attributes", {})
    attrs["desired_loan_rate"] = desired_rate
    attrs["current_decide_loan"] = bool(decide_loan)
    if not decide_loan:
        attrs["current_loan_amount"] = 0.0

    player["loan_decision"] = {
        "expectation_level": rate_level,
        "market_rate": round(market_rate, 4),
        "desired_loan_rate": desired_rate,
        "decide_loan": bool(decide_loan),
    }

    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)

    return player

def _parse_bool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "t", "yes", "y", "borrow", "yes")

def main() -> None:
    parser = argparse.ArgumentParser(description="Loan decision (two questions) -> update params and write back to player.json")
    parser.add_argument(
        "--level", type=int, required=True, choices=[1, 2, 3, 4, 5],
        help="Q1: Interest rate expectation level (1=significant decrease ... 5=significant increase)",
    )
    parser.add_argument(
        "--borrow", type=str, required=True,
        help="Q2: Whether to borrow: yes/no",
    )
    parser.add_argument("--player", type=str, default=DEFAULT_PLAYER_PATH)
    parser.add_argument("--env", type=str, default=DEFAULT_ENV_PATH)
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    args = parser.parse_args()

    player = apply_loan_decision(
        rate_level=args.level,
        decide_loan=_parse_bool(args.borrow),
        player_path=args.player,
        env_path=args.env,
        seed=args.seed,
    )
    d = player["loan_decision"]
    print(
        f"Rate expectation level {d['expectation_level']} | Last month market rate {d['market_rate']*100:.2f}% "
        f"-> Desired loan rate {d['desired_loan_rate']*100:.2f}% | "
        f"Borrow: {'yes' if d['decide_loan'] else 'no'}"
        + ("" if d["decide_loan"] else " (loan amount set to 0)")
    )
    print(f"Written back to {args.player}")

if __name__ == "__main__":
    main()
