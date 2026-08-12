from __future__ import annotations

import argparse
import json
import os
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_RESULTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "results"))

NEC_FIRST, NEC_FLOOR, NEC_DECAY = 1.0, 0.5, 0.99
LUX_FIRST, LUX_FLOOR, LUX_DECAY = 10.0, 2.0, 0.88

def _load_json(p):
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

_REASON_ENDOGENOUS = "Endogenous attributes computed (income tax, mortgage, available funds, wealth level)"

def _get_endogenous_current_total_assets(agent_records: list, tick_0based: int) -> float:
    for rec in agent_records:
        if rec.get("tick") == tick_0based:
            for ev in rec.get("events", []):
                if ev.get("reason") == _REASON_ENDOGENOUS:
                    fields = ev.get("fields", {})
                    cta = fields.get("current_total_assets", {})
                    if "after" in cta:
                        return cta["after"]
            break
    return 0.0

def _compute_end_total_assets(state: dict, p_nec: float, p_lux: float,
                              income_tax_rate: float) -> float:
    is_employed = bool(state.get("is_employed", False))
    last_wage = state.get("last_wage", 0) or 0
    wage_after_tax = last_wage * (1 - income_tax_rate) if is_employed else 0.0

    last_deposit = state.get("last_deposit_amount", 0) or 0
    last_deposit_rate = state.get("last_deposit_rate", 0) or 0
    deposit_with_interest = last_deposit * (1 + last_deposit_rate / 12) if last_deposit > 0 else 0.0

    last_loan = state.get("last_loan_amount", 0) or 0
    last_loan_rate = state.get("last_loan_rate", 0) or 0
    loan_with_interest = last_loan * (1 + last_loan_rate / 12) if last_loan > 0 else 0.0

    mortgage_payment = state.get("current_mortgage_payment", 0) or 0
    current_subsidy = state.get("current_subsidy", 0) or 0
    last_rnd_bonus = state.get("last_rnd_bonus", 0) or 0

    total_available_funds = (
        wage_after_tax
        + last_rnd_bonus
        + deposit_with_interest
        - loan_with_interest
        - mortgage_payment
        + current_subsidy
    )
    if total_available_funds < current_subsidy:
        total_available_funds = current_subsidy

    stock_val = (
        (state.get("shares_held_necessity", 0) or 0) * (p_nec or 0)
        + (state.get("shares_held_luxury", 0) or 0) * (p_lux or 0)
    )
    return total_available_funds + stock_val

def _asset_change_pct(init_assets: float, end_assets: float) -> float | None:
    if not init_assets or init_assets <= 0:
        return None
    return (end_assets - init_assets) / init_assets * 100.0

def _geo_sum(n: int, first: float, floor: float, decay: float) -> float:
    n = int(n)
    if n <= 0:
        return 0.0
    bonus = (first - floor) * (1 - decay ** n) / (1 - decay)
    return n * floor + bonus

def happiness(nec_qty: int, lux_qty: int) -> float:
    return (_geo_sum(nec_qty, NEC_FIRST, NEC_FLOOR, NEC_DECAY)
            + _geo_sum(lux_qty, LUX_FIRST, LUX_FLOOR, LUX_DECAY))

def compare_performance(player_path: str = DEFAULT_PLAYER_PATH,
                        results_dir: str = DEFAULT_RESULTS_DIR) -> dict[str, Any]:
    player = _load_json(player_path)
    pa = player.get("attributes", {})
    matched_id = str(player["matched_agent_id"])
    t0 = player.get("selected_tick", 1) - 1
    is_labor = bool(player.get("is_labor_force", pa.get("is_labor_force")))
    wealth = player.get("wealth_level", pa.get("wealth_level"))

    hh = _load_json(os.path.join(results_dir, "households.json"))["agents"]
    envrecs = {r["tick"]: r for r in _load_json(os.path.join(results_dir, "information_environment.json"))["ticks"]}
    env_te = envrecs[t0]["tick_end"]
    p_nec = env_te.get("last_stock_price_necessity")
    p_lux = env_te.get("last_stock_price_luxury")
    income_tax_rate = env_te.get("personal_income_tax_rate", 0) or 0

    def agent_te(aid):
        return next((r["tick_end"] for r in hh[aid] if r.get("tick") == t0), None)

    init_matched = _get_endogenous_current_total_assets(hh[matched_id], t0)
    m_te = agent_te(matched_id)

    player_metrics = {
        "asset_change_pct": _asset_change_pct(init_matched, _compute_end_total_assets(pa, p_nec, p_lux, income_tax_rate)),
        "happiness": happiness(pa.get("last_consumption_qty_necessity", 0), pa.get("last_consumption_qty_luxury", 0)),
    }

    matched_metrics = {
        "asset_change_pct": _asset_change_pct(init_matched, _compute_end_total_assets(m_te, p_nec, p_lux, income_tax_rate)),
        "happiness": happiness(m_te.get("last_consumption_qty_necessity", 0), m_te.get("last_consumption_qty_luxury", 0)),
    }

    changes, haps = [], []
    group_size = 0
    for aid in hh:
        te = agent_te(aid)
        if not te or bool(te.get("is_labor_force")) != is_labor or te.get("wealth_level") != wealth:
            continue
        group_size += 1
        init_a = _get_endogenous_current_total_assets(hh[aid], t0)
        end_a = _compute_end_total_assets(te, p_nec, p_lux, income_tax_rate)
        ch = _asset_change_pct(init_a, end_a)
        if ch is not None:
            changes.append(ch)
        haps.append(happiness(te.get("last_consumption_qty_necessity", 0), te.get("last_consumption_qty_luxury", 0)))
    group_metrics = {
        "asset_change_pct": (sum(changes) / len(changes)) if changes else None,
        "happiness": (sum(haps) / len(haps)) if haps else 0.0,
    }

    return {
        "selected_tick": t0 + 1,
        "group_key": {"is_labor_force": is_labor, "wealth_level": wealth},
        "group_size": group_size,
        "player": player_metrics,
        "matched_agent": matched_metrics,
        "group_mean": group_metrics,
    }

def _fmt_pct(x):
    return "—" if x is None else (f"+{x:.2f}%" if x >= 0 else f"{x:.2f}%")

def main():
    ap = argparse.ArgumentParser(description="Performance comparison: asset change & current happiness")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--results", default=DEFAULT_RESULTS_DIR)
    a = ap.parse_args()
    r = compare_performance(a.player, a.results)
    gk = r["group_key"]
    print("=" * 56)
    print("  Performance Comparison")
    print("=" * 56)
    print(f"  tick {r['selected_tick']} · comparison group: "
          f"{'labor force' if gk['is_labor_force'] else 'non-labor force'} · wealth level {gk['wealth_level']}"
          f" ({r['group_size']} agents)")
    print("-" * 56)
    print("  Asset Change:")
    print(f"     You           : {_fmt_pct(r['player']['asset_change_pct'])}")
    print(f"     Original Agent: {_fmt_pct(r['matched_agent']['asset_change_pct'])}")
    print(f"     Group Mean    : {_fmt_pct(r['group_mean']['asset_change_pct'])}")
    print("-" * 56)
    print("  Current Happiness:")
    print(f"     You           : {r['player']['happiness']:.1f} pts")
    print(f"     Original Agent: {r['matched_agent']['happiness']:.1f} pts")
    print(f"     Group Mean    : {r['group_mean']['happiness']:.1f} pts")

if __name__ == "__main__":
    main()
