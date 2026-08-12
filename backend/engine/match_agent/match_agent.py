from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

RISK_ORDER: dict[str, int] = {
    "conservative": 1,
    "steady": 2,
    "balanced": 3,
    "growth": 4,
    "aggressive": 5,
}

TASK_LOAN = "loan"
TASK_EMPLOYMENT = "employment"
TASK_CONSUMPTION = "consumption"
TASK_STOCK = "stock"
TASK_DEPOSIT = "deposit"

TASK_ORDER: list[str] = [
    TASK_LOAN, TASK_EMPLOYMENT, TASK_CONSUMPTION, TASK_STOCK, TASK_DEPOSIT,
]

TASK_LABELS: dict[str, str] = {
    TASK_LOAN: "Loan Decision",
    TASK_EMPLOYMENT: "Employment Decision",
    TASK_CONSUMPTION: "Consumption Decision",
    TASK_STOCK: "Stock Decision",
    TASK_DEPOSIT: "Deposit Decision",
}
TASK_LOCATIONS: dict[str, str] = {
    TASK_LOAN: "Commercial Bank",
    TASK_EMPLOYMENT: "Job Market",
    TASK_CONSUMPTION: "Supermarket",
    TASK_STOCK: "Stock Exchange",
    TASK_DEPOSIT: "Commercial Bank",
}

def determine_available_tasks(
    is_labor_force: bool,
    wealth_level: int,
    is_employed: bool = True,
    government_extra_subsidy: bool = False,
) -> list[str]:
    tasks: list[str] = []
    if is_labor_force:
        loan_eligible = (
            wealth_level <= 2
            and is_employed
            and not government_extra_subsidy
        )
        if loan_eligible:
            tasks.append(TASK_LOAN)
        tasks.append(TASK_EMPLOYMENT)

    tasks.extend([TASK_CONSUMPTION, TASK_STOCK, TASK_DEPOSIT])
    return tasks

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESULTS_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "results"))
DEFAULT_HOUSEHOLDS_PATH = os.path.join(DEFAULT_RESULTS_DIR, "households.json")
DEFAULT_ENV_PATH = os.path.join(DEFAULT_RESULTS_DIR, "information_environment.json")
DEFAULT_PLAYER_DIR = _THIS_DIR
DEFAULT_PLAYER_FILENAME = "player.json"

NUM_TICKS = 13

@dataclass
class MatchResult:
    agent_id: int
    selected_tick: int
    is_labor_force: bool
    requested_wealth_level: int
    requested_risk: str
    matched_risk: str
    risk_distance: int
    exact_risk_match: bool
    candidate_count: int
    available_tasks: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        return d

def load_households(households_path: str) -> dict[str, Any]:
    if not os.path.isfile(households_path):
        raise FileNotFoundError(
            f"households.json not found: {households_path}\n"
            f"Please run the simulation first, or specify the correct path with --households."
        )
    with open(households_path, "r", encoding="utf-8") as f:
        return json.load(f)

def _tick_to_index(selected_tick: int) -> int:
    if not (1 <= selected_tick <= NUM_TICKS):
        raise ValueError(f"tick must be between 1..{NUM_TICKS}, got {selected_tick}")
    return selected_tick - 1

def get_tick_start_snapshot(
    agent_records: list[dict[str, Any]], tick_0based: int
) -> dict[str, Any]:
    for rec in agent_records:
        if rec.get("tick") == tick_0based:
            return rec["tick_start"]
    raise KeyError(f"This agent has no record for tick={tick_0based}")

def _get_tick_record(
    agent_records: list[dict[str, Any]], tick_0based: int
) -> dict[str, Any]:
    for rec in agent_records:
        if rec.get("tick") == tick_0based:
            return rec
    raise KeyError(f"This agent has no record for tick={tick_0based}")

_REASON_ENDOGENOUS = "Endogenous attributes computed (income tax, mortgage, available funds, wealth level)"

def _get_endogenous_updates(record: dict[str, Any]) -> dict[str, Any]:
    for ev in record.get("events", []):
        if ev.get("reason") == _REASON_ENDOGENOUS:
            return {k: v["after"] for k, v in ev.get("fields", {}).items() if "after" in v}
    return {}

def _build_snapshot_with_endogenous(record: dict[str, Any]) -> dict[str, Any]:
    snap = dict(record.get("tick_start", {}))
    snap.update(_get_endogenous_updates(record))
    return snap

