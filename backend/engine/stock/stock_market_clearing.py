from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_RESULTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "results"))
DEFAULT_ENV_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "results", "information_environment.json"))

def _load_json(p):
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _tick_end(records, t0):
    for rec in records:
        if rec.get("tick") == t0:
            return rec["tick_end"]
    raise KeyError(f"This agent has no record for tick={t0}")

def _env_snapshot(env_path, selected_tick):
    data = _load_json(env_path)
    t0 = selected_tick - 1
    snap = next((r["tick_start"] for r in data.get("ticks", []) if r.get("tick") == t0), None)
    if snap is None:
        raise KeyError(f"Environment data has no record for tick={t0}")
    return snap

def _run_auction(participants, last_price):
    if not participants:
        return last_price, {}
    buyers = [p for p in participants if p["desired_qty"] > 0]
    sellers = [p for p in participants if p["desired_qty"] < 0]
    if not buyers or not sellers:
        return last_price, {p["agent_id"]: 0 for p in participants}
    buyers.sort(key=lambda x: (-x["desired_price"], -x["beta"]))
    sellers.sort(key=lambda x: (x["desired_price"], -x["beta"]))
    all_prices = sorted(set(p["desired_price"] for p in participants))
    best_price, best_vol = last_price, 0
    for price in all_prices:
        buy_vol = sum(abs(p["desired_amount"]) // price for p in buyers if p["desired_price"] >= price and price > 0)
        sell_vol = sum(min(abs(p["desired_qty"]), p["shares_held"]) for p in sellers if p["desired_price"] <= price)
        vol = min(buy_vol, sell_vol)
        if vol > best_vol:
            best_vol, best_price = vol, price
    if best_vol == 0:
        return last_price, {p["agent_id"]: 0 for p in participants}
    results = {p["agent_id"]: 0 for p in participants}
    rem_buy = rem_sell = best_vol
    for b in [p for p in buyers if p["desired_price"] >= best_price]:
        if rem_buy <= 0:
            break
        actual = min(int(abs(b["desired_amount"]) // best_price), rem_buy)
        results[b["agent_id"]] = actual
        rem_buy -= actual
    for s in [p for p in sellers if p["desired_price"] <= best_price]:
        if rem_sell <= 0:
            break
        actual = min(min(abs(s["desired_qty"]), s["shares_held"]), rem_sell)
        results[s["agent_id"]] = -actual
        rem_sell -= actual
    return best_price, results

def _listed_target(sector):
    return "luxury" if sector == "necessity" else "necessity"

def _build_participants(hh, fm, matched_id, pattrs, kind, t0):
    parts = []
    for aid_str in sorted(hh, key=int):
        aid = int(aid_str)
        snap = pattrs if aid == matched_id else _tick_end(hh[aid_str], t0)
        qty = snap.get(f"current_desired_stock_trade_qty_{kind}")
        if qty:
            parts.append({
                "agent_id": aid, "desired_price": snap.get(f"desired_stock_price_{kind}") or 1.0,
                "desired_qty": qty, "desired_amount": snap.get(f"current_desired_stock_trade_amount_{kind}") or 0.0,
                "shares_held": snap.get(f"shares_held_{kind}") or 0, "beta": snap.get("beta"),
            })
    for fid_str in sorted(fm, key=int):
        te = _tick_end(fm[fid_str], t0)
        if te.get("is_listed"):
            if _listed_target(te.get("sector")) != kind:
                continue
            qty = te.get("current_desired_stock_trade_qty")
            if qty:
                parts.append({
                    "agent_id": 1000 + int(fid_str), "desired_price": te.get("desired_stock_price") or 1.0,
                    "desired_qty": qty, "desired_amount": te.get("current_desired_stock_trade_amount") or 0.0,
                    "shares_held": te.get("shares_held") or 0, "beta": te.get("beta"),
                })
        else:
            qty = te.get(f"current_desired_stock_trade_qty_{kind}")
            if qty:
                parts.append({
                    "agent_id": 1000 + int(fid_str), "desired_price": te.get(f"desired_stock_price_{kind}") or 1.0,
                    "desired_qty": qty, "desired_amount": te.get(f"current_desired_stock_trade_amount_{kind}") or 0.0,
                    "shares_held": te.get(f"shares_held_{kind}") or 0, "beta": te.get("beta"),
                })
    return parts

def run_player_stock_market(
    player_path: str = DEFAULT_PLAYER_PATH,
    results_dir: str = DEFAULT_RESULTS_DIR,
    env_path: str = DEFAULT_ENV_PATH,
    seed: int | None = None,
) -> dict[str, Any]:
    player = _load_json(player_path)
    matched_id = player["matched_agent_id"]
    selected_tick = player.get("selected_tick", 1)
    t0 = selected_tick - 1
    attrs = player.setdefault("attributes", {})

    hh = _load_json(os.path.join(results_dir, "households.json"))["agents"]
    fm = _load_json(os.path.join(results_dir, "firms.json"))["agents"]
    snap = _env_snapshot(env_path, selected_tick)

    remaining = attrs.get("current_remaining_assets", 0.0) or 0.0
    outcomes = {}
    new_shares = {}
    for kind in ("necessity", "luxury"):
        old_price = snap.get(f"current_stock_price_{kind}") or (10.0 if kind == "necessity" else 100.0)
        parts = _build_participants(hh, fm, matched_id, attrs, kind, t0)
        price, trades = _run_auction(parts, old_price)
        old_sh = attrs.get(f"shares_held_{kind}", 0) or 0
        traded = trades.get(matched_id, 0)
        ns = max(0, old_sh + traded)
        new_shares[kind] = ns
        remaining += old_sh * (price - old_price)
        outcomes[kind] = {"clearing_price": price, "traded_qty": traded, "old_shares": old_sh, "new_shares": ns}

    np_, lp_ = outcomes["necessity"]["clearing_price"], outcomes["luxury"]["clearing_price"]
    nec_val = new_shares["necessity"] * np_
    lux_val = new_shares["luxury"] * lp_
    total = nec_val + lux_val
    attrs["shares_held_necessity"] = new_shares["necessity"]
    attrs["shares_held_luxury"] = new_shares["luxury"]
    attrs["last_stock_investment"] = round(total, 2)
    attrs["last_necessity_stock_ratio"] = round(nec_val / total, 4) if total > 0 else 0.5
    attrs["last_stock_investment_ratio"] = round(total / remaining, 4) if remaining > 0 else 0.0
    remaining = max(0.0, remaining - total)
    attrs["current_remaining_assets"] = round(remaining, 2)

    narrative = _narrative(outcomes, total, remaining)
    player["stock_market_result"] = {
        "necessity": outcomes["necessity"], "luxury": outcomes["luxury"],
        "stock_value_after": round(total, 2), "remaining_assets": round(remaining, 2),
    }
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return {"narrative": narrative, "result": player["stock_market_result"]}

def _leg(name, o):
    q = o["traded_qty"]
    if q > 0:
        return f"{name}: bought {q} shares at {o['clearing_price']:,.2f} yuan, now holding {o['new_shares']} shares."
    if q < 0:
        return f"{name}: sold {-q} shares at {o['clearing_price']:,.2f} yuan, now holding {o['new_shares']} shares."
    return f"{name}: no transaction this time (holdings unchanged at {o['new_shares']} shares), clearing price {o['clearing_price']:,.2f} yuan."

def _narrative(outcomes, total, remaining):
    L = ["[Stock Market - Call Auction Results]", ""]
    L.append("(The broker prints the transaction receipt)")
    L.append(_leg("Necessity stock", outcomes["necessity"]))
    L.append(_leg("Luxury stock", outcomes["luxury"]))
    L.append(f"Your total stock holdings are now worth approximately {total:,.0f} yuan.")
    if remaining > 0:
        L.append(f"You still have about {remaining:,.0f} yuan in cash remaining, which you can deposit in the bank in the next step.")
    else:
        L.append("Most of your funds have been invested in stocks, very little cash remains.")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Player stock market matching (write back to player.json)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--results", default=DEFAULT_RESULTS_DIR)
    ap.add_argument("--env", default=DEFAULT_ENV_PATH)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    print(run_player_stock_market(a.player, a.results, a.env, a.seed)["narrative"])

if __name__ == "__main__":
    main()
