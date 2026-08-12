from __future__ import annotations

import argparse
import json
import math
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(os.path.join(_THIS_DIR, "..", "match_agent", "player.json"))
DEFAULT_RESULTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "results"))

GOODS_BRAND_ALPHA = 0.8
GOODS_BRAND_WEALTH_GAMMA = 0.5

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

def _attr_low(desired, posted, la):
    if posted <= 0 or desired <= 0:
        return -100.0
    return math.log(desired / posted) - (la - 1) * max(0.0, math.log(posted / desired))

def _probs(attractions, beta):
    if not attractions:
        return []
    scaled = [beta * a for a in attractions]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    tot = sum(exps)
    return [1.0 / len(attractions)] * len(attractions) if tot == 0 else [e / tot for e in exps]

def _weighted_order(probs, rng):
    idx, rem, order = list(range(len(probs))), list(probs), []
    for _ in range(len(idx)):
        tot = sum(rem)
        if tot <= 0:
            order.extend([i for i in idx if i not in order])
            break
        norm = [p / tot for p in rem]
        c = rng.choices(range(len(idx)), weights=norm, k=1)[0]
        order.append(idx[c]); idx.pop(c); rem.pop(c)
    return order

def _run_goods_matching(buyers, sellers, rng):
    hh_purchases = {b["agent_id"]: [] for b in buyers}
    firm_sales = {s["firm_id"]: 0 for s in sellers}
    if not buyers or not sellers:
        return hh_purchases, firm_sales
    firm_stock = {s["firm_id"]: s["available_qty"] for s in sellers}
    budget_rem = {b["agent_id"]: b["budget"] for b in buyers}
    seller_price = {s["firm_id"]: s["posted_price"] for s in sellers}
    buyer_map = {b["agent_id"]: b for b in buyers}

    prefs = {}
    for b in buyers:
        attrs = []
        for s in sellers:
            a = _attr_low(b["desired_price"], s["posted_price"], b["loss_aversion"])
            scale = s.get("scale_level", 3)
            wealth = b.get("wealth_level", 3)
            wf = max(0.0, 1.0 + GOODS_BRAND_WEALTH_GAMMA * (wealth - 3) / 2.0)
            a += GOODS_BRAND_ALPHA * (scale - 1) / 4.0 * wf
            attrs.append(a)
        order = _weighted_order(_probs(attrs, b["beta"]), rng)
        prefs[b["agent_id"]] = [sellers[i]["firm_id"] for i in order]

    active = list(prefs.keys())
    for rnd in range(min(10, len(sellers))):
        if not active:
            break
        nxt = []
        firm_applicants = {}
        for bid in active:
            pl = prefs[bid]
            if rnd < len(pl):
                fid = pl[rnd]
                if firm_stock.get(fid, 0) > 0:
                    firm_applicants.setdefault(fid, []).append(bid)
                else:
                    nxt.append(bid)
        for fid, applicants in firm_applicants.items():
            price = seller_price[fid]
            applicants.sort(key=lambda bid: -buyer_map[bid]["beta"])
            for bid in applicants:
                qty_can = int(budget_rem[bid] // price) if price > 0 else 0
                stock = firm_stock[fid]
                if qty_can <= 0:
                    continue
                if stock >= qty_can:
                    hh_purchases[bid].append((fid, price, qty_can))
                    firm_sales[fid] += qty_can
                    firm_stock[fid] -= qty_can
                    budget_rem[bid] -= qty_can * price
                elif stock > 0:
                    nxt.append(bid)
        active = nxt
    return hh_purchases, firm_sales

def _agg(purchases):
    if not purchases:
        return 0, 0.0, 0.0
    qty = sum(q for _, _, q in purchases)
    spent = sum(p * q for _, p, q in purchases)
    return qty, (spent / qty if qty > 0 else 0.0), spent

def _build_buyers(hh, matched_id, pattrs, sector, t0):
    buyers = []
    for aid_str in sorted(hh, key=int):
        aid = int(aid_str)
        snap = pattrs if aid == matched_id else _tick_end(hh[aid_str], t0)
        buyers.append({
            "agent_id": aid,
            "desired_price": snap.get(f"desired_goods_price_{sector}") or 1.0,
            "budget": snap.get(f"current_desired_consumption_amount_{sector}") or 0.0,
            "beta": snap.get("beta"), "loss_aversion": snap.get("loss_aversion"),
            "wealth_level": snap.get("wealth_level", 3),
        })
    return buyers

def _build_sellers(fm, sector, t0):
    sellers = []
    for fid_str in sorted(fm, key=int):
        te = _tick_end(fm[fid_str], t0)
        if te.get("sector") != sector:
            continue
        premarket_stock = int((te.get("inventory") or 0) + (te.get("last_sales_qty") or 0))
        if premarket_stock > 0:
            sellers.append({
                "firm_id": int(fid_str), "posted_price": te.get("current_posttax_price"),
                "available_qty": premarket_stock, "scale_level": te.get("scale_level", 3),
            })
    return sellers

def run_player_goods_market(
    player_path: str = DEFAULT_PLAYER_PATH,
    results_dir: str = DEFAULT_RESULTS_DIR,
    seed: int | None = None,
) -> dict[str, Any]:
    player = _load_json(player_path)
    matched_id = player["matched_agent_id"]
    t0 = player.get("selected_tick", 1) - 1
    attrs = player.setdefault("attributes", {})

    hh = _load_json(os.path.join(results_dir, "households.json"))["agents"]
    fm = _load_json(os.path.join(results_dir, "firms.json"))["agents"]

    rng = random.Random(seed) if seed is not None else random.Random()
    nec_purch, _ = _run_goods_matching(_build_buyers(hh, matched_id, attrs, "necessity", t0),
                                       _build_sellers(fm, "necessity", t0), rng)
    lux_purch, _ = _run_goods_matching(_build_buyers(hh, matched_id, attrs, "luxury", t0),
                                       _build_sellers(fm, "luxury", t0), rng)

    nec_qty, nec_avg, nec_spent = _agg(nec_purch.get(matched_id, []))
    lux_qty, lux_avg, lux_spent = _agg(lux_purch.get(matched_id, []))
    total_spent = nec_spent + lux_spent

    avail = attrs.get("total_available_funds", 0.0) or 0.0
    loan_ok = bool(attrs.get("current_loan_success"))
    loan_amt = attrs.get("last_loan_amount", 0.0) or 0.0
    cur_total = attrs.get("current_total_assets", 0.0) or 0.0

    attrs["last_consumption_qty_necessity"] = nec_qty
    attrs["last_consumption_qty_luxury"] = lux_qty
    attrs["last_consumption_avg_price_necessity"] = round(nec_avg, 2)
    attrs["last_consumption_avg_price_luxury"] = round(lux_avg, 2)
    attrs["current_real_consumption_amount_necessity"] = round(nec_spent, 2)
    attrs["current_real_consumption_amount_luxury"] = round(lux_spent, 2)
    attrs["last_necessity_consumption_ratio"] = round(nec_spent / total_spent, 4) if total_spent > 0 else 1.0
    if avail > 0:
        attrs["last_consumption_ratio"] = round(
            max(0.0, (total_spent - loan_amt) / avail) if loan_ok else total_spent / avail, 4)
    else:
        attrs["last_consumption_ratio"] = 0.0
    remaining = max(0.0, cur_total + (loan_amt if loan_ok else 0.0) - total_spent)
    attrs["current_remaining_assets"] = round(remaining, 2)

    narrative = _narrative(nec_qty, nec_avg, nec_spent, lux_qty, lux_avg, lux_spent, total_spent, remaining)
    player["consumption_market_result"] = {
        "necessity_qty": nec_qty, "necessity_spent": round(nec_spent, 2),
        "luxury_qty": lux_qty, "luxury_spent": round(lux_spent, 2),
        "total_spent": round(total_spent, 2), "remaining_assets": round(remaining, 2),
    }
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return {"narrative": narrative, "result": player["consumption_market_result"]}

def _narrative(nq, na, ns, lq, la, ls, total, remaining):
    L = ["[Goods Market - Shopping Results]", ""]
    L.append("(After checkout, the shopping assistant hands you the receipt)")
    L.append(f"'Necessities: bought {nq} items, average price {na:,.2f} yuan, spent {ns:,.0f} yuan.'")
    L.append(f"'Luxury goods: bought {lq} items, average price {la:,.2f} yuan, spent {ls:,.0f} yuan.'")
    L.append(f"'Total consumption this month: {total:,.0f} yuan.'")
    if nq == 0 and lq == 0:
        L.append("'You barely bought anything this month -- perhaps your bids were too low or inventory was sold out.'")
    L.append(f"'After shopping you have about {remaining:,.0f} yuan left, available for investment and deposits.'")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Player goods market matching (write back to player.json)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--results", default=DEFAULT_RESULTS_DIR)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    print(run_player_goods_market(a.player, a.results, a.seed)["narrative"])

if __name__ == "__main__":
    main()
