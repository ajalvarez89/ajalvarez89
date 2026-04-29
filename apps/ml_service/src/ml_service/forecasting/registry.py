"""Local model registry: champion/challenger directory layout."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REGISTRY_ROOT = Path("/app/models")


@dataclass
class RegistryEntry:
    name: str
    version: str
    base_dir: Path
    metadata: dict


class ModelRegistry:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or REGISTRY_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def list_versions(self, name: str) -> list[str]:
        d = self.root / name
        if not d.exists():
            return []
        return sorted([p.name for p in d.iterdir() if p.is_dir()])

    def champion(self, name: str) -> RegistryEntry | None:
        d = self.root / name
        link = d / "champion.json"
        if not link.exists():
            return None
        version = json.loads(link.read_text())["version"]
        return self._entry(name, version)

    def set_champion(self, name: str, version: str) -> None:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "champion.json").write_text(json.dumps({"version": version}, indent=2))

    def _entry(self, name: str, version: str) -> RegistryEntry:
        base = self.root / name / version
        meta_file = base / "metadata.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        return RegistryEntry(name=name, version=version, base_dir=base, metadata=meta)

    def get(self, name: str, version: str) -> RegistryEntry:
        return self._entry(name, version)
