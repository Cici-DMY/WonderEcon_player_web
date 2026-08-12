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

def _load_json(p):
    if not os.path.isfile(p):
        raise FileNotFoundError(f"JSON file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _tick_rec(records, t0):
    for rec in records:
        if rec.get("tick") == t0:
            return rec
    raise KeyError(f"This agent has no record for tick={t0}")

def _was_seeker(records, t0) -> bool:
    rec = _tick_rec(records, t0)
    for ev in rec.get("events", []):
        if "Labor market" in ev.get("reason", ""):
            f = ev.get("fields", {}).get("is_employed")
            if f is not None:
                return f.get("before") is False

    return not bool(rec["tick_end"].get("is_employed"))

def _attr_high(desired_wage, firm_wage, loss_aversion):
    if firm_wage <= 0 or desired_wage <= 0:
        return -100.0
    return math.log(firm_wage / desired_wage) - (loss_aversion - 1) * max(0.0, math.log(desired_wage / firm_wage))

def _probs(attractions, beta):
    if not attractions:
        return []
    scaled = [beta * a for a in attractions]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    tot = sum(exps)
    return [1.0 / len(attractions)] * len(attractions) if tot == 0 else [e / tot for e in exps]

def _weighted_order(probs, rng):
    idx = list(range(len(probs)))
    rem = list(probs)
    order = []
    for _ in range(len(idx)):
        tot = sum(rem)
        if tot <= 0:
            order.extend([i for i in idx if i not in order])
            break
        norm = [p / tot for p in rem]
        c = rng.choices(range(len(idx)), weights=norm, k=1)[0]
        order.append(idx[c])
        idx.pop(c)
        rem.pop(c)
    return order

def _run_labor_matching(job_seekers, hiring_firms, rng):
    if not job_seekers or not hiring_firms:
        return {s["agent_id"]: None for s in job_seekers}
    results = {s["agent_id"]: None for s in job_seekers}
    firm_remaining = {f["firm_id"]: f["slots"] for f in hiring_firms}
    seeker_map = {s["agent_id"]: s for s in job_seekers}

    prefs = {}
    for s in job_seekers:
        attrs = [_attr_high(s["desired_wage"], f["desired_wage"], s["loss_aversion"]) for f in hiring_firms]
        order = _weighted_order(_probs(attrs, s["beta"]), rng)
        prefs[s["agent_id"]] = [hiring_firms[i]["firm_id"] for i in order]

    unmatched = list(prefs.keys())
    for rnd in range(min(10, len(hiring_firms))):
        if not unmatched:
            break
        applications, still = {}, []
        for sid in unmatched:
            pl = prefs[sid]
            if rnd < len(pl) and firm_remaining.get(pl[rnd], 0) > 0:
                applications.setdefault(pl[rnd], []).append(sid)
            else:
                still.append(sid)
        for fid, applicants in applications.items():
            applicants.sort(key=lambda sid: -seeker_map[sid]["beta"])
            slots = firm_remaining[fid]
            hired, rejected = applicants[:slots], applicants[slots:]
            for sid in hired:
                results[sid] = fid
                firm_remaining[fid] -= 1
            still.extend(rejected)
        unmatched = still
    return results

def run_player_labor_market(
    player_path: str = DEFAULT_PLAYER_PATH,
    results_dir: str = DEFAULT_RESULTS_DIR,
    seed: int | None = None,
) -> dict[str, Any]:
    player = _load_json(player_path)
    matched_id = player["matched_agent_id"]
    t0 = player.get("selected_tick", 1) - 1
    attrs = player.setdefault("attributes", {})
    emp_dec = player.get("employment_decision", {})

    hh = _load_json(os.path.join(results_dir, "households.json"))["agents"]
    fm = _load_json(os.path.join(results_dir, "firms.json"))["agents"]

    quit_eff = bool(emp_dec.get("quit_effective"))
    matched_was_seeker = _was_seeker(hh[str(matched_id)], t0)
    currently_unemployed = not bool(attrs.get("is_employed"))
    player_is_seeker = quit_eff or matched_was_seeker or currently_unemployed
    involuntary = player_is_seeker and not quit_eff

    seekers = []
    for aid_str in sorted(hh, key=int):
        aid = int(aid_str)
        if aid == matched_id:
            continue
        te = _tick_rec(hh[aid_str], t0)["tick_end"]
        if not te.get("is_labor_force"):
            continue
        if _was_seeker(hh[aid_str], t0):
            seekers.append({
                "agent_id": aid, "desired_wage": te.get("desired_wage") or 1000.0,
                "beta": te.get("beta"), "loss_aversion": te.get("loss_aversion"),
            })
    if player_is_seeker:
        seekers.append({
            "agent_id": matched_id, "desired_wage": attrs.get("desired_wage") or 1000.0,
            "beta": attrs.get("beta"), "loss_aversion": attrs.get("loss_aversion"),
        })

    firm_wage = {}
    hiring = []
    for fid_str in sorted(fm, key=int):
        te = _tick_rec(fm[fid_str], t0)["tick_end"]
        firm_wage[int(fid_str)] = te.get("desired_wage")
        need = te.get("current_hiring_need") or 0
        if need > 0:
            hiring.append({"firm_id": int(fid_str), "desired_wage": te.get("desired_wage"),
                           "slots": need, "beta": te.get("beta")})

    rng = random.Random(seed) if seed is not None else random.Random()
    results = _run_labor_matching(seekers, hiring, rng) if player_is_seeker else {}

    hired_fid = results.get(matched_id) if player_is_seeker else None
    old_wage = attrs.get("last_wage", 0.0) or 0.0

    if not player_is_seeker:
        outcome = "kept_job"

        emp_id = attrs.get("employer_id")
        if emp_id is not None and firm_wage.get(emp_id):
            attrs["last_wage"] = firm_wage[emp_id]
    elif hired_fid is not None:
        outcome = "hired"
        attrs["is_employed"] = True
        attrs["employer_id"] = hired_fid
        attrs["last_wage"] = firm_wage.get(hired_fid) or attrs.get("last_wage", 0.0)
    else:
        outcome = "unemployed"
        attrs["is_employed"] = False
        attrs["employer_id"] = None
        attrs["last_wage"] = 0.0

    n_seekers = len(seekers)
    n_hired = sum(1 for v in results.values() if v is not None)
    new_wage = attrs.get("last_wage", 0.0) or 0.0
    narrative = _narrative(outcome, involuntary, attrs.get("employer_id"), old_wage, new_wage, n_seekers, n_hired)

    player["labor_market_result"] = {
        "outcome": outcome, "involuntary": involuntary, "employer_id": attrs.get("employer_id"),
        "last_wage": new_wage, "n_seekers": n_seekers, "n_hired": n_hired,
    }
    with open(player_path, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return {"narrative": narrative, "outcome": outcome, "result": player["labor_market_result"]}

def _narrative(outcome, involuntary, fid, old_wage, new_wage, n_seekers, n_hired):
    L = ["[Labor Market - Matching Results]", ""]
    if outcome == "kept_job":
        L.append("(You chose not to resign and stayed at your current position.)")
        L.append("")
        L.append("  - Employment status: employed (chose to stay)")
        L.append(f"  - Current employer: Company #{fid}")
        L.append(f"  - Current salary: {new_wage:,.0f} yuan")
        return "\n".join(L)

    L.append(f"(This month {n_seekers} people were job hunting in the market, {n_hired} successfully got hired.)")
    if involuntary:
        L.append("(You did not resign voluntarily, but are currently unemployed/laid off and entered the labor market to find work again.)")
    L.append("")
    if outcome == "hired":
        cmp_txt = ""
        if old_wage > 0:
            cmp_txt = f" (previous salary {old_wage:,.0f} yuan, " + (
                "new job pays more)" if new_wage > old_wage else "new job pays less)" if new_wage < old_wage else "same level)")
        L.append(f"  - Employment status: employed (newly hired from market){cmp_txt}")
        L.append(f"  - Current employer: Company #{fid}")
        L.append(f"  - Current salary: {new_wage:,.0f} yuan")
    else:
        L.append("  - Employment status: unemployed (no job match this month)")
        L.append("  - Current employer: none")
        L.append("  - Current salary: 0 yuan")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(description="Player labor market matching (write back to player.json)")
    ap.add_argument("--player", default=DEFAULT_PLAYER_PATH)
    ap.add_argument("--results", default=DEFAULT_RESULTS_DIR)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    print(run_player_labor_market(a.player, a.results, a.seed)["narrative"])

if __name__ == "__main__":
    main()
