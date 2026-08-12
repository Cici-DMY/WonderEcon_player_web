from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_DEPOSIT = "deposit"
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

def build_deposit_briefing(player: str | dict, env: str | dict) -> str:
    pdata = _load_json(player)
    attrs = pdata.get("attributes", {})
    selected_tick = pdata.get("selected_tick", 1)
    if TASK_DEPOSIT not in pdata.get("available_tasks", []):
        return "(Your character does not have a deposit decision task.)"

    snap = _get_env_snapshot(env, selected_tick)
    wealth = attrs.get("wealth_level", 3)
    risk = attrs.get("risk_preference", "balanced")
    beta = attrs.get("beta")
    last_dep_rate = attrs.get("last_deposit_rate")
    remaining = attrs.get("current_remaining_assets", 0.0) or 0.0
    mkt_dep = snap.get("last_avg_bank_deposit_rate")
    tick0 = snap.get("current_tick", selected_tick - 1)

    L = []
    L.append("[Commercial Bank - Deposit Window]")
    L.append("")
    L.append("(The teller waves you over with a smile)")
    L.append("")
    L.append("'Last stop! Just deposit your remaining money and you're done.'")
    L.append("")
    L.append(
        f"'Your profile -- **wealth: {WEALTH_PLAIN.get(wealth, 'average')}**, **personality: {RISK_PLAIN.get(risk, 'balanced')}**. "
        f"**Last time your deposit rate was {_pct(last_dep_rate)}**. "
        f"You currently have **{_money(remaining)} remaining**, which will **all be deposited into the bank** -- no need to worry about how much to deposit. "
        f"Last time the average rate was {_pct(mkt_dep)}, **{CN_ECONOMIC_BACKGROUND.get(tick0, '')}**'"
    )
    L.append("")
    L.append("'You only need to make one decision: what deposit rate do you hope to get? Don't worry, **deposits always succeed, there is no quota limit**.'")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Commercial bank NPC briefing (deposit decision)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    a = ap.parse_args()
    print(build_deposit_briefing(a.player, a.env))

if __name__ == "__main__":
    main()
