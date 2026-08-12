from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_EMPLOYMENT = "employment"

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

def _beta_plain(beta):
    if beta is None:
        return "unknown"
    return "very strong" if beta >= 1.6 else "fairly strong" if beta >= 1.3 else "moderate" if beta >= 0.8 else "somewhat weak" if beta >= 0.4 else "fairly weak"

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

def build_employment_briefing(player: str | dict, env: str | dict) -> str:
    pdata = _load_json(player)
    attrs = pdata.get("attributes", {})
    selected_tick = pdata.get("selected_tick", 1)
    if TASK_EMPLOYMENT not in pdata.get("available_tasks", []):
        return "(Your character does not have an employment decision task. You can skip the job market.)"

    snap = _get_env_snapshot(env, selected_tick)
    wealth = attrs.get("wealth_level", 3)
    risk = attrs.get("risk_preference", "balanced")
    beta = attrs.get("beta")
    employed = bool(attrs.get("is_employed"))
    employer = attrs.get("employer_id")
    last_wage = attrs.get("last_wage", 0.0) or 0.0
    avg_wage = snap.get("last_avg_household_wage")
    tick0 = snap.get("current_tick", selected_tick - 1)

    L = []
    L.append("[Job Market]")
    L.append("")
    L.append("(The recruitment consultant flips through your resume)")
    L.append("")
    L.append("'Come, have a seat! Let me help you with the job situation.'")
    L.append("")

    if employed:
        L.append(
            f"'Your profile -- **wealth: {WEALTH_PLAIN.get(wealth, 'average')}**, **personality: {RISK_PLAIN.get(risk, 'balanced')}**, "
            f"**overall ability: {_beta_plain(beta)} tier** -- companies prioritize candidates with stronger ability. "
            f"You are currently **employed at Company #{employer}, monthly salary {_money(last_wage)}**. "
            f"The **average monthly salary out there is {_money(avg_wage)}**, "
            f"**{CN_ECONOMIC_BACKGROUND.get(tick0, '')}**'"
        )
        L.append("")
        L.append("'Two decisions: (1) What monthly salary do you want? (2) Do you want to resign and look for a new job?'")
        L.append("")
        L.append(
            "'About resigning -- **there is risk**: you might find something better, or worse, or even no one hires you this month. "
            "Also even if you don't resign, **you could still get laid off**. Think carefully before deciding.'"
        )
    else:
        L.append(
            f"'Your profile -- **wealth: {WEALTH_PLAIN.get(wealth, 'average')}**, **personality: {RISK_PLAIN.get(risk, 'balanced')}**, "
            f"**overall ability: {_beta_plain(beta)} tier** -- companies prioritize candidates with stronger ability. "
            f"You are **currently unemployed** and will enter the market directly. "
            f"The **average monthly salary out there is {_money(avg_wage)}**, "
            f"**{CN_ECONOMIC_BACKGROUND.get(tick0, '')}**'"
        )
        L.append("")
        L.append(
            "'You only need to make one decision: what monthly salary do you want? "
            "Reminder: job hunting has risks -- you might match with a high-paying or low-paying company, or temporarily not find anything.'"
        )
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Job market NPC briefing (employment decision)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    a = ap.parse_args()
    print(build_employment_briefing(a.player, a.env))

if __name__ == "__main__":
    main()
