from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_RESULTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "results"))

POLES = {
    "Time Preference": (("S", "Spending"), ("A", "Saving")),
    "Risk Attitude": (("R", "Aggressive"), ("P", "Conservative")),
    "Market Stance": (("C", "Contrarian"), ("T", "Trend-following")),
    "Consumption Taste": (("U", "Practical"), ("F", "Refined")),
}

POLE_DESC = {
    "S": "Money is for spending, live in the moment",
    "A": "Money is for saving, slow and steady",
    "R": "Dare to borrow, trade stocks, quit jobs — thrill of the gamble",
    "P": "Low debt, light positions, seek stability — safety first",
    "C": "Independent judgment, goes against the crowd, dares to act contrarian",
    "T": "Follow the crowd, go with the trend",
    "U": "Focus on function and value for money, practicality first",
    "F": "Buy the best, life should have quality",
}

def _load_json(p):
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _env_snapshot(env_path, selected_tick):
    data = _load_json(env_path)
    t0 = selected_tick - 1
    snap = next((r["tick_start"] for r in data.get("ticks", []) if r.get("tick") == t0), None)
    if snap is None:
        raise KeyError(f"Environment data has no record for tick={t0}")
    return snap

def _mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0.0

def _sign(x):
    return 1 if x > 1e-12 else (-1 if x < -1e-12 else 0)

def _vote(pv, gm, weight=1, higher_pole=1):
    if pv is None or gm is None:
        return 0
    if abs(pv - gm) < 1e-9:
        return 0
    return (weight if pv > gm else -weight) * higher_pole

def _tag(s, left, right):
    return left if s > 0 else (right if s < 0 else "neutral(0)")

def _safe_div(a, b):
    if b is None or b <= 0:
        return None
    if a is None:
        return None
    return a / b

_REASON_ENDOGENOUS = "Endogenous attributes computed (income tax, mortgage, available funds, wealth level)"
_REASON_GOODS = "Household goods phase: belief, desired price, consumption ratio/amount"
_REASON_LOAN = "Household loan phase: belief, desired rate, decision, amount"
_REASON_GOODS_MARKET = "Goods market: consumption qty, avg price, real consumption amount, remaining assets"
_REASON_STOCK = "Household stock phase: belief, desired price, investment amount, trade qty/direction"

def _event_field_after(record: dict, reason: str, field: str):
    for ev in record.get("events", []):
        if ev.get("reason") != reason:
            continue
        f = ev.get("fields", {}).get(field)
        if f is not None and "after" in f:
            return f["after"]
    return None

def _agent_desired_consumption_ratio(rec: dict) -> float | None:
    nec = _event_field_after(rec, _REASON_GOODS, "current_desired_consumption_amount_necessity") or 0.0
    lux = _event_field_after(rec, _REASON_GOODS, "current_desired_consumption_amount_luxury") or 0.0
    avail = _event_field_after(rec, _REASON_ENDOGENOUS, "total_available_funds")
    return _safe_div(nec + lux, avail)

def _agent_desired_necessity_share(rec: dict) -> float | None:
    nec = _event_field_after(rec, _REASON_GOODS, "current_desired_consumption_amount_necessity") or 0.0
    lux = _event_field_after(rec, _REASON_GOODS, "current_desired_consumption_amount_luxury") or 0.0
    total = nec + lux
    if total <= 0:
        return None
    return nec / total

def _agent_desired_stock_ratio(rec: dict) -> float | None:
    nec = _event_field_after(rec, _REASON_STOCK, "current_desired_stock_investment_necessity") or 0.0
    lux = _event_field_after(rec, _REASON_STOCK, "current_desired_stock_investment_luxury") or 0.0
    remaining = _event_field_after(rec, _REASON_GOODS_MARKET, "current_remaining_assets")
    return _safe_div(nec + lux, remaining)

def _agent_desired_necessity_stock_ratio(rec: dict) -> float | None:
    nec = _event_field_after(rec, _REASON_STOCK, "current_desired_stock_investment_necessity") or 0.0
    lux = _event_field_after(rec, _REASON_STOCK, "current_desired_stock_investment_luxury") or 0.0
    total = nec + lux
    if total <= 0:
        return None
    return nec / total

