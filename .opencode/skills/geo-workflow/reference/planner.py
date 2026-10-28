#!/usr/bin/env python3
"""Validate, order and combine candidates for a geo workflow."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from capability_registry import CapabilityRegistry
from constraint_engine import SUPPORTED_TYPES, evaluate_ready_constraints


def validate_candidate(feature: dict[str, Any], node_id: str) -> None:
    if feature.get("type") != "Feature":
        raise ValueError(f"{node_id}: Kandidat ist kein GeoJSON-Feature")
    if not feature.get("geometry"):
        raise ValueError(f"{node_id}: Kandidatengeometrie fehlt")
    properties = feature.get("properties") or {}
    required = {
        "candidate_id",
        "producer_skill",
        "entity_type",
        "temporal",
        "score",
        "confidence",
        "sources",
        "warnings",
    }
    missing = required - properties.keys()
    if missing:
        raise ValueError(f"{node_id}: Kandidat fehlen Felder {sorted(missing)}")
    confidence = float(properties["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError(f"{node_id}: confidence liegt nicht zwischen 0 und 1")
    temporal = properties["temporal"] or {}
    temporal_required = {"start", "end", "duration_minutes", "timezone", "precision"}
    missing_temporal = temporal_required - temporal.keys()
    if missing_temporal:
        raise ValueError(
            f"{node_id}: temporal fehlen Felder {sorted(missing_temporal)}"
        )
    for key in ("start", "end"):
        if temporal.get(key):
            parsed = datetime.fromisoformat(temporal[key].replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError(f"{node_id}: temporal.{key} benötigt eine Zeitzone")
    duration = temporal.get("duration_minutes")
    if duration is not None and float(duration) < 0:
        raise ValueError(f"{node_id}: negative Dauer")


def aggregate_candidates(
    node_id: str, candidates: list[dict[str, Any]], entity_type: str
) -> dict[str, Any]:
    """Represent a complete candidate set as one GeometryCollection feature."""
    sources = []
    warnings = []
    confidences = []
    for candidate in candidates:
        properties = candidate["properties"]
        sources.extend(properties.get("sources") or [])
        warnings.extend(properties.get("warnings") or [])
        confidences.append(float(properties.get("confidence", 0)))
    return {
        "type": "Feature",
        "geometry": {
            "type": "GeometryCollection",
            "geometries": [candidate["geometry"] for candidate in candidates],
        },
        "properties": {
            "candidate_id": f"{node_id}:all",
            "producer_skill": "geo-workflow",
            "entity_type": entity_type,
            "start": None,
            "end": None,
            "temporal": {
                "start": None,
                "end": None,
                "duration_minutes": None,
                "timezone": None,
                "precision": "unknown",
            },
            "score": 0,
            "confidence": min(confidences, default=0),
            "sources": sources,
            "warnings": sorted(set(warnings)),
            "raw_reference": None,
            "member_count": len(candidates),
        },
    }


def validate_workflow(workflow: dict[str, Any], registry: CapabilityRegistry) -> None:
    for key in ("workflow_id", "nodes", "constraints"):
        if key not in workflow:
            raise ValueError(f"Workflow-Pflichtfeld fehlt: {key}")
    node_ids = [node.get("id") for node in workflow["nodes"]]
    if any(not node_id for node_id in node_ids) or len(node_ids) != len(set(node_ids)):
        raise ValueError("Knoten-IDs fehlen oder sind nicht eindeutig")
    known = set(node_ids)
    errors = []
    for node in workflow["nodes"]:
        errors.extend(
            f"{node['id']}: {message}" for message in registry.validate_node(node)
        )
        unknown_dependencies = set(node.get("depends_on") or []) - known
        if unknown_dependencies:
            errors.append(
                f"{node['id']}: unbekannte Abhängigkeiten {sorted(unknown_dependencies)}"
            )
    for constraint in workflow["constraints"]:
        kind = constraint.get("type")
        if kind not in SUPPORTED_TYPES:
            errors.append(f"Unbekannter Constraint-Typ: {kind}")
        unary = {"starts_between", "ends_between", "duration_between", "active_at"}
        if kind not in unary and not constraint.get("to"):
            errors.append(f"Constraint '{kind}' benötigt ein to-Feld")
        parameters = constraint.get("parameters") or {}
        required_parameters = {
            "starts_between": {"start", "end"},
            "ends_between": {"start", "end"},
            "duration_between": {"min_minutes", "max_minutes"},
            "active_at": {"at"},
            "avoids": {"min_distance_m"},
        }.get(kind, set())
        missing_parameters = required_parameters - parameters.keys()
        if missing_parameters:
            errors.append(
                f"Constraint '{kind}' fehlen Parameter {sorted(missing_parameters)}"
            )
        for field in ("from", "to"):
            reference = constraint.get(field)
            if reference and reference not in known:
                errors.append(
                    f"Constraint referenziert unbekannten Knoten: {reference}"
                )
    if errors:
        raise ValueError("\n".join(errors))
    plan_node_order(workflow)


def plan_node_order(workflow: dict[str, Any]) -> list[str]:
    """Topological order, with anchored/selective nodes preferred among peers."""
    nodes = {node["id"]: node for node in workflow["nodes"]}
    dependencies = {
        node_id: set(node.get("depends_on") or []) for node_id, node in nodes.items()
    }

    def priority(node_id: str):
        params = nodes[node_id].get("parameters") or {}
        anchors = sum(
            key in params
            for key in (
                "at",
                "date",
                "time",
                "start",
                "end",
                "bbox",
                "geometry",
                "arrival_window",
                "departure_window",
            )
        )
        return (-anchors, node_id)

    result = []
    while dependencies:
        ready = sorted(
            (node_id for node_id, deps in dependencies.items() if not deps),
            key=priority,
        )
        if not ready:
            cycle = ", ".join(sorted(dependencies))
            raise ValueError(f"Zyklische Knotenabhängigkeiten: {cycle}")
        for node_id in ready:
            result.append(node_id)
            dependencies.pop(node_id)
            for deps in dependencies.values():
                deps.discard(node_id)
    return result


def deduplicate_route_candidates(
    node_id: str, features: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Dublikate im Kandidatensatz entfernen (Linienfolge + Dauer + Umstiege).

    Relevant für Routen-Kandidaten (ÖPNV, Ride), die mehrfach in leicht
    unterschiedlichen Node-IDs erscheinen, aber dieselbe Linienfolge und
    Dauer tragen. Rückgabe: deduplizierte Liste.
    """
    deduped = []
    seen = set()
    for feature in features:
        properties = feature.get("properties") or {}
        segments = properties.get("segments")
        if not segments:
            deduped.append(feature)
            continue
        signature = (
            properties.get("entity_type"),
            tuple(str(leg.get("linie") or "") for leg in segments),
            round(
                float((properties.get("temporal") or {}).get("duration_minutes") or 0),
                1,
            ),
            properties.get("transfers"),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(feature)
    if len(deduped) != len(features):
        # deutlich machen, dass Kandidatenanalysen ohne Duplikate verlaufen
        pass
    return deduped


def solve(
    workflow: dict[str, Any], candidates: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Backtracking solver with hard pruning and visible soft penalties."""
    order = plan_node_order(workflow)
    limits = workflow.get("limits") or {}
    max_candidates = int(limits.get("max_candidates_per_node", 50))
    max_combinations = int(limits.get("max_combinations", 5000))
    max_runtime = float(limits.get("max_runtime_seconds", 900))
    deadline = time.monotonic() + max_runtime
    constraints = workflow.get("constraints") or []
    solutions: list[dict[str, Any]] = []
    partial_by_depth: dict[int, list[dict[str, Any]]] = {}
    rejections: Counter[str] = Counter()
    explored = 0
    truncated = False

    nodes_by_id = {node["id"]: node for node in workflow["nodes"]}
    prepared_candidates: dict[str, list[dict[str, Any]]] = {}
    for node_id in order:
        if node_id not in candidates:
            raise ValueError(f"Kandidaten für Knoten '{node_id}' fehlen")
        for candidate in candidates[node_id]:
            validate_candidate(candidate, node_id)
            expected = set(nodes_by_id[node_id].get("entity_types") or [])
            actual = (candidate.get("properties") or {}).get("entity_type")
            if expected and actual not in expected:
                raise ValueError(
                    f"{node_id}: Entitätstyp '{actual}' nicht in {sorted(expected)}"
                )
        if nodes_by_id[node_id].get("selection", "one") == "all":
            entity_type = next(iter(expected), "candidate_set")
            prepared_candidates[node_id] = [
                aggregate_candidates(node_id, candidates[node_id], entity_type)
            ]
        else:
            prepared_candidates[node_id] = deduplicate_route_candidates(
                node_id, candidates[node_id]
            )

    def visit(
        index: int,
        assignment: dict[str, dict[str, Any]],
        penalties: list[dict[str, Any]],
    ):
        nonlocal explored, truncated
        if explored >= max_combinations or time.monotonic() >= deadline:
            truncated = True
            return
        if index == len(order):
            base_score = sum(
                float((feature.get("properties") or {}).get("score", 0))
                for feature in assignment.values()
            )
            solutions.append(
                {
                    "assignments": dict(assignment),
                    "score": base_score - sum(item["penalty"] for item in penalties),
                    "soft_violations": list(penalties),
                }
            )
            return

        node_id = order[index]
        ranked = sorted(
            prepared_candidates[node_id],
            key=lambda feature: float(
                (feature.get("properties") or {}).get("score", 0)
            ),
            reverse=True,
        )[:max_candidates]
        for feature in ranked:
            explored += 1
            assignment[node_id] = feature
            newly_ready = [
                constraint
                for constraint in constraints
                if node_id in {constraint.get("from"), constraint.get("to")}
            ]
            evaluated = evaluate_ready_constraints(newly_ready, assignment)
            hard_failures = [
                result
                for constraint, result in evaluated
                if not result.passed and constraint.get("hard", True)
            ]
            if hard_failures:
                for failure in hard_failures:
                    rejections[failure.reason] += 1
                valid_prefix = {
                    assigned_id: assigned
                    for assigned_id, assigned in assignment.items()
                    if assigned_id != node_id
                }
                partial_by_depth.setdefault(index, []).append(valid_prefix)
            else:
                new_penalties = [
                    {
                        "reason": result.reason,
                        "penalty": result.penalty,
                        "constraint": constraint["type"],
                    }
                    for constraint, result in evaluated
                    if not result.passed and not constraint.get("hard", True)
                ]
                visit(index + 1, assignment, penalties + new_penalties)
            assignment.pop(node_id, None)
            if truncated:
                break

    visit(0, {}, [])
    solutions.sort(key=lambda solution: solution["score"], reverse=True)
    partial_solutions = []
    if not solutions and partial_by_depth:
        deepest = max(partial_by_depth)
        for assignment in partial_by_depth[deepest][:3]:
            partial_solutions.append(
                {
                    "assigned_nodes": list(assignment),
                    "assignments": assignment,
                    "missing_nodes": [
                        node_id for node_id in order if node_id not in assignment
                    ],
                }
            )
    return {
        "workflow_id": workflow["workflow_id"],
        "complete_solutions": solutions,
        "partial_solutions": partial_solutions,
        "rejections": dict(rejections),
        "warnings": ["Suchlimits erreicht; Ergebnis ist möglicherweise unvollständig"]
        if truncated
        else [],
        "explored": explored,
        "node_order": order,
    }


def _load_candidates(
    path: Path, workflow: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    result = {}
    for node in workflow["nodes"]:
        candidate_path = path / node["id"] / "kandidaten.geojson"
        status_path = path / node["id"] / "status.json"
        if not status_path.exists():
            raise ValueError(f"Status für Knoten '{node['id']}' fehlt")
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") not in {"success", "empty", "degraded", "error"}:
            raise ValueError(f"Ungültiger Status für Knoten '{node['id']}'")
        if status["status"] == "error":
            raise RuntimeError(
                f"Knoten '{node['id']}' fehlgeschlagen: "
                f"{status.get('error_message') or status.get('error_class') or 'unbekannter Fehler'}"
            )
        data = json.loads(candidate_path.read_text(encoding="utf-8"))
        result[node["id"]] = data["features"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Geo-Workflow planen und Kandidaten verbinden"
    )
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--skills", default=".opencode/skills")
    parser.add_argument("--candidates")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    workflow = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    registry = CapabilityRegistry(args.skills).load()
    validate_workflow(workflow, registry)
    result: dict[str, Any] = {
        "workflow_id": workflow["workflow_id"],
        "node_order": plan_node_order(workflow),
    }
    if args.candidates:
        result = solve(workflow, _load_candidates(Path(args.candidates), workflow))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
