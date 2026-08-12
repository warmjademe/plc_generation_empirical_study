#!/usr/bin/env python3
"""Qualify every reference and authored negative before a model experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from plc_loop.dataset import TaskPackage, load_task
from plc_loop.orchestrator import load_config
from plc_loop.validators import validators_from_config


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-root", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--plcverif-wall-timeout",
        type=int,
        help="qualification-only PLCverif process timeout; this changes no property or verdict",
    )
    parser.add_argument(
        "--retry-nonqualified",
        action="store_true",
        help="archive and rerun completed task records that are not qualified",
    )
    args = parser.parse_args()
    bank_root = args.bank_root.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise FileExistsError(f"refusing to overwrite qualification output {output}")
    output.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config.resolve())
    configured = {validator.name: validator for validator in validators_from_config(config["validators"], Path(config["_config_dir"]))}
    if args.plcverif_wall_timeout is not None:
        if args.plcverif_wall_timeout <= 0:
            raise ValueError("--plcverif-wall-timeout must be positive")
        configured["plcverif"] = replace(
            configured["plcverif"], timeout_seconds=args.plcverif_wall_timeout
        )
    task_dirs = sorted(path for path in (bank_root / "tasks").iterdir() if path.is_dir())

    # Bind the qualification record to the adapter scripts, libraries, and tool
    # launchers actually named by the frozen validator commands.  The config hash
    # alone would not detect a later edit to one of those files.
    validator_artifacts = {}
    for name, validator in sorted(configured.items()):
        for token in getattr(validator, "command", ()):
            path = Path(token)
            if path.is_file():
                validator_artifacts[f"{name}:{path}"] = sha256(path)
    openplc_image = None
    openplc_validator = configured.get("openplc")
    if openplc_validator is not None:
        command = list(getattr(openplc_validator, "command", ()))
        try:
            docker = command[command.index("--docker") + 1]
            image = command[command.index("--image") + 1]
            inspected = subprocess.run(
                [docker, "image", "inspect", "--format", "{{.Id}}", image],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if inspected.returncode == 0 and inspected.stdout.strip():
                openplc_image = {"tag": image, "image_id": inspected.stdout.strip()}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass

    run_spec = {
        "schema_version": "1.0",
        "bank_manifest_sha256": sha256(bank_root / "manifest.jsonl"),
        "config_sha256": sha256(args.config.resolve()),
        "validator_artifact_sha256": validator_artifacts,
        "openplc_container_image": openplc_image,
        "expected_task_count": args.expected_count,
    }
    run_spec_path = output / "run_spec.json"
    if run_spec_path.is_file():
        previous_spec = json.loads(run_spec_path.read_text(encoding="utf-8"))
        if previous_spec != run_spec:
            raise RuntimeError("resume refused: frozen bank, config, validator artifacts, or image changed")
    else:
        write_json(run_spec_path, run_spec)

    # Preserve interrupted evidence instead of deleting it.  A task directory is
    # reusable only after its atomic per-task qualification record exists.
    interrupted_root = output / "interrupted"
    for task_dir in task_dirs:
        task_output = output / task_dir.name
        record_path = task_output / "qualification.json"
        should_retry = False
        if record_path.is_file() and args.retry_nonqualified:
            should_retry = json.loads(record_path.read_text(encoding="utf-8")).get("qualified") is not True
        if not task_output.exists() or (record_path.is_file() and not should_retry):
            continue
        if not args.resume:
            raise RuntimeError(f"incomplete task output without --resume: {task_output}")
        interrupted_root.mkdir(exist_ok=True)
        destination = interrupted_root / task_dir.name
        suffix = 1
        while destination.exists():
            suffix += 1
            destination = interrupted_root / f"{task_dir.name}__{suffix}"
        task_output.rename(destination)

    def qualify(task_dir: Path) -> dict:
        task = load_task(task_dir)
        existing_record = output / task.task_id / "qualification.json"
        if args.resume and existing_record.is_file():
            record = json.loads(existing_record.read_text(encoding="utf-8"))
            expected_hashes = {
                "reference": sha256(task_dir / "reference.st"),
                "authored_negative": sha256(task_dir / "negative_control/NC1.st"),
            }
            actual_hashes = {
                role: value.get("candidate_sha256")
                for role, value in record.get("candidates", {}).items()
            }
            if record.get("task_id") != task.task_id or actual_hashes != expected_hashes:
                raise RuntimeError(f"resume refused: completed record for {task.task_id} does not match the frozen candidates")
            return {**record, "resumed": True}
        validators = [configured["compiler"], configured["plcverif"], configured["openplc"]]
        for validator in validators:
            validator.preflight(task)
        candidates = {
            "reference": task_dir / "reference.st",
            "authored_negative": task_dir / "negative_control/NC1.st",
        }
        task_output = output / task.task_id
        task_output.mkdir()
        records = {}
        for role, candidate in candidates.items():
            artifact = task_output / role
            artifact.mkdir()
            validation_task = task
            profile_name = "all_mandatory_properties"
            if role == "authored_negative":
                # A calibration negative has one predeclared defect and only
                # needs one trustworthy witness.  Checking unrelated properties
                # before its target wastes most qualification time, especially
                # for stateful edge/timer tasks.  Keep the same MatIEC ->
                # PLCverif -> OpenPLC order, but give PLCverif a task view that
                # contains only the target requirement's native property.
                control = json.loads((task_dir / "negative_control/index.json").read_text(encoding="utf-8"))["controls"][0]
                target_requirements = set(control["target_requirement_ids"])
                property_document = json.loads((task_dir / "properties.json").read_text(encoding="utf-8"))
                selected = [
                    item for item in property_document["properties"]
                    if target_requirements.intersection(item.get("requirement_ids", []))
                ]
                if selected and all(item.get("plcverif", {}).get("cases") for item in selected):
                    profile_document = {**property_document, "properties": selected}
                    profile = dict(profile_document["plcverif_profile"])
                    profile["native_property_count"] = sum(bool(item["plcverif"]["cases"]) for item in selected)
                    profile["fully_native_property_count"] = sum(
                        item["plcverif"].get("coverage") == "complete" for item in selected
                    )
                    profile["total_property_count"] = len(selected)
                    profile_document["plcverif_profile"] = profile
                    profile_dir = artifact / "target_property_profile"
                    profile_dir.mkdir()
                    write_json(profile_dir / "metadata.json", task.metadata)
                    write_json(profile_dir / "properties.json", profile_document)
                    write_json(
                        profile_dir / "openplc_tests.json",
                        json.loads((task_dir / "openplc_tests.json").read_text(encoding="utf-8")),
                    )
                    validation_task = TaskPackage(
                        root=profile_dir,
                        metadata=task.metadata,
                        requirement_text=task.requirement_text,
                        interface_text=task.interface_text,
                    )
                    profile_name = "predeclared_negative_target_only"
                else:
                    # Some independently authored calibration negatives target a
                    # requirement outside PLCverif's qualified invariant fragment.
                    # They must still traverse the same three gates: run every
                    # available native property, then let the independent OpenPLC
                    # oracle kill the predeclared defect.  Unsupported formal
                    # syntax is never treated as a proof or as a counterexample.
                    profile_name = "all_native_properties_then_openplc_negative_target"
            gates = []
            for validator in validators:
                result = validator.run(validation_task, candidate, artifact)
                gates.append(result)
                if result.status == "fail" and validator.blocking:
                    break
                if result.status == "inconclusive" and validator.blocking and getattr(validator, "inconclusive_is_blocking", True):
                    break
            records[role] = {
                "candidate_sha256": sha256(candidate),
                "qualification_profile": profile_name,
                "gates": [gate.to_dict() for gate in gates],
            }
        reference_statuses = {gate["name"]: gate["status"] for gate in records["reference"]["gates"]}
        negative_statuses = {gate["name"]: gate["status"] for gate in records["authored_negative"]["gates"]}
        reference_ok = (
            reference_statuses.get("compiler") == "pass"
            and reference_statuses.get("plcverif") == "pass"
            and reference_statuses.get("openplc") == "pass"
        )
        negative_killed = (
            negative_statuses.get("compiler") == "pass"
            and any(negative_statuses.get(name) == "fail" for name in ("plcverif", "openplc"))
        )
        record = {
            "task_id": task.task_id,
            "reference_ok": reference_ok,
            "authored_negative_killed": negative_killed,
            "qualified": reference_ok and negative_killed,
            "driver_protocol": "reference-all-properties_negative-predeclared-target-v2",
            "candidates": records,
        }
        write_json(task_output / "qualification.json", record)
        return record

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(qualify, task_dir): task_dir.name for task_dir in task_dirs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {"task_id": task_id, "qualified": False, "error": f"{type(exc).__name__}: {exc}"}
            records.append(record)
            print(json.dumps({"task_id": task_id, "qualified": record["qualified"], "error": record.get("error")}, ensure_ascii=False), flush=True)
    records.sort(key=lambda item: item["task_id"])
    document = {
        "schema_version": "1.0",
        "scope": "reference MatIEC -> PLCverif -> OpenPLC plus compile-valid authored negative",
        "bank_manifest_sha256": sha256(bank_root / "manifest.jsonl"),
        "config_sha256": sha256(args.config.resolve()),
        "validator_artifact_sha256": validator_artifacts,
        "openplc_container_image": openplc_image,
        "plcverif_wall_timeout_seconds": configured["plcverif"].timeout_seconds,
        "task_count": len(records),
        "qualified_count": sum(bool(record["qualified"]) for record in records),
        "resumed_task_count": sum(bool(record.get("resumed")) for record in records),
        "driver_protocol_counts": {
            protocol: sum(record.get("driver_protocol", "reference-and-negative-all-properties-v1") == protocol for record in records)
            for protocol in sorted({
                record.get("driver_protocol", "reference-and-negative-all-properties-v1")
                for record in records
            })
        },
        "expected_task_count": args.expected_count,
        "status": "pass" if len(records) == args.expected_count and all(record["qualified"] for record in records) else "fail",
        "tasks": records,
    }
    write_json(output / "qualification.json", document)
    print(json.dumps({
        "status": document["status"], "task_count": document["task_count"],
        "qualified_count": document["qualified_count"],
        "failed_tasks": [record["task_id"] for record in records if not record["qualified"]],
    }, ensure_ascii=False))
    return 0 if document["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