def _agent_desired_loan_ratio(rec: dict) -> float:
    decide = _event_field_after(rec, _REASON_LOAN, "current_decide_loan")
    if not decide:
        return 0.0
    amount = _event_field_after(rec, _REASON_LOAN, "current_loan_amount") or 0.0
    wage = rec.get("tick_start", {}).get("last_wage") or 0.0
    if wage <= 0:
        return 0.0
    return amount / wage

def _agent_quit(record: dict) -> bool:
    for ev in record.get("events", []):
        if "wage phase" in ev.get("reason", "").lower():
            f = ev.get("fields", {}).get("is_employed")
            if f is not None:
                return f.get("before") is True and f.get("after") is False
    return False

def judge_player_epti(player_path: str = DEFAULT_PLAYER_PATH,
                      results_dir: str = DEFAULT_RESULTS_DIR) -> dict[str, Any]:
    player = _load_json(player_path)
    pa = player.get("attributes", {})
    selected_tick = player.get("selected_tick", 1)
    t0 = selected_tick - 1
    is_labor = bool(player.get("is_labor_force", pa.get("is_labor_force")))
    wealth = player.get("wealth_level", pa.get("wealth_level"))

    hh = _load_json(os.path.join(results_dir, "households.json"))["agents"]
    env = _env_snapshot(os.path.join(results_dir, "information_environment.json"), selected_tick)

    group = []
    for aid, recs in hh.items():
        rec = next((r for r in recs if r.get("tick") == t0), None)
        if not rec:
            continue
        ts = rec.get("tick_start", {})
        if bool(ts.get("is_labor_force")) == is_labor and ts.get("wealth_level") == wealth:
            group.append(rec)

    ref = {
        "goods_nec": env.get("last_avg_taxed_goods_price_necessity"),
        "goods_lux": env.get("last_avg_taxed_goods_price_luxury"),
        "stock_nec": env.get("last_stock_price_necessity"),
        "stock_lux": env.get("last_stock_price_luxury"),
    }

    loan_group = is_labor and wealth is not None and wealth <= 2

    dims = {}
    dims["Time Preference"] = _dim_time(player, group)
    dims["Risk Attitude"] = _dim_risk(player, pa, group, loan_group, is_labor)
    dims["Market Stance"] = _dim_market(pa, group, ref)
    dims["Consumption Taste"] = _dim_taste(player, group)

    code = "".join(_letter(name, d["score"]) for name, d in dims.items())
    return {
        "code": code,
        "code_dashed": "-".join(_letter(name, d["score"]) for name, d in dims.items()),
        "dims": dims,
        "group_size": len(group),
        "group_key": {"is_labor_force": is_labor, "wealth_level": wealth},
    }

def _letter(dim_name, score):
    (lf, _), (rf, _) = POLES[dim_name]
    return lf if score >= 0 else rf

def _name(dim_name, score):
    (lf, ln), (rf, rn) = POLES[dim_name]
    return (lf, ln) if score >= 0 else (rf, rn)

def _dim_time(player, group):
    crit = []
    score = 0

    cd = player.get("consumption_decision", {})
    pv = cd.get("consumption_ratio")
    gm = _mean([r for r in (_agent_desired_consumption_ratio(g) for g in group) if r is not None])
    s = _vote(pv, gm, weight=2, higher_pole=1)
    score += s
    if pv is not None:
        crit.append(f"Desired consumption ratio {pv*100:.1f}% vs group mean {gm*100:.1f}% (weight 2) -> {_tag(s, 'S', 'A')}")

    letter = _letter("Time Preference", score)
    return {"score": score, "criteria": crit, "pole": _name("Time Preference", score), "desc": POLE_DESC[letter]}

