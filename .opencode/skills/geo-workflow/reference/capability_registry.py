#!/usr/bin/env python3
"""Load and validate skill capability manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_CAPABILITY_KEYS = {
    "id",
    "produces",
    "required_parameters",
    "optional_parameters",
    "spatial_filters",
    "temporal_filters",
    "adapter",
}


class CapabilityRegistry:
    def __init__(self, skills_directory: str | Path):
        self.skills_directory = Path(skills_directory)
        self.skills: dict[str, dict[str, Any]] = {}
        self.capabilities: dict[tuple[str, str], dict[str, Any]] = {}

    def load(self) -> "CapabilityRegistry":
        self.skills.clear()
        self.capabilities.clear()
        for path in sorted(self.skills_directory.glob("*/capabilities.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            self._validate_manifest(data, path)
            skill_id = data["skill_id"]
            if skill_id in self.skills:
                raise ValueError(
                    f"Doppelte Skill-ID in Capability Registry: {skill_id}"
                )
            data["_path"] = str(path)
            self.skills[skill_id] = data
            for capability in data["capabilities"]:
                key = (skill_id, capability["id"])
                if key in self.capabilities:
                    raise ValueError(
                        f"Doppelte Capability: {skill_id}/{capability['id']}"
                    )
                self.capabilities[key] = capability
        return self

    @staticmethod
    def _validate_manifest(data: dict[str, Any], path: Path) -> None:
        if not isinstance(data.get("skill_id"), str) or not data["skill_id"]:
            raise ValueError(f"Ungültige skill_id in {path}")
        if not isinstance(data.get("version"), int) or data["version"] < 1:
            raise ValueError(f"Ungültige version in {path}")
        if not isinstance(data.get("capabilities"), list):
            raise ValueError(f"capabilities fehlt in {path}")
        for capability in data["capabilities"]:
            missing = REQUIRED_CAPABILITY_KEYS - capability.keys()
            if missing:
                raise ValueError(f"{path}: Capability fehlen Felder {sorted(missing)}")

    def get(self, skill_id: str, capability_id: str) -> dict[str, Any]:
        try:
            return self.capabilities[(skill_id, capability_id)]
        except KeyError as error:
            raise ValueError(
                f"Nicht unterstützte Capability: {skill_id}/{capability_id}"
            ) from error

    def validate_node(self, node: dict[str, Any]) -> list[str]:
        capability = self.get(node["producer_skill"], node["capability"])
        parameters = node.get("parameters") or {}
        missing = [
            name for name in capability["required_parameters"] if name not in parameters
        ]
        produced = set(capability["produces"])
        unexpected = set(node.get("entity_types") or []) - produced
        errors = []
        if missing:
            errors.append(f"Fehlende Parameter: {', '.join(missing)}")
        if unexpected:
            errors.append(
                f"Nicht erzeugbare Entitätstypen: {', '.join(sorted(unexpected))}"
            )
        return errors
