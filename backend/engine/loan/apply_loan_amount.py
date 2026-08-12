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

TASK_LOAN = "loan"
LOAN_PCT_MIN = 0.05
LOAN_PCT_MAX = 0.50

LOAN_AMOUNT_BANDS: dict[int, tuple[float, float]] = {
    1: (0.05, 0.14),
    2: (0.14, 0.23),
    3: (0.23, 0.32),
    4: (0.32, 0.41),
    5: (0.41, 0.50),
}

def _load_json(path_or_dict: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path_or_dict, dict):
        return path_or_dict
    if not os.path.isfile(path_or_dict):
        raise FileNotFoundError(f"JSON file not found: {path_or_dict}")
    with open(path_or_dict, "r", encoding="utf-8") as f:
        return json.load(f)

def assign_loan_ratio(level: int, seed: int | None = None) -> float:
    if level not in LOAN_AMOUNT_BANDS:
        raise ValueError(f"level must be 1~5, got {level}")
    lo, hi = LOAN_AMOUNT_BANDS[level]
    rng = random.Random(seed) if seed is not None else random
    raw = rng.uniform(lo, hi)
    return max(LOAN_PCT_MIN, min(LOAN_PCT_MAX, round(raw, 3)))

def apply_loan_amount(
    level: int,
    player_path: str = DEFAULT_PLAYER_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    if not os.path.isfile(player_path):
        raise FileNotFoundError(f"Player JSON not found: {player_path}")
    player = _load_json(player_path)

    if TASK_LOAN not in player.get("available_tasks", []):
        raise ValueError("This player is not eligible for a loan; loan amount should not be applied.")

    attrs = player.setdefault("attributes", {})

    if not attrs.get("current_decide_loan"):
        raise ValueError("This player did not choose to borrow this month; loan amount should not be applied.")

    last_wage = attrs.get("last_wage", 0.0) or 0.0
    loan_ratio = assign_loan_ratio(level, seed=seed)
    loan_amount = round(last_wage * loan_ratio, 2)

    attrs["current_loan_amount"] = loan_amount
    player["loan_amount_decision"] = {
        "level": level,
        "loan_ratio": loan_ratio,
        "current_loan_amount": loan_amount,
    }

    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)

    return player

def main() -> None:
    parser = argparse.ArgumentParser(description="Loan amount ratio question -> update current_loan_amount and write back to player.json")
    parser.add_argument(
        "--level", type=int, required=True, choices=[1, 2, 3, 4, 5],
        help="Loan amount ratio level (1=borrow very little ... 5=borrow maximum)",
    )
    parser.add_argument("--player", type=str, default=DEFAULT_PLAYER_PATH)
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    args = parser.parse_args()

    player = apply_loan_amount(level=args.level, player_path=args.player, seed=args.seed)
    d = player["loan_amount_decision"]
    print(
        f"Level {d['level']} -> loan ratio {d['loan_ratio']*100:.1f}% (of last wage)"
        f" -> loan amount {d['current_loan_amount']:,.2f} yuan (written back to {args.player})"
    )

if __name__ == "__main__":
    main()
