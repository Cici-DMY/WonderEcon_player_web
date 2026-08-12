from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))

TASK_LABELS = [
    ("loan", "Loan"),
    ("employment", "Employment"),
    ("consumption", "Consumption"),
    ("stock", "Stock"),
    ("deposit", "Deposit"),
]

def _load_json(p):
    if isinstance(p, dict):
        return p
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _money(x):
    return "—" if x is None else f"{x:,.0f} yuan"

def _pct(x):
    return "—" if x is None else f"{x*100:.2f}%"

def _recap_loan(player) -> str:
    res = player.get("loan_market_result")
    dec = player.get("loan_decision", {})
    if res is None and not dec:
        return "(not performed)"
    if not (res or {}).get("applied", dec.get("decide_loan")):
        return "Did not apply for loan"
    if res and res.get("success"):
        bank = res.get("bank_id")
        return f"Approved, {_money(res.get('amount'))} @ {_pct(res.get('rate'))}" + (f" (Bank #{bank})" if bank is not None else "")

    want = player.get("loan_amount_decision", {}).get("current_loan_amount")\
        or player.get("attributes", {}).get("current_loan_amount")
    return f"Applied for {_money(want)}, but not approved"

def _recap_employment(player) -> str:
    res = player.get("labor_market_result")
    if res is None:
        ed = player.get("employment_decision")
        return "(not performed)" if ed is None else "Desired wage set (not yet matched)"
    outcome = res.get("outcome")
    emp = res.get("employer_id")
    wage = res.get("last_wage")
    if outcome == "kept_job":
        return f"Kept job, salary {_money(wage)}" + (f" (Company #{emp})" if emp is not None else "")
    if outcome == "hired":
        tag = " (re-employed after layoff)" if res.get("involuntary") else ""
        return f"Newly hired, salary {_money(wage)}" + (f" (Company #{emp})" if emp is not None else "") + tag

    return "No job match, unemployed this month" + (" (involuntarily entered market)" if res.get("involuntary") else "")

def _recap_consumption(player) -> str:
    res = player.get("consumption_market_result")
    if res is None:
        return "(not performed)"
    nq = res.get("necessity_qty", 0) or 0
    lq = res.get("luxury_qty", 0) or 0
    return f"{nq + lq} items (necessities {nq} + luxury {lq}), total {_money(res.get('total_spent'))}"

def _stock_leg(name, leg) -> str:
    if not leg:
        return f"{name} —"
    q = leg.get("traded_qty", 0) or 0
    p = leg.get("clearing_price")
    pstr = f"{p:,.2f} yuan" if isinstance(p, (int, float)) else "—"
    if q > 0:
        return f"{name} bought {q} shares @ {pstr}"
    if q < 0:
        return f"{name} sold {-q} shares @ {pstr}"
    return f"{name} no transaction"

def _recap_stock(player) -> str:
    res = player.get("stock_market_result")
    if res is None:
        return "(not performed)"
    return _stock_leg("Necessity stock", res.get("necessity")) + "; " + _stock_leg("Luxury stock", res.get("luxury"))

def _recap_deposit(player) -> str:
    res = player.get("deposit_market_result")
    if res is None:
        return "(not performed)"
    amt = res.get("amount", 0) or 0
    if amt <= 0:
        return "No funds to deposit"
    bank = res.get("bank_id")
    return f"{_money(amt)} -> Bank #{bank} @ {_pct(res.get('rate'))}"

_RECAP_FUNCS = {
    "loan": _recap_loan,
    "employment": _recap_employment,
    "consumption": _recap_consumption,
    "stock": _recap_stock,
    "deposit": _recap_deposit,
}

def build_decision_review(player: str | dict) -> dict[str, Any]:
    p = _load_json(player)
    avail = p.get("available_tasks", [t for t, _ in TASK_LABELS])
    lines = []
    for task, label in TASK_LABELS:
        if task not in avail:
            continue
        lines.append((label, _RECAP_FUNCS[task](p)))
    text = "[Decision Review]\n" + "\n".join(f"  {label}: {recap}" for label, recap in lines)
    return {"lines": lines, "text": text}

def main():
    ap = argparse.ArgumentParser(description="Decision review (input player JSON)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    a = ap.parse_args()
    print(build_decision_review(a.player)["text"])

if __name__ == "__main__":
    main()
