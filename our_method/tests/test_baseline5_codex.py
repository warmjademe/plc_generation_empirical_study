from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE_CODES = Path(__file__).resolve().parents[2]
if str(SOURCE_CODES) not in sys.path:
    sys.path.insert(0, str(SOURCE_CODES))

from baseline5_codex import (  # noqa: E402
    EXACT_MODEL,
    CodexBaselineHarness,
    CodexCLI,
    CodexCallResult,
    _audit_cli_events,
    _audit_rollouts,
    _estimate_cost,
    _workspace_hashes,
)
from plc_loop.models import Evidence, GateResult  # noqa: E402


TASK = SOURCE_CODES / "datasets/tasks/C01_M01_two_out_of_three_vote"
CONFIG = SOURCE_CODES / "our_method/configs/codex_gpt_5_6_luna_external_baseline.json"


class FakeCodexAgent:
    requested_model = EXACT_MODEL
    provider_id = "test-double"

    def __init__(self, candidates: list[str]):
        self.candidates = list(candidates)
        self.prompts: list[str] = []
        self.invocations: list[dict] = []

    def preflight(self):
        return {
            "executable": "/fake/codex",
            "version": "codex-cli fake",
            "executable_sha256": "0" * 64,
        }

    def invoke(self, workspace: Path, prompt: str, call_dir: Path):
        self.prompts.append(prompt)
        self.invocations.append({
            "initial_candidate": (workspace / "candidate.st").read_text(encoding="utf-8"),
            "workspace_files": sorted(path.name for path in workspace.iterdir()),
        })
        source = self.candidates.pop(0)
        (workspace / "candidate.st").write_text(source, encoding="utf-8")
        return CodexCallResult(
            session_id=f"fake-{len(self.prompts)}",
            result_text="ready",
            resolved_models=(EXACT_MODEL,),
            usage={"input_tokens": 10, "output_tokens": 5, "estimated_cost_usd": 0.000008},
            duration_ms=1,
            agent_turns=1,
            agent_items=2,
            estimated_cost_usd=0.000008,
            access_audit_valid=True,
            instruction_isolation_valid=True,
        )


class FakeValidator:
    def __init__(
        self,
        name: str,
        *,
        sealed: bool = False,
        sealed_status: str = "pass",
        sealed_statuses: list[str] | None = None,
    ):
        self.name = name
        self.sealed = sealed
        self.sealed_status = sealed_status
        self.sealed_statuses = list(sealed_statuses or [])
        self.blocking = True
        self.calls = 0

    def preflight(self, task):
        return None

    def run(self, task, candidate_path, artifact_dir):
        self.calls += 1
        if self.sealed:
            status = self.sealed_statuses.pop(0) if self.sealed_statuses else self.sealed_status
            return GateResult(self.name, status, "sealed verdict")
        if "GOOD" in candidate_path.read_text(encoding="utf-8"):
            return GateResult(self.name, "pass", "visible pass", passed_requirement_ids=("R1",))
        return GateResult(
            self.name,
            "fail",
            "visible failure",
            evidence=(Evidence(self.name, "test_failure", "expected GOOD", ("R1",)),),
        )


