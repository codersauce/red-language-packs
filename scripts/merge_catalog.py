#!/usr/bin/env python3
"""Merge target metadata from one pack release into the versioned catalog."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


def comparable(entry: dict) -> dict:
    value = deepcopy(entry)
    value.pop("artifacts", None)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    catalog = json.loads(args.base.read_text())
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("packages"), list):
        raise ValueError("base catalog must use schema_version 1 and a packages array")
    packages = {entry["id"]: entry for entry in catalog["packages"]}
    pending: dict[str, dict] = {}
    for path in args.metadata:
        entry = json.loads(path.read_text())
        package_id = entry["id"]
        if package_id not in pending:
            pending[package_id] = entry
            continue
        if comparable(pending[package_id]) != comparable(entry):
            raise ValueError(f"target metadata disagrees for {package_id}")
        for target, artifact in entry["artifacts"].items():
            if target in pending[package_id]["artifacts"]:
                raise ValueError(f"duplicate target {target} for {package_id}")
            pending[package_id]["artifacts"][target] = artifact
    packages.update(pending)
    output = {
        "schema_version": 1,
        "packages": [packages[key] for key in sorted(packages)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
