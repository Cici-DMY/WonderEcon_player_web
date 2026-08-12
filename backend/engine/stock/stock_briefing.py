from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_STOCK = "stock"
WEALTH_PLAIN = {5: "very wealthy", 4: "fairly comfortable", 3: "average",
                2: "somewhat tight", 1: "very poor"}
RISK_PLAIN = {"conservative": "conservative and cautious", "steady": "steady and practical", "balanced": "balanced",
              "growth": "growth-oriented", "aggressive": "bold and aggressive"}
CN_ECONOMIC_BACKGROUND = {
    0: "The economy is slightly overheated, real estate is booming.", 1: "The economy is running at a high level, prices are starting to rise.",
    2: "Demand is still high, but momentum is slowing.", 3: "Prices are rising faster and faster.", 4: "Inflationary pressure is increasing.",
    5: "The economy is fully overheated, prices are very high.", 6: "Prices are surging more fiercely, inflation is worsening.",
    7: "The economy is showing stagflation signs - things are expensive and people can barely afford to buy.", 8: "High prices persist.",
    9: "The economy is cooling down, but prices remain high.", 10: "Stagflation worsens, demand shrinks significantly.",
    11: "Prices are peaking, but the real economy is weakening.", 12: "Demand is contracting across the board.",
}

def _money(x):
    return "—" if x is None else f"{x:,.0f} yuan"

def _price(x):
    return "—" if x is None else f"{x:,.2f} yuan"

def _pct(x):
    return "—" if x is None else f"{x*100:.2f}%"

def _beta_plain(b):
    if b is None:
        return "unknown"
    return "very strong" if b >= 1.6 else "fairly strong" if b >= 1.3 else "moderate" if b >= 0.8 else "somewhat weak" if b >= 0.4 else "fairly weak"

def _load_json(p):
    if isinstance(p, dict):
        return p
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_env_snapshot(env, selected_tick):
    data = _load_json(env)
    if "ticks" not in data:
        return data
    t0 = selected_tick - 1
    for rec in data.get("ticks", []):
        if rec.get("tick") == t0:
            return rec["tick_start"]
    raise KeyError(f"Environment data has no record for tick={t0}")

def build_stock_briefing(player: str | dict, env: str | dict) -> str:
    pdata = _load_json(player)
    attrs = pdata.get("attributes", {})
    selected_tick = pdata.get("selected_tick", 1)
    if TASK_STOCK not in pdata.get("available_tasks", []):
        return "(Your character does not have a stock decision task.)"

    snap = _get_env_snapshot(env, selected_tick)
    wealth = attrs.get("wealth_level", 3)
    risk = attrs.get("risk_preference", "balanced")
    beta = attrs.get("beta")
    loan_ok = bool(attrs.get("current_loan_success"))
    remaining = attrs.get("current_remaining_assets", 0.0) or 0.0
    sh_nec = attrs.get("shares_held_necessity", 0)
    sh_lux = attrs.get("shares_held_luxury", 0)
    last_ratio = attrs.get("last_stock_investment_ratio", 0.0) or 0.0
    last_nec_share = attrs.get("last_necessity_stock_ratio", 0.0) or 0.0

    p_nec = snap.get("last_stock_price_necessity")
    p_lux = snap.get("last_stock_price_luxury")
    pr_nec = snap.get("last_listed_firm_profit_rate_necessity")
    rk_nec = snap.get("last_listed_firm_profit_rank_necessity")
    pr_lux = snap.get("last_listed_firm_profit_rate_luxury")
    rk_lux = snap.get("last_listed_firm_profit_rank_luxury")
    tick0 = snap.get("current_tick", selected_tick - 1)

    L = []
    L.append("[Stock Exchange]")
    L.append("")
    L.append("(The broker pulls up your account)")
    L.append("")
    L.append("Let me see how to invest today.")
    L.append("")

    L.append(
        f"Your situation: **wealth: {WEALTH_PLAIN.get(wealth, 'average')}**, **personality: {RISK_PLAIN.get(risk, 'balanced')}**, "
        f"**ability: {_beta_plain(beta)} tier** (at the same bid price, those with stronger ability get matched first). "
        f"You currently **hold {sh_nec} shares of the necessity goods company and "
        f"{sh_lux} shares of the luxury goods company**. "
        f"Last time you invested {last_ratio*100:.0f}% of your spare cash in stocks, "
        f"{'mostly' if last_nec_share > 0.55 else 'about half' if last_nec_share > 0.45 else 'a small portion'} in the necessity goods company. "
        f"This time your **available spare cash is about {_money(remaining)}**."
    )
    if loan_ok:
        L.append("Note! You borrowed money this month, so by the rules **all spare cash must be invested in stocks** - no need to choose a ratio.")
    L.append("")

    def _rank_eval(rk):
        if rk is None:
            return "hard to say"
        if rk <= 4:
            return "good"
        if rk <= 8:
            return "decent"
        return "mediocre"

    rk_nec_str = f"ranked {rk_nec} out of 12" if rk_nec else "ranking unknown"
    rk_lux_str = f"ranked {rk_lux}" if rk_lux else "ranking unknown"
    L.append(
        f"Market info: last round necessity company stock price **{_price(p_nec)}**, luxury company **{_price(p_lux)}**. "
        f"**Necessity company profitability: {_rank_eval(rk_nec)}, {rk_nec_str}; luxury company: {rk_lux_str}, {_rank_eval(rk_lux)}**. "
        f"**{CN_ECONOMIC_BACKGROUND.get(tick0, '')}**"
    )
    L.append("")

    if loan_ok:
        L.append(
            "Three decisions: 1. What is the max price you would pay for necessity company stock? 2. What about luxury company? "
            "3. How to split between the two? Reminder: **the stock market has friction - you may not be able to buy everything**."
        )
    else:
        L.append(
            "Four decisions: 1. What is the max price you would pay for necessity company stock? 2. What about luxury company? "
            "3. What proportion of spare cash to invest? 4. How to split between the two? Reminder: **the stock market has friction - you may not be able to buy everything**."
        )
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Stock Exchange NPC briefing (stock decision)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    a = ap.parse_args()
    print(build_stock_briefing(a.player, a.env))

if __name__ == "__main__":
    main()