def match_player_to_agent(
    households_path: str | dict[str, Any],
    selected_tick: int,
    is_labor_force: bool,
    wealth_level: int,
    risk_preference: str,
) -> MatchResult:

    if wealth_level not in (1, 2, 3, 4, 5):
        raise ValueError(f"wealth_level must be 1..5, got {wealth_level}")
    if risk_preference not in RISK_ORDER:
        raise ValueError(
            f"risk_preference must be one of {list(RISK_ORDER)}, got {risk_preference!r}"
        )
    tick_0based = _tick_to_index(selected_tick)

    data = (
        households_path
        if isinstance(households_path, dict)
        else load_households(households_path)
    )
    agents: dict[str, Any] = data["agents"]

    player_rank = RISK_ORDER[risk_preference]

    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for aid_str, records in agents.items():
        rec = _get_tick_record(records, tick_0based)
        endogenous = _get_endogenous_updates(rec)
        snap = rec.get("tick_start", {})
        actual_wealth = endogenous.get("wealth_level", snap.get("wealth_level"))
        if (
            bool(snap.get("is_labor_force")) == bool(is_labor_force)
            and actual_wealth == wealth_level
        ):
            candidates.append((int(aid_str), snap, rec))

    if not candidates:
        raise LookupError(
            f"tick {selected_tick}, identity={'labor force' if is_labor_force else 'non-labor force'}、"
            f"wealth_level={wealth_level}: no candidate agents found."
        )

    def sort_key(item: tuple[int, dict[str, Any], dict[str, Any]]) -> tuple[int, int]:
        aid, snap, rec = item
        agent_rank = RISK_ORDER.get(snap.get("risk_preference"), 0)
        return (abs(agent_rank - player_rank), aid)

    best_aid, best_snap, best_rec = min(candidates, key=sort_key)
    best_rank = RISK_ORDER.get(best_snap.get("risk_preference"), 0)
    distance = abs(best_rank - player_rank)

    final_attrs = _build_snapshot_with_endogenous(best_rec)

    return MatchResult(
        agent_id=best_aid,
        selected_tick=selected_tick,
        is_labor_force=bool(is_labor_force),
        requested_wealth_level=wealth_level,
        requested_risk=risk_preference,
        matched_risk=best_snap.get("risk_preference"),
        risk_distance=distance,
        exact_risk_match=(distance == 0),
        candidate_count=len(candidates),
        available_tasks=determine_available_tasks(
            is_labor_force=bool(is_labor_force),
            wealth_level=wealth_level,
            is_employed=bool(final_attrs.get("is_employed", False)),
            government_extra_subsidy=bool(final_attrs.get("government_extra_subsidy", False)),
        ),
        attributes=final_attrs,
    )

def create_player(
    selected_tick: int,
    is_labor_force: bool,
    wealth_level: int,
    risk_preference: str,
    households_path: str = DEFAULT_HOUSEHOLDS_PATH,
    output_dir: str = DEFAULT_PLAYER_DIR,
    player_filename: str = DEFAULT_PLAYER_FILENAME,
) -> dict[str, Any]:
    result = match_player_to_agent(
        households_path=households_path,
        selected_tick=selected_tick,
        is_labor_force=is_labor_force,
        wealth_level=wealth_level,
        risk_preference=risk_preference,
    )

    player_record = {
        "matched_agent_id": result.agent_id,
        "selected_tick": result.selected_tick,
        "is_labor_force": result.is_labor_force,
        "wealth_level": result.requested_wealth_level,
        "risk_preference": result.requested_risk,
        "matched_risk": result.matched_risk,
        "risk_distance": result.risk_distance,
        "exact_risk_match": result.exact_risk_match,
        "available_tasks": result.available_tasks,
        "attributes": result.attributes,
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, player_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(player_record, f, ensure_ascii=False, indent=2)
    player_record["_player_json_path"] = out_path
    return player_record

def get_environment_snapshot(
    env_path: str, selected_tick: int
) -> dict[str, Any]:
    tick_0based = _tick_to_index(selected_tick)
    if not os.path.isfile(env_path):
        raise FileNotFoundError(f"information_environment.json not found: {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        env_data = json.load(f)
    for rec in env_data.get("ticks", []):
        if rec.get("tick") == tick_0based:
            return rec["tick_start"]
    raise KeyError(f"Environment data has no record for tick={tick_0based}")

def _parse_bool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "t", "yes", "y", "labor")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Player-Agent matching (Economic World Model game interaction)"
    )
    parser.add_argument("--tick", type=int, required=True, help="Player selected tick (1-13)")
    parser.add_argument(
        "--labor-force", type=str, required=True,
        help="Identity: true=labor force / false=non-labor force",
    )
    parser.add_argument("--wealth", type=int, required=True, help="Wealth level (1-5)")
    parser.add_argument(
        "--risk", type=str, required=True,
        choices=list(RISK_ORDER), help="Risk preference",
    )
    parser.add_argument(
        "--households", type=str, default=DEFAULT_HOUSEHOLDS_PATH,
        help=f"households.json path (default: {DEFAULT_HOUSEHOLDS_PATH})",
    )
    parser.add_argument(
        "--out-dir", type=str, default=DEFAULT_PLAYER_DIR,
        help=f"Player JSON output directory (default: {DEFAULT_PLAYER_DIR})",
    )
    parser.add_argument(
        "--out-name", type=str, default=DEFAULT_PLAYER_FILENAME,
        help=f"Player JSON filename (default: {DEFAULT_PLAYER_FILENAME})",
    )
    args = parser.parse_args()

    player = create_player(
        selected_tick=args.tick,
        is_labor_force=_parse_bool(args.labor_force),
        wealth_level=args.wealth,
        risk_preference=args.risk,
        households_path=args.households,
        output_dir=args.out_dir,
        player_filename=args.out_name,
    )

    print("=" * 60)
    print("  Match Result")
    print("=" * 60)
    print(f"  Selection: tick={player['selected_tick']}, "
          f"identity={'labor force' if player['is_labor_force'] else 'non-labor force'}, "
          f"wealth_level={player['wealth_level']}, risk={player['risk_preference']}")
    print(f"  Matched agent_id = {player['matched_agent_id']}")
    print(f"  Agent risk preference = {player['matched_risk']} "
          f"(distance {player['risk_distance']}, "
          f"{'exact match' if player['exact_risk_match'] else 'nearest match'})")
    task_str = " → ".join(
        f"{TASK_LABELS[t]}({TASK_LOCATIONS[t]})" for t in player["available_tasks"]
    )
    print(f"  Available tasks ({len(player['available_tasks'])}): {task_str}")
    print("-" * 60)
    print(f"  Player JSON written to: {player['_player_json_path']}")

if __name__ == "__main__":
    main()
