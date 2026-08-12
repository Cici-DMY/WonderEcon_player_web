from __future__ import annotations

import argparse
import json
import math
import os
import random
from typing import Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PLAYER_PATH = os.path.normpath(
    os.path.join(_THIS_DIR, "..", "match_agent", "player.json")
)
DEFAULT_RESULTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "results"))

FIRM_ID_OFFSET = 1000
BANK_RISK_LABEL = {"conservative": "conservative", "aggressive": "aggressive"}

def _load_json(path: str) -> dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"JSON file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _tick_end(records: list[dict[str, Any]], tick_0based: int) -> dict[str, Any]:
    for rec in records:
        if rec.get("tick") == tick_0based:
            return rec["tick_end"]
    raise KeyError(f"This agent has no record for tick={tick_0based}")

def _compute_attraction(desired_rate: float, offered_rate: float, loss_aversion: float) -> float:
    if offered_rate <= 0 or desired_rate <= 0:
        return -100.0
    base = math.log(desired_rate / offered_rate)
    loss = (loss_aversion - 1) * max(0.0, math.log(offered_rate / desired_rate))
    return base - loss

def _compute_probabilities(attractions: list[float], beta: float) -> list[float]:
    if not attractions:
        return []
    scaled = [beta * a for a in attractions]
    max_s = max(scaled)
    exps = [math.exp(s - max_s) for s in scaled]
    total = sum(exps)
    if total == 0:
        return [1.0 / len(attractions)] * len(attractions)
    return [e / total for e in exps]

def _run_loan_matching(
    borrowers: list[dict[str, Any]],
    bank_offers: list[dict[str, Any]],
    rng: random.Random,
) -> dict[int, dict[str, Any] | None]:
    results: dict[int, dict[str, Any] | None] = {b["agent_id"]: None for b in borrowers}
    if not borrowers or not bank_offers:
        return results
    bank_remaining = {bk["bank_id"]: bk["available_pool"] for bk in bank_offers}
    for borrower in borrowers:
        attractions = [
            _compute_attraction(borrower["desired_rate"], bank["offered_rate"], borrower["loss_aversion"])
            for bank in bank_offers
        ]
        probs = _compute_probabilities(attractions, borrower["beta"])
        chosen_idx = rng.choices(range(len(bank_offers)), weights=probs, k=1)[0]
        chosen = bank_offers[chosen_idx]
        if bank_remaining[chosen["bank_id"]] >= borrower["amount"]:
            results[borrower["agent_id"]] = {
                "bank_id": chosen["bank_id"], "rate": chosen["offered_rate"],
                "amount": borrower["amount"], "success": True,
            }
            bank_remaining[chosen["bank_id"]] -= borrower["amount"]
        else:
            results[borrower["agent_id"]] = {
                "bank_id": chosen["bank_id"], "rate": chosen["offered_rate"],
                "amount": 0, "success": False,
            }
    return results

def _loan_inputs_from_snapshot(snap: dict[str, Any], agent_id: int) -> dict[str, Any] | None:
    if snap.get("current_decide_loan") and (snap.get("current_loan_amount") or 0) > 0:
        return {
            "agent_id": agent_id,
            "desired_rate": snap.get("desired_loan_rate") or 0.06,
            "amount": snap["current_loan_amount"],
            "beta": snap.get("beta"),
            "loss_aversion": snap.get("loss_aversion"),
        }
    return None

def _assemble(player: dict[str, Any], results_dir: str, tick_0based: int):
    matched_id = player["matched_agent_id"]
    pattrs = player.get("attributes", {})

    hh = _load_json(os.path.join(results_dir, "households.json"))["agents"]
    fm = _load_json(os.path.join(results_dir, "firms.json"))["agents"]
    bk = _load_json(os.path.join(results_dir, "banks.json"))["agents"]

    borrowers: list[dict[str, Any]] = []

    for aid_str in sorted(hh, key=int):
        aid = int(aid_str)
        snap = pattrs if aid == matched_id else _tick_end(hh[aid_str], tick_0based)
        item = _loan_inputs_from_snapshot(snap, aid)
        if item:
            borrowers.append(item)

    for fid_str in sorted(fm, key=int):
        snap = _tick_end(fm[fid_str], tick_0based)
        item = _loan_inputs_from_snapshot(snap, FIRM_ID_OFFSET + int(fid_str))
        if item:
            borrowers.append(item)

    bank_offers: list[dict[str, Any]] = []
    bank_info: dict[int, dict[str, Any]] = {}
    for bid_str in sorted(bk, key=int):
        snap = _tick_end(bk[bid_str], tick_0based)
        bid = int(bid_str)
        bank_offers.append({
            "bank_id": bid,
            "offered_rate": snap.get("desired_loan_rate"),
            "available_pool": snap.get("current_pool"),
        })
        bank_info[bid] = {"risk_preference": snap.get("risk_preference")}

    return borrowers, bank_offers, bank_info