def _dim_risk(player, pa, group, loan_group, is_labor):
    crit = []
    score = 0

    if loan_group:
        pld = player.get("loan_decision", {})
        plam = player.get("loan_amount_decision", {})
        pv = plam.get("loan_ratio", 0.0) if pld.get("decide_loan") else 0.0
        gm = _mean([_agent_desired_loan_ratio(g) for g in group])
        s = _vote(pv, gm, weight=1, higher_pole=1)
        score += s
        crit.append(f"Desired loan ratio {pv*100:.1f}% vs group mean {gm*100:.1f}% -> {_tag(s, 'R', 'P')}")

    sd = player.get("stock_decision", {})
    pv = sd.get("stock_ratio")
    gm = _mean([r for r in (_agent_desired_stock_ratio(g) for g in group) if r is not None])
    s = _vote(pv, gm, weight=2, higher_pole=1)
    score += s
    if pv is not None:
        crit.append(f"Desired stock investment ratio {pv*100:.1f}% vs group mean {gm*100:.1f}% (weight 2) -> {_tag(s, 'R', 'P')}")

    pv = sd.get("necessity_stock_ratio")
    gm = _mean([r for r in (_agent_desired_necessity_stock_ratio(g) for g in group) if r is not None])
    if pv is not None:
        s = _vote(pv, gm, weight=1, higher_pole=-1)
        score += s
        crit.append(f"Desired necessity stock ratio {pv*100:.1f}% vs group mean {gm*100:.1f}% (low=luxury-biased=aggressive) -> {_tag(s, 'R', 'P')}")

    if is_labor:
        ed = player.get("employment_decision", {})
        if ed.get("quit_applicable", True):
            pv_q = 1.0 if ed.get("quit_effective") else 0.0
            gm_q = _mean([1.0 if _agent_quit(g) else 0.0 for g in group])
            s = _vote(pv_q, gm_q, weight=1, higher_pole=1)
            score += s
            crit.append(f"Voluntary quit {'yes' if pv_q>0 else 'no'} vs group quit rate {gm_q*100:.1f}% -> {_tag(s, 'R', 'P')}")

    letter = _letter("Risk Attitude", score)
    return {"score": score, "criteria": crit, "pole": _name("Risk Attitude", score), "desc": POLE_DESC[letter]}

def _dim_market(pa, group, ref):
    crit = []
    score = 0
    checks = [
        ("Necessity goods desired price", "desired_goods_price_necessity", ref["goods_nec"], 1),
        ("Luxury goods desired price", "desired_goods_price_luxury", ref["goods_lux"], 1),
        ("Necessity stock desired price", "desired_stock_price_necessity", ref["stock_nec"], 1),
        ("Luxury stock desired price", "desired_stock_price_luxury", ref["stock_lux"], 2),
    ]
    for label, field, r, w in checks:
        if r is None or not r:
            continue
        pdir = _sign((pa.get(field) or r) - r)
        majority = _sign(sum(_sign((g.get("tick_end", {}).get(field) or r) - r) for g in group))
        if majority == 0:
            continue
        s = w if pdir != majority else -w
        score += s
        d = {1: "above initial", -1: "below initial", 0: "=neutral"}
        wtag = " (weight 2)" if w == 2 else ""
        crit.append(f"{label}{wtag} {d[pdir]} vs majority {d[majority]} -> {'C(Contrarian)' if s>0 else 'T(Trend-following)'}")
    letter = _letter("Market Stance", score)
    return {"score": score, "criteria": crit, "pole": _name("Market Stance", score), "desc": POLE_DESC[letter]}

def _dim_taste(player, group):
    crit = []

    cd = player.get("consumption_decision", {})
    nec_share = cd.get("necessity_share")
    pv = (1.0 - nec_share) if isinstance(nec_share, (int, float)) else None

    gm = _mean([
        (1.0 - r) for r in (
            _agent_desired_necessity_share(g) for g in group
        ) if r is not None
    ])

    score = 0
    if pv is not None:
        score = _vote(pv, gm, weight=1, higher_pole=-1)
        crit.append(f"Desired luxury consumption ratio {pv*100:.1f}% vs group mean {gm*100:.1f}% -> {'U(Practical)' if score>0 else 'F(Refined)'}")
    letter = _letter("Consumption Taste", score)
    return {"score": score, "criteria": crit, "pole": _name("Consumption Taste", score), "desc": POLE_DESC[letter]}

def main():
    ap = argparse.ArgumentParser(description="Determine player EPTI type")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--results", default=DEFAULT_RESULTS_DIR)
    a = ap.parse_args()
    r = judge_player_epti(a.player, a.results)
    print("=" * 56)
    print(f"  Player EPTI type: {r['code']}  ({r['code_dashed']})")
    print("=" * 56)
    gk = r["group_key"]
    print(f"  Reference group: {'labor force' if gk['is_labor_force'] else 'non-labor force'} / wealth level {gk['wealth_level']}"
          f" ({r['group_size']} agents)")
    for name, d in r["dims"].items():
        (lf, ln) = d["pole"]
        print("-" * 56)
        print(f"  {name}: {lf} ({ln})   [dimension score {d['score']:+d}]")
        print(f"     -> {POLE_DESC[lf]}")
        for c in d["criteria"]:
            print(f"     - {c}")

if __name__ == "__main__":
    main()
