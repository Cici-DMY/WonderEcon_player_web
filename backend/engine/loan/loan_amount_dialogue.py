from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "match_agent", "player.json")
)
DEFAULT_ENV_PATH = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "results", "information_environment.json")
)

TASK_LOAN = "loan"
LOAN_PCT_MIN = 0.05
LOAN_PCT_MAX = 0.50

CN_ECONOMIC_BACKGROUND: dict[int, str] = {
    0: "The economy is slightly overheated, real estate is booming.",
    1: "The economy is running at a high level, prices are starting to rise.",
    2: "Demand is still high, but momentum is slowing.",
    3: "Prices are rising faster and faster.",
    4: "Inflationary pressure is increasing.",
    5: "The economy is fully overheated, prices are very high.",
    6: "Prices are surging more fiercely, inflation is worsening.",
    7: "The economy is showing stagflation signs - things are expensive and people can barely afford to buy.",
    8: "High prices persist.",
    9: "The economy is cooling down, but prices remain high.",
    10: "Stagflation worsens, demand shrinks significantly.",
    11: "Prices are peaking, but the real economy is weakening.",
    12: "Demand is contracting across the board.",
}

WEALTH_PLAIN: dict[int, str] = {
    5: "very high (top 20% of total assets)",
    4: "fairly high (top 20%~40%)",
    3: "average (middle 40%~60%)",
    2: "somewhat low (bottom 20%~40%)",
    1: "very low (bottom 20%)",
}

RISK_PLAIN: dict[str, str] = {
    "conservative": "conservative and cautious, afraid of losing money",
    "steady": "steady and practical, does things carefully",
    "balanced": "balanced between offense and defense",
    "growth": "growth-oriented, willing to take some risks",
    "aggressive": "bold and aggressive, pursues high returns",
}

def _money(x: float | None) -> str:
    return "—" if x is None else f"{x:,.0f} yuan"

def _beta_plain(beta: float | None) -> str:
    if beta is None:
        return "unknown"
    if beta >= 1.6:
        return "very strong"
    if beta >= 1.3:
        return "fairly strong"
    if beta >= 0.8:
        return "moderate"
    if beta >= 0.4:
        return "somewhat weak"
    return "fairly weak"

def _pct(rate: float | None) -> str:
    return "—" if rate is None else f"{rate * 100:.2f}%"

def _load_json(path_or_dict: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path_or_dict, dict):
        return path_or_dict
    if not os.path.isfile(path_or_dict):
        raise FileNotFoundError(f"JSON file not found: {path_or_dict}")
    with open(path_or_dict, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_env_snapshot(env: str | dict[str, Any], selected_tick: int) -> dict[str, Any]:
    data = _load_json(env)
    if "ticks" not in data:
        return data
    tick_0based = selected_tick - 1
    for rec in data.get("ticks", []):
        if rec.get("tick") == tick_0based:
            return rec["tick_start"]
    raise KeyError(f"Environment data has no record for tick={tick_0based}")

def build_loan_amount_dialogue(
    player: str | dict[str, Any],
    env: str | dict[str, Any],
) -> str:
    player_data = _load_json(player)
    attributes: dict[str, Any] = player_data.get("attributes", {})
    selected_tick: int = player_data.get("selected_tick", 1)
    available_tasks: list[str] = player_data.get("available_tasks", [])

    if TASK_LOAN not in available_tasks:
        return "(Your character is not eligible for a loan and will not enter this dialogue.)"

    env_snapshot = _get_env_snapshot(env, selected_tick)

    risk = attributes.get("risk_preference", "balanced")
    beta = attributes.get("beta")
    wealth = attributes.get("wealth_level", 3)
    had_loan = bool(attributes.get("last_has_loan"))
    last_loan_rate = attributes.get("last_loan_rate")
    extra_subsidy = bool(attributes.get("government_extra_subsidy"))

    last_wage = attributes.get("last_wage", 0.0) or 0.0
    available = attributes.get("total_available_funds", 0.0) or 0.0
    market_loan_rate = env_snapshot.get("last_avg_bank_loan_rate")
    tick0 = env_snapshot.get("current_tick", selected_tick - 1)

    chosen_rate = (player_data.get("loan_decision") or {}).get("desired_loan_rate")

    min_loan = last_wage * LOAN_PCT_MIN
    max_loan = last_wage * LOAN_PCT_MAX
    rate_str = _pct(market_loan_rate) if market_loan_rate else "current market rate"

    lines: list[str] = []
    lines.append("[Commercial Bank - Loan Window]")
    lines.append("")
    lines.append("(The loan officer opens your file)")
    lines.append("")
    lines.append("'Alright, you've decided to borrow! Let's determine how much.'")
    lines.append("")

    if chosen_rate:
        rate_sentence = (
            f"The rate you chose earlier is about {_pct(chosen_rate)} (last month's market average was {rate_str}). "
        )
    else:
        rate_sentence = f"Last month the average borrowing rate was about {rate_str}. "

    lines.append(
        f"'Your monthly salary is {_money(last_wage)}, **minimum loan {_money(min_loan)} (5% of salary), maximum loan {_money(max_loan)} (half of salary)**. "
        f"You **currently have {_money(available)}**, and the loan amount will be added on top. "
        f"{rate_sentence}**{CN_ECONOMIC_BACKGROUND.get(tick0, '')}**'"
    )
    lines.append("")
    lines.append(
        "'Three reminders: first, borrowed money **can only be spent, not saved or invested**; "
        "second, **the more you borrow, the more you repay next month**; "
        "third, after borrowing most of the money must be spent, **and the rest goes to stocks -- gains and losses are possible**.'"
    )
    lines.append("")
    lines.append("'How much do you want to borrow? Let me know.'")

    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Loan amount ratio - Bank NPC dialogue generator (standalone module)")
    parser.add_argument(
        "--player", type=str, default=DEFAULT_PLAYER_PATH,
        help=f"Player JSON path (default {DEFAULT_PLAYER_PATH})",
    )
    parser.add_argument(
        "--env", type=str, default=DEFAULT_ENV_PATH,
        help=f"information_environment.json path (default {DEFAULT_ENV_PATH})",
    )
    args = parser.parse_args()
    print(build_loan_amount_dialogue(args.player, args.env))

if __name__ == "__main__":
    main()
