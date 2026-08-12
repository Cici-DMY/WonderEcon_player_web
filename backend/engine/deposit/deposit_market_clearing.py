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
BANK_RISK_LABEL = {"conservative": "conservative", "aggressive": "aggressive"}

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

def _attr_deposit(desired, offered, la):
    if offered <= 0 or desired <= 0:
        return -100.0
    return math.log(offered / desired) - (la - 1) * max(0.0, math.log(desired / offered))

def _probs(attractions, beta):
    if not attractions:
        return []
    scaled = [beta * a for a in attractions]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    tot = sum(exps)
    return [1.0 / len(attractions)] * len(attractions) if tot == 0 else [e / tot for e in exps]

def run_player_deposit_market(
    player_path: str = DEFAULT_PLAYER_PATH,
    results_dir: str = DEFAULT_RESULTS_DIR,
    seed: int | None = None,
) -> dict[str, Any]:
    player = _load_json(player_path)
    t0 = player.get("selected_tick", 1) - 1
    attrs = player.setdefault("attributes", {})

    bk = _load_json(os.path.join(results_dir, "banks.json"))["agents"]
    banks = []
    for bid_str in sorted(bk, key=int):
        te = _tick_end(bk[bid_str], t0)
        banks.append({"bank_id": int(bid_str), "offered_rate": te.get("desired_deposit_rate"),
                      "risk_preference": te.get("risk_preference")})

    amount = max(0.0, attrs.get("current_remaining_assets", 0.0) or 0.0)
    desired = attrs.get("desired_deposit_rate") or 0.02
    beta = attrs.get("beta") or 1.0
    la = attrs.get("loss_aversion") or 1.4

    if amount <= 0 or not banks:
        attrs["last_deposit_amount"] = 0.0
        chosen = banks[0] if banks else {"bank_id": 0, "offered_rate": 0.0225, "risk_preference": None}
        attrs["last_deposit_rate"] = chosen["offered_rate"]
        attrs["last_deposit_bank_id"] = chosen["bank_id"]
        narrative = "[Deposit Market - Results]\n\n(You have almost no remaining funds - there is no money to deposit this month.)"
        player["deposit_market_result"] = {"amount": 0.0, "bank_id": chosen["bank_id"],
                                           "rate": chosen["offered_rate"]}
        with open(player_path, "w", encoding="utf-8") as f:
            json.dump(player, f, ensure_ascii=False, indent=2)
        return {"narrative": narrative, "result": player["deposit_market_result"]}

    rng = random.Random(seed) if seed is not None else random.Random()
    attractions = [_attr_deposit(desired, b["offered_rate"] if b["offered_rate"] else 0.001, la) for b in banks]
    probs = _probs(attractions, beta)
    chosen = banks[rng.choices(range(len(banks)), weights=probs, k=1)[0]]

    attrs["last_deposit_amount"] = round(amount, 2)
    attrs["last_deposit_rate"] = chosen["offered_rate"]
    attrs["last_deposit_bank_id"] = chosen["bank_id"]

    label = BANK_RISK_LABEL.get(chosen["risk_preference"], "")
    bank_name = f"Bank #{chosen['bank_id']} ({label})" if label else f"Bank #{chosen['bank_id']}"
    L = ["[Deposit Market - Results]", "",
         "(The teller has processed your deposit)",
         f"You deposited all your remaining {amount:,.0f} yuan into {bank_name}. ",
         f"Deposit rate: {chosen['offered_rate']*100:.2f}% (executed at bank quoted rate). All decisions for this month are now complete!"]
    player["deposit_market_result"] = {"amount": round(amount, 2), "bank_id": chosen["bank_id"],
                                       "rate": chosen["offered_rate"]}
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return {"narrative": "\n".join(L), "result": player["deposit_market_result"]}

def main():
    ap = argparse.ArgumentParser(description="Player deposit market matching (write back to player.json)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--results", default=DEFAULT_RESULTS_DIR)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    print(run_player_deposit_market(a.player, a.results, a.seed)["narrative"])

if __name__ == "__main__":
    main()