class Baseline5Tests(unittest.TestCase):
    def test_candidates_are_independent_and_early_stop_on_full_pass(self):
        agent = FakeCodexAgent(["BAD", "GOOD"])
        compiler = FakeValidator("compiler")
        plcverif = FakeValidator("plcverif")
        sealed = FakeValidator("openplc", sealed=True)
        with tempfile.TemporaryDirectory() as directory:
            result = CodexBaselineHarness(
                CONFIG,
                TASK,
                Path(directory) / "run",
                agent=agent,
                validators=[compiler, plcverif, sealed],
            ).run()
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["candidates_used"], 2)
        self.assertEqual(result["model_calls_used"], 2)
        self.assertEqual(result["candidate_policy"], "independent_pass_at_10")
        self.assertFalse(result["validator_feedback_to_model"])
        self.assertEqual(sealed.calls, 1)
        self.assertEqual(agent.prompts[0], agent.prompts[1])
        self.assertEqual(
            agent.invocations[0]["initial_candidate"], agent.invocations[1]["initial_candidate"]
        )
        self.assertTrue(all("feedback.md" not in item["workspace_files"] for item in agent.invocations))

    def test_sealed_failure_is_not_disclosed_and_next_sample_is_independent(self):
        agent = FakeCodexAgent(["GOOD", "GOOD"])
        sealed = FakeValidator("openplc", sealed=True, sealed_statuses=["fail", "pass"])
        with tempfile.TemporaryDirectory() as directory:
            result = CodexBaselineHarness(
                CONFIG,
                TASK,
                Path(directory) / "run",
                agent=agent,
                validators=[FakeValidator("compiler"), FakeValidator("plcverif"), sealed],
            ).run()
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["model_calls_used"], 2)
        self.assertEqual(len(agent.prompts), 2)
        self.assertEqual(agent.prompts[0], agent.prompts[1])

    def test_independent_candidate_budget_is_exactly_capped_at_ten(self):
        agent = FakeCodexAgent(["BAD"] * 11)
        with tempfile.TemporaryDirectory() as directory:
            result = CodexBaselineHarness(
                CONFIG,
                TASK,
                Path(directory) / "run",
                agent=agent,
                validators=[
                    FakeValidator("compiler"),
                    FakeValidator("plcverif"),
                    FakeValidator("openplc", sealed=True),
                ],
            ).run()
        self.assertEqual(result["status"], "candidate_budget_exhausted")
        self.assertEqual(result["candidates_used"], 10)
        self.assertEqual(result["model_calls_used"], 10)
        self.assertEqual(len(agent.candidates), 1)

    def test_rollout_model_audit_is_exact_and_fail_closed(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            session = root / "codex/sessions/2026/08/12/run.jsonl"
            session.parent.mkdir(parents=True)
            rows = [
                {"type": "session_meta", "payload": {
                    "id": "thread-1", "cwd": str(workspace), "model_provider": "teamorouter",
                    "cli_version": "0.test", "base_instructions": "builtin",
                }},
                {"type": "turn_context", "payload": {
                    "cwd": str(workspace), "model": EXACT_MODEL,
                }},
            ]
            session.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            valid = _audit_rollouts(root / "codex", workspace, EXACT_MODEL, "teamorouter")
            self.assertTrue(valid["valid"])
            rows[1]["payload"]["model"] = "gpt-5.6-sol"
            session.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            invalid = _audit_rollouts(root / "codex", workspace, EXACT_MODEL, "teamorouter")
            self.assertFalse(invalid["valid"])
            self.assertIn("single-model protocol violation", " ".join(invalid["violations"]))

    def test_access_audit_rejects_external_reads_and_extra_files(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            workspace = Path(directory)
            for name in ("requirement.md", "interface.st", "candidate.st"):
                (workspace / name).write_text(name, encoding="utf-8")
            before = _workspace_hashes(workspace)
            (workspace / "notes.txt").write_text("unexpected", encoding="utf-8")
            events = [
                {
                    "type": "item.completed",
                    "item": {"type": "command_execution", "command": "cat /root/private.txt"},
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "file_change",
                        "changes": [{"path": "/tmp/outside.st", "kind": "update"}],
                    },
                },
            ]
            audit = _audit_cli_events(events, workspace, before, _workspace_hashes(workspace))
            self.assertFalse(audit["valid"])
            self.assertIn("outside isolated workspace", " ".join(audit["violations"]))
            self.assertIn("file_change escaped", " ".join(audit["violations"]))
            self.assertIn("undeclared files created", " ".join(audit["violations"]))

    def test_cost_uses_uncached_cached_and_output_rates(self):
        cost = _estimate_cost(
            {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 200},
            {"input_per_million": 0.20, "cached_input_per_million": 0.02, "output_per_million": 1.20},
        )
        self.assertAlmostEqual(cost, 0.000368)

    def test_cli_adapter_audits_fake_runtime_without_paid_call(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            executable = root / "codex-fake"
            executable.write_text(
                """#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
if args == ['--version']:
    print('codex-cli fake')
    raise SystemExit(0)
if args[:3] == ['debug', 'models', '--bundled']:
    print(json.dumps({'models': [{'slug': 'gpt-5.6-luna'}]}))
    raise SystemExit(0)
workspace = pathlib.Path(args[args.index('--cd') + 1])
model = args[args.index('--model') + 1]
last = pathlib.Path(args[args.index('--output-last-message') + 1])
(workspace / 'candidate.st').write_text('GOOD', encoding='utf-8')
last.write_text('ready', encoding='utf-8')
session = pathlib.Path(os.environ['CODEX_HOME']) / 'sessions' / 'run.jsonl'
session.parent.mkdir(parents=True)
rows = [
 {'type': 'session_meta', 'payload': {
     'id': 'fake-thread', 'cwd': str(workspace), 'model_provider': 'teamorouter',
     'cli_version': 'fake', 'base_instructions': 'builtin'}},
 {'type': 'turn_context', 'payload': {'cwd': str(workspace), 'model': model}},
]
session.write_text('\\n'.join(json.dumps(row) for row in rows) + '\\n', encoding='utf-8')
events = [
 {'type': 'thread.started', 'thread_id': 'fake-thread'},
 {'type': 'turn.started'},
 {'type': 'error', 'message': 'Reconnecting... 1/5'},
 {'type': 'item.completed', 'item': {'type': 'file_change', 'changes': [{'path': str(workspace / 'candidate.st'), 'kind': 'update'}]}},
 {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'ready'}},
 {'type': 'turn.completed', 'usage': {
     'input_tokens': 100, 'cached_input_tokens': 20, 'output_tokens': 10}},
]
for event in events:
    print(json.dumps(event))
""",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            workspace = root / "workspace"
            workspace.mkdir()
            for name in ("requirement.md", "interface.st", "candidate.st"):
                (workspace / name).write_text(name, encoding="utf-8")
            settings = {
                "executable": str(executable),
                "model": EXACT_MODEL,
                "reasoning_effort": "medium",
                "timeout_seconds": 10,
                "provider": {
                    "id": "teamorouter",
                    "name": "Teamorouter",
                    "base_url": "https://api.teamorouter.com/v1",
                    "api_key_env": "TEAMOROUTER_API_KEY",
                    "wire_api": "responses",
                    "supports_websockets": False,
                },
                "pricing_usd_per_million_tokens": {
                    "input_per_million": 0.20,
                    "cached_input_per_million": 0.02,
                    "output_per_million": 1.20,
                },
            }
            adapter = CodexCLI(settings)
            with mock.patch.dict(
                "os.environ", {"TEAMOROUTER_API_KEY": "fake-test-key"}, clear=False
            ):
                self.assertEqual(adapter.preflight()["version"], "codex-cli fake")
                result = adapter.invoke(workspace, "make candidate", root / "call")
            self.assertEqual(result.resolved_models, (EXACT_MODEL,))
            self.assertTrue(result.access_audit_valid)
            self.assertEqual(result.agent_turns, 1)
            self.assertEqual(result.agent_items, 2)
            self.assertEqual((workspace / "candidate.st").read_text(encoding="utf-8"), "GOOD")
            request = json.loads((root / "call/request.json").read_text(encoding="utf-8"))
            options = request["command_options"]
            for feature in (
                "plugins", "remote_plugin", "plugin_sharing", "apps", "multi_agent",
                "skill_search", "skill_mcp_dependency_install", "browser_use",
                "browser_use_external", "computer_use", "image_generation", "goals", "hooks",
            ):
                self.assertIn(feature, options)
            record = json.loads((root / "call/call_record.json").read_text(encoding="utf-8"))
            self.assertEqual(record["transport_warnings"], ["Reconnecting... 1/5"])


if __name__ == "__main__":
    unittest.main()
