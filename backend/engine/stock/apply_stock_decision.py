from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

TASK_STOCK = "stock"
PRICE_FLOOR = 1.0

PRICE_BANDS = {1: (0.80, 0.89), 2: (0.89, 0.95), 3: (0.95, 1.01), 4: (1.01, 1.07), 5: (1.07, 1.15)}
STOCK_RATIO_RANGE = (0.0, 0.50)
NEC_SHARE_RANGE = (0.10, 0.90)

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

def _mult_price(level, ref, rng):
    lo, hi = PRICE_BANDS[level]
    return max(PRICE_FLOOR, round(rng.uniform(lo * ref, hi * ref), 2))

def _tile(level, lo, hi, rng, nd=4):
    w = (hi - lo) / 5.0
    return round(rng.uniform(lo + (level - 1) * w, lo + level * w), nd)

def _set_split_trade(attrs, kind, desired_invest, last_price):
    shares = attrs.get(f"shares_held_{kind}", 0) or 0
    attrs[f"current_desired_stock_investment_{kind}"] = round(desired_invest, 2)
    attrs[f"current_desired_stock_trade_amount_{kind}"] = round(desired_invest - shares * last_price, 2)
    target = int(desired_invest // last_price) if last_price > 0 else shares
    attrs[f"current_desired_stock_trade_qty_{kind}"] = int(target - shares)

def apply_stock_decision(
    nec_price_level: int, lux_price_level: int, nec_share_level: int,
    stock_ratio_level: int | None = None,
    player_path: str = DEFAULT_PLAYER_PATH, env_path: str = DEFAULT_ENV_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    for lv in (nec_price_level, lux_price_level, nec_share_level):
        if lv not in (1, 2, 3, 4, 5):
            raise ValueError(f"Level must be 1~5, got {lv}")
    if not os.path.isfile(player_path):
        raise FileNotFoundError(f"Player JSON not found: {player_path}")
    player = _load_json(player_path)
    if TASK_STOCK not in player.get("available_tasks", []):
        raise ValueError("This player has no stock decision task.")

    attrs = player.setdefault("attributes", {})
    snap = _env_snapshot(env_path, player.get("selected_tick", 1))
    rng = _rng(seed)

    r_nec = snap.get("last_stock_price_necessity") or 10.0
    r_lux = snap.get("last_stock_price_luxury") or 100.0
    attrs["desired_stock_price_necessity"] = _mult_price(nec_price_level, r_nec, rng)
    attrs["desired_stock_price_luxury"] = _mult_price(lux_price_level, r_lux, rng)

    remaining = attrs.get("current_remaining_assets", 0.0) or 0.0
    loan_ok = bool(attrs.get("current_loan_success"))
    if loan_ok:
        stock_ratio = 1.0
        total_invest = remaining
    else:
        if stock_ratio_level is None:
            stock_ratio_level = 3
        if stock_ratio_level not in (1, 2, 3, 4, 5):
            raise ValueError(f"stock_ratio_level must be 1~5, got {stock_ratio_level}")
        stock_ratio = _tile(stock_ratio_level, *STOCK_RATIO_RANGE, rng)
        total_invest = remaining * stock_ratio

    nec_share = _tile(nec_share_level, *NEC_SHARE_RANGE, rng)
    attrs["last_necessity_stock_ratio"] = nec_share

    _set_split_trade(attrs, "necessity", total_invest * nec_share, r_nec)
    _set_split_trade(attrs, "luxury", total_invest * (1 - nec_share), r_lux)

    player["stock_decision"] = {
        "nec_price_level": nec_price_level, "lux_price_level": lux_price_level,
        "nec_share_level": nec_share_level, "stock_ratio_level": (None if loan_ok else stock_ratio_level),
        "loan_forced_full_invest": loan_ok,
        "desired_stock_price_necessity": attrs["desired_stock_price_necessity"],
        "desired_stock_price_luxury": attrs["desired_stock_price_luxury"],
        "stock_ratio": round(stock_ratio, 4), "necessity_stock_ratio": nec_share,
        "total_invest": round(total_invest, 2),
    }
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return player

def main():
    ap = argparse.ArgumentParser(description="Stock decision -> write back to player.json")
    ap.add_argument("--nec-price", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--lux-price", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--nec-share", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--ratio", type=int, default=None, choices=[1, 2, 3, 4, 5],
                    help="Stock investment ratio level (ignored when loan approved, optional)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    p = apply_stock_decision(a.nec_price, a.lux_price, a.nec_share, a.ratio, a.player, a.env, a.seed)
    d = p["stock_decision"]
    forced = " (loan approved, forced 100%)" if d["loan_forced_full_invest"] else ""
    print(f"Necessity stock bid {d['desired_stock_price_necessity']} | Luxury stock bid {d['desired_stock_price_luxury']}"
          f" | Investment ratio {d['stock_ratio']*100:.1f}%{forced} | Necessity stock share {d['necessity_stock_ratio']*100:.1f}%"
          f" | Total investment {d['total_invest']:,.0f} yuan (written back)")

if __name__ == "__main__":
    main()
