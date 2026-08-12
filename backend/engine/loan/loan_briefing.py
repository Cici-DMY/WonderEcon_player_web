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

NUM_TICKS = 13
LOAN_MAX_PCT_OF_WAGE = 0.50
TASK_LOAN = "loan"

WEALTH_PLAIN: dict[int, str] = {
    5: "very wealthy",
    4: "fairly comfortable",
    3: "average",
    2: "somewhat tight",
    1: "very poor",
}

RISK_PLAIN: dict[str, str] = {
    "conservative": "conservative and cautious, afraid of losing money, prefers safety",
    "steady": "steady and practical, does things carefully",
    "balanced": "balanced between offense and defense, weighs both returns and risks",
    "growth": "growth-oriented, willing to take some risks for higher returns",
    "aggressive": "bold and aggressive, dares to take risks, pursues high returns",
}

CN_ECONOMIC_BACKGROUND: dict[int, str] = {
    0: "The economy is slightly overheated, real estate is booming, everyone is rushing to invest.",
    1: "The economy is running at a high level, prices are starting to rise (signs of inflation).",
    2: "Demand is still high, but momentum is slowing.",
    3: "Prices are rising faster and faster.",
    4: "Inflationary pressure is increasing.",
    5: "The economy is fully overheated, prices are very high.",
    6: "Prices are surging more fiercely, inflation is clearly worsening.",
    7: "The economy is showing stagflation: things are getting expensive, but people can barely afford to buy.",
    8: "High prices persist.",
    9: "The economy is cooling down, but prices remain high.",
    10: "Stagflation worsens, demand shrinks significantly.",
    11: "Prices are peaking, but the real economy is weakening.",
    12: "Demand is contracting across the board.",
}

HIKE_TICKS: dict[int, tuple[float, float]] = {
    6: (2.50, 5.56),
    9: (2.75, 5.81),
    10: (3.00, 6.06),
    12: (3.25, 6.31),
}

def _money(x: float | None) -> str:
    return "—" if x is None else f"{x:,.0f} yuan"

def _pct(rate: float | None) -> str:
    return "—" if rate is None else f"{rate * 100:.2f}%"

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

def _queue_plain(beta: float | None) -> str:
    if beta is None:
        return "your queue position is uncertain"
    if beta >= 1.6:
        return "you are near the front of the queue"
    if beta >= 1.3:
        return "you are fairly near the front"
    if beta >= 0.8:
        return "you are in the middle of the queue"
    if beta >= 0.4:
        return "you are fairly far back in the queue"
    return "you are near the back of the queue"

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

def build_loan_briefing(
    player: str | dict[str, Any],
    env: str | dict[str, Any],
) -> str:
    player_data = _load_json(player)
    attributes: dict[str, Any] = player_data.get("attributes", {})
    selected_tick: int = player_data.get("selected_tick", 1)
    available_tasks: list[str] = player_data.get("available_tasks", [])

    if TASK_LOAN not in available_tasks:
        return "(Your character is not eligible for a loan this month. You can skip the bank and proceed to the next stop.)"

    env_snapshot = _get_env_snapshot(env, selected_tick)

    wealth = attributes.get("wealth_level", 3)
    risk = attributes.get("risk_preference", "balanced")
    beta = attributes.get("beta")
    extra_subsidy = bool(attributes.get("government_extra_subsidy"))
    last_wage = attributes.get("last_wage", 0.0) or 0.0
    available = attributes.get("total_available_funds", 0.0) or 0.0
    had_loan = bool(attributes.get("last_has_loan"))
    last_loan_rate = attributes.get("last_loan_rate")

    market_loan_rate = env_snapshot.get("last_avg_bank_loan_rate")
    tick0 = env_snapshot.get("current_tick", selected_tick - 1)
    player_tick = tick0 + 1

    loan_cap = last_wage * LOAN_MAX_PCT_OF_WAGE

    lines: list[str] = []
    lines.append("[Commercial Bank - Loan Window]")
    lines.append("")
    lines.append("(The bank manager smiles and hands you a glass of water)")
    lines.append("")
    lines.append("'Welcome! Have a seat, let me look at your situation.'")
    lines.append("")

    loan_history = f"Last month you borrowed once, at interest rate {_pct(last_loan_rate)}." if had_loan else "Last month you did not borrow."
    lines.append(
        f"'About you -- **wealth level: {WEALTH_PLAIN.get(wealth, 'average')}**, **personality: {RISK_PLAIN.get(risk, 'balanced')}**, "
        f"**overall ability: {_beta_plain(beta)} tier**, **{_queue_plain(beta)}**. "
        f"{loan_history} "
        f"Your **monthly salary is {_money(last_wage)}**, and you can **borrow up to {_money(loan_cap)}** this time. "
        f"You currently have **about {_money(available)} available to spend**.'"
    )
    lines.append("")

    hike_sentence = ""
    if tick0 in HIKE_TICKS:
        new_dep, _new_loan = HIKE_TICKS[tick0]
        hike_sentence = f"**The central bank just raised interest rates**, borrowing will cost more going forward. "
    lines.append(
        f"'The situation outside -- **{CN_ECONOMIC_BACKGROUND.get(tick0, 'The economy is stable.')}** "
        f"{hike_sentence}"
        f"Last month the average borrowing rate was {_pct(market_loan_rate)}.'"
    )
    lines.append("")

    lines.append(
        "'Rules you need to know: borrowed money **can only be spent, not saved or invested elsewhere**. "
        "Also once you borrow, most of your money must be spent, **and the rest goes to stocks -- losses are possible**. Think carefully about whether to borrow.'"
    )
    lines.append("")

    lines.append("'Now I need you to do two things: (1) Do you think interest rates will go up or down? (2) Will you borrow or not?'")

    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Loan decision NPC briefing generator (standalone module)")
    parser.add_argument(
        "--player", type=str, default=DEFAULT_PLAYER_PATH,
        help=f"Player JSON path (default {DEFAULT_PLAYER_PATH})",
    )
    parser.add_argument(
        "--env", type=str, default=DEFAULT_ENV_PATH,
        help=f"information_environment.json path (default {DEFAULT_ENV_PATH})",
    )
    args = parser.parse_args()
    print(build_loan_briefing(args.player, args.env))

if __name__ == "__main__":
    main()
