#!/usr/bin/env python3
"""Validate, lower, and render one Ladder IR document without an API call."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

METHOD_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = METHOD_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from plc_loop.ladder import LadderError, compile_ladder_document  # noqa: E402
from plc_loop.delta_dvp import (  # noqa: E402
    NativeLdError,
    build_ispsoft_package,
    render_native_ld_function_block_source,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Ladder IR JSON")
    parser.add_argument("--interface", required=True, type=Path, help="fixed interface.st")
    parser.add_argument("--task-id")
    parser.add_argument("--st-output", required=True, type=Path)
    parser.add_argument("--svg-output", required=True, type=Path)
    parser.add_argument(
        "--ispsoft-source-output",
        type=Path,
        help="optional ISPSoft native [FB,LD] Unzipped.src output",
    )
    parser.add_argument(
        "--ispsoft-package-output",
        type=Path,
        help="optional encrypted ISPSoft native-LD .FBU output",
    )
    parser.add_argument(
        "--ispsoft-password-env",
        default="DELTAPLC_ISPSOFT_SOURCE_PASSWORD",
        help="environment variable used only when --ispsoft-package-output is requested",
    )
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        compiled = compile_ladder_document(
            document,
            args.interface.read_text(encoding="utf-8"),
            args.task_id,
        )
        native = None
        if args.ispsoft_source_output is not None or args.ispsoft_package_output is not None:
            native = render_native_ld_function_block_source(
                document,
                args.interface.read_text(encoding="utf-8"),
                args.task_id,
            )
    except (OSError, json.JSONDecodeError, LadderError, NativeLdError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False))
        return 1
    args.st_output.parent.mkdir(parents=True, exist_ok=True)
    args.svg_output.parent.mkdir(parents=True, exist_ok=True)
    args.st_output.write_text(compiled.st_program, encoding="utf-8")
    args.svg_output.write_text(compiled.svg, encoding="utf-8")
    if native is not None and args.ispsoft_source_output is not None:
        args.ispsoft_source_output.parent.mkdir(parents=True, exist_ok=True)
        args.ispsoft_source_output.write_bytes(native.source)
    if native is not None and args.ispsoft_package_output is not None:
        password = os.environ.get(args.ispsoft_password_env, "")
        if not password:
            print(json.dumps({
                "status": "fail",
                "error": f"environment variable {args.ispsoft_password_env} is empty",
            }, ensure_ascii=False))
            return 1
        args.ispsoft_package_output.parent.mkdir(parents=True, exist_ok=True)
        args.ispsoft_package_output.write_bytes(
            build_ispsoft_package(native.source, password)
        )
    print(json.dumps({
        "status": "pass",
        "language": "ld",
        "semantic_validation_artifact": str(args.st_output),
        "visual_artifact": str(args.svg_output),
        "native_ispsoft_ld_exported": native is not None,
        "native_ispsoft_ld_source": str(args.ispsoft_source_output) if args.ispsoft_source_output else None,
        "native_ispsoft_ld_package": str(args.ispsoft_package_output) if args.ispsoft_package_output else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
