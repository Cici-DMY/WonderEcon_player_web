from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_CONSUMPTION = "consumption"

CONSUMPTION_RATIO_BOUNDS = {
    True:  {5: (0.06, 0.12), 4: (0.20, 0.28), 3: (0.37, 0.50), 2: (0.50, 0.62), 1: (0.60, 0.80)},
    False: {5: (0.04, 0.10), 4: (0.16, 0.24), 3: (0.28, 0.36), 2: (0.36, 0.48), 1: (0.50, 0.62)},
}
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

def build_consumption_briefing(player: str | dict, env: str | dict) -> str:
    pdata = _load_json(player)
    attrs = pdata.get("attributes", {})
    selected_tick = pdata.get("selected_tick", 1)
    if TASK_CONSUMPTION not in pdata.get("available_tasks", []):
        return "(Your character does not have a consumption decision task.)"

    snap = _get_env_snapshot(env, selected_tick)
    wealth = attrs.get("wealth_level", 3)
    risk = attrs.get("risk_preference", "balanced")
    beta = attrs.get("beta")
    is_labor = bool(attrs.get("is_labor_force"))
    loan_ok = bool(attrs.get("current_loan_success"))
    avail = attrs.get("total_available_funds", 0.0) or 0.0
    loan_amt = attrs.get("last_loan_amount", 0.0) or 0.0
    nec_q = attrs.get("last_consumption_qty_necessity", 0)
    lux_q = attrs.get("last_consumption_qty_luxury", 0)
    nec_p = attrs.get("last_consumption_avg_price_necessity")
    lux_p = attrs.get("last_consumption_avg_price_luxury")
    last_ratio = attrs.get("last_consumption_ratio", 0.0) or 0.0
    last_nec_share = attrs.get("last_necessity_consumption_ratio", 0.0) or 0.0

    mkt_nec = snap.get("last_avg_taxed_goods_price_necessity")
    mkt_lux = snap.get("last_avg_taxed_goods_price_luxury")
    avg_nec_q = snap.get("last_avg_household_consumption_qty_necessity")
    avg_lux_q = snap.get("last_avg_household_consumption_qty_luxury")
    tick0 = snap.get("current_tick", selected_tick - 1)

    if loan_ok:
        lo, hi = 0.80, 1.00
    else:
        lo, hi = CONSUMPTION_RATIO_BOUNDS[is_labor][wealth]

    L = []
    L.append("[Supermarket - Shopping Entrance]")
    L.append("")
    L.append("(The shopping assistant pushes a cart over to greet you)")
    L.append("")
    L.append("'Hey there! What are you planning to buy this month?'")
    L.append("")

    nec_warn = " (You didn't buy any daily necessities last month, remember to stock up this time)" if (nec_q or 0) == 0 else ""
    L.append(
        f"'Let me look at your profile -- **wealth: {WEALTH_PLAIN.get(wealth, 'average')}**, **personality: {RISK_PLAIN.get(risk, 'balanced')}**, **shopping ability: {_beta_plain(beta)}** "
        f"(stronger ability means you get priority at the same price). "
        f"Last month you bought {nec_q} daily necessities and {lux_q} luxury items, mostly spending on necessities.{nec_warn}'"
    )
    L.append("")

    L.append(
        f"'You currently have **about {_money(avail)} to spend**. "
    )
    if loan_ok:
        L.append(f"This month your loan was approved ({_money(loan_amt)}), already added to your budget. ")
    L.append(
        f"Last month **daily necessities averaged {_price(mkt_nec)} per item, luxury goods averaged {_price(mkt_lux)} per item**, "
        f"people generally bought {avg_nec_q if avg_nec_q is None else round(avg_nec_q,1)} necessities and "
        f"{avg_lux_q if avg_lux_q is None else round(avg_lux_q,1)} luxury items. "
        f"**{CN_ECONOMIC_BACKGROUND.get(tick0, '')}**'"
    )
    L.append("")

    L.append(
        "'You need to make four decisions: (1) What is the max price you are willing to pay per necessity item? (2) Per luxury item? "
        "(3) What percentage of your available money to spend? (4) Do you want to buy more necessities or more luxury items? "
        "The higher your bid, the easier it is to buy, but money runs out faster!'"
    )
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Supermarket NPC briefing (consumption decision)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    a = ap.parse_args()
    print(build_consumption_briefing(a.player, a.env))

if __name__ == "__main__":
    main()