def _bank_name(bank_id: int, bank_info: dict[int, dict[str, Any]]) -> str:
    risk = bank_info.get(bank_id, {}).get("risk_preference")
    label = BANK_RISK_LABEL.get(risk, "")
    return f"Bank #{bank_id} ({label})" if label else f"Bank #{bank_id}"

def _build_narrative(applied, res, amount_wanted, desired_rate, bank_info, n_apply, n_granted) -> str:
    lines: list[str] = ["[Loan Market - Matching Results]", ""]
    if not applied:
        lines.append("(You did not apply for a loan this month and left the bank directly.)")
        return "\n".join(lines)

    lines.append(f"(This month the market had {n_apply} loan applications in total, and {n_granted} were approved.)")
    lines.append("")
    if res and res.get("success"):
        lines.append("(The loan officer checked your documents and nodded)")
        lines.append("'Congratulations! Your loan has been approved --'")
        lines.append(f"'  - Lending bank: {_bank_name(res['bank_id'], bank_info)}'")
        lines.append(f"'  - Loan amount: {res['amount']:,.2f} yuan'")
        lines.append(f"'  - Actual rate: {res['rate']*100:.2f}% (executed at bank's offered rate)'")
        lines.append("'This money will be added to your consumption budget this month. Enjoy!'")
    else:
        tried = _bank_name(res["bank_id"], bank_info) if res else "bank"
        lines.append("(The loan officer checked the system and looked apologetic)")
        lines.append(
            f"'Sorry, your request to borrow {amount_wanted:,.2f} yuan could not be approved -- "
            f"the {tried} you selected has run out of lending quota this month and cannot fulfill your request.'"
        )
        lines.append("'You won't carry this loan this month. Let's try again next time.'")
    return "\n".join(lines)

def run_player_loan_market(
    player_path: str = DEFAULT_PLAYER_PATH,
    results_dir: str = DEFAULT_RESULTS_DIR,
    seed: int | None = None,
) -> dict[str, Any]:
    player = _load_json(player_path)
    matched_id = player["matched_agent_id"]
    tick_0based = player.get("selected_tick", 1) - 1
    pattrs = player.setdefault("attributes", {})

    borrowers, bank_offers, bank_info = _assemble(player, results_dir, tick_0based)

    rng = random.Random(seed) if seed is not None else random.Random()
    results = _run_loan_matching(borrowers, bank_offers, rng)

    n_apply = len(borrowers)
    n_granted = sum(1 for r in results.values() if r and r.get("success"))

    applied = any(b["agent_id"] == matched_id for b in borrowers)
    res = results.get(matched_id) if applied else None

    if res and res.get("success"):
        pattrs["last_has_loan"] = True
        pattrs["last_loan_amount"] = res["amount"]
        pattrs["last_loan_rate"] = res["rate"]
        pattrs["last_loan_bank_id"] = res["bank_id"]
        pattrs["current_loan_success"] = True
        pattrs["attempted_loan_bank_id"] = res["bank_id"]
    else:
        pattrs["last_has_loan"] = False
        pattrs["last_loan_amount"] = 0.0
        pattrs["last_loan_rate"] = None
        pattrs["last_loan_bank_id"] = None
        pattrs["current_loan_success"] = (False if applied else None)
        pattrs["attempted_loan_bank_id"] = res["bank_id"] if res else None

    amount_wanted = pattrs.get("current_loan_amount", 0.0) or 0.0
    desired_rate = pattrs.get("desired_loan_rate")
    narrative = _build_narrative(
        applied, res, amount_wanted, desired_rate, bank_info, n_apply, n_granted
    )

    player["loan_market_result"] = {
        "applied": applied,
        "success": bool(res and res.get("success")) if applied else None,
        "bank_id": res["bank_id"] if res else None,
        "rate": res["rate"] if res else None,
        "amount": res["amount"] if (res and res.get("success")) else 0.0,
        "n_applications": n_apply,
        "n_granted": n_granted,
    }

    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)

    return {
        "narrative": narrative,
        "applied": applied,
        "success": player["loan_market_result"]["success"],
        "result": res,
        "n_applications": n_apply,
        "n_granted": n_granted,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Player loan market matching (results written back to player.json)")
    parser.add_argument("--player", type=str, default=DEFAULT_PLAYER_PATH)
    parser.add_argument("--results", type=str, default=DEFAULT_RESULTS_DIR,
                        help="results directory (containing households/firms/banks.json)")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed (for reproducibility)")
    args = parser.parse_args()

    out = run_player_loan_market(args.player, args.results, seed=args.seed)
    print(out["narrative"])

if __name__ == "__main__":
    main()
