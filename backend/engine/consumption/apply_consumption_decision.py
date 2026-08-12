from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_CONSUMPTION = "consumption"
PRICE_FLOOR = 1.0

NEC_PRICE_BANDS = {1: (0.97, 1.01), 2: (1.01, 1.04), 3: (1.04, 1.08), 4: (1.08, 1.12), 5: (1.12, 1.16)}
LUX_PRICE_BANDS = {1: (0.86, 0.92), 2: (0.92, 0.97), 3: (0.97, 1.02), 4: (1.02, 1.07), 5: (1.07, 1.12)}

NECESSITY_SHARE_RANGE_BY_WEALTH = {
    5: (0.45, 0.80),
    4: (0.60, 0.92),
    3: (0.78, 1.00),
    2: (0.85, 1.00),
    1: (0.90, 1.00),
}
CONSUMPTION_RATIO_BOUNDS = {
    True:  {5: (0.06, 0.12), 4: (0.20, 0.28), 3: (0.37, 0.50), 2: (0.50, 0.62), 1: (0.60, 0.80)},
    False: {5: (0.04, 0.10), 4: (0.16, 0.24), 3: (0.28, 0.36), 2: (0.36, 0.48), 1: (0.50, 0.62)},
}

def _load_json(p):
    if isinstance(p, dict):
        return p
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _env_snapshot(env, selected_tick):
    data = _load_json(env)
    if "ticks" not in data:
        return data
    t0 = selected_tick - 1
    snap = next((r["tick_start"] for r in data.get("ticks", []) if r.get("tick") == t0), None)
    if snap is None:
        raise KeyError(f"Environment data has no record for tick={t0}")
    return snap

def _rng(seed):
    return random.Random(seed) if seed is not None else random

def _mult_price(level, ref, rng, bands):
    lo, hi = bands[level]
    return max(PRICE_FLOOR, round(rng.uniform(lo * ref, hi * ref), 2))

def _tile(level, lo, hi, rng, ndigits=3):
    w = (hi - lo) / 5.0
    a = lo + (level - 1) * w
    b = lo + level * w
    return round(rng.uniform(a, b), ndigits)

def apply_consumption_decision(
    nec_price_level: int, lux_price_level: int,
    consume_ratio_level: int, necessity_share_level: int,
    player_path: str = DEFAULT_PLAYER_PATH, env_path: str = DEFAULT_ENV_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    for lv in (nec_price_level, lux_price_level, consume_ratio_level, necessity_share_level):
        if lv not in (1, 2, 3, 4, 5):
            raise ValueError(f"Level must be 1~5, got {lv}")
    if not os.path.isfile(player_path):
        raise FileNotFoundError(f"Player JSON not found: {player_path}")
    player = _load_json(player_path)
    if TASK_CONSUMPTION not in player.get("available_tasks", []):
        raise ValueError("This player has no consumption decision task.")

    attrs = player.setdefault("attributes", {})
    snap = _env_snapshot(env_path, player.get("selected_tick", 1))
    rng = _rng(seed)

    r_nec = snap.get("last_avg_taxed_goods_price_necessity") or 12.65
    r_lux = snap.get("last_avg_taxed_goods_price_luxury") or 126.5
    dp_nec = _mult_price(nec_price_level, r_nec, rng, NEC_PRICE_BANDS)
    dp_lux = _mult_price(lux_price_level, r_lux, rng, LUX_PRICE_BANDS)
    attrs["desired_goods_price_necessity"] = dp_nec
    attrs["desired_goods_price_luxury"] = dp_lux

    loan_ok = bool(attrs.get("current_loan_success"))
    if loan_ok:
        lo, hi = 0.80, 1.00
    else:
        is_labor = bool(attrs.get("is_labor_force"))
        lo, hi = CONSUMPTION_RATIO_BOUNDS[is_labor][attrs.get("wealth_level", 3)]
    cons_ratio = _tile(consume_ratio_level, lo, hi, rng)
    avail = attrs.get("total_available_funds", 0.0) or 0.0
    budget = avail * cons_ratio + (attrs.get("last_loan_amount", 0.0) or 0.0 if loan_ok else 0.0)

    nec_lo, nec_hi = NECESSITY_SHARE_RANGE_BY_WEALTH.get(attrs.get("wealth_level", 3), (0.78, 1.00))
    nec_share = _tile(necessity_share_level, nec_lo, nec_hi, rng)
    attrs["current_desired_consumption_amount_necessity"] = round(budget * nec_share, 2)
    attrs["current_desired_consumption_amount_luxury"] = round(budget * (1 - nec_share), 2)

    player["consumption_decision"] = {
        "nec_price_level": nec_price_level, "lux_price_level": lux_price_level,
        "consume_ratio_level": consume_ratio_level, "necessity_share_level": necessity_share_level,
        "desired_goods_price_necessity": dp_nec, "desired_goods_price_luxury": dp_lux,
        "consumption_ratio": cons_ratio, "necessity_share": nec_share,
        "total_budget": round(budget, 2),
    }
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return player

def main():
    ap = argparse.ArgumentParser(description="Consumption (four questions) -> write back to player.json")
    ap.add_argument("--nec-price", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--lux-price", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--ratio", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--nec-share", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    p = apply_consumption_decision(a.nec_price, a.lux_price, a.ratio, a.nec_share, a.player, a.env, a.seed)
    d = p["consumption_decision"]
    print(f"Necessity desired price {d['desired_goods_price_necessity']} | Luxury desired price {d['desired_goods_price_luxury']}"
          f" | Consumption ratio {d['consumption_ratio']*100:.1f}% | Necessity share {d['necessity_share']*100:.1f}%"
          f" | Total budget {d['total_budget']:,.0f} yuan (written back)")

if __name__ == "__main__":
    main()
