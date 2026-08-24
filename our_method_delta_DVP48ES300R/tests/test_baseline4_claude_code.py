from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


# Keep this DVP variant's plc_loop package authoritative during full unittest
# discovery.  The external baseline adapter adds ../our_method/src for its own
# standalone execution; without this early import it can poison later tests
# with the sibling package solely because files are discovered alphabetically.
LOCAL_SRC = Path(__file__).resolve().parents[1] / "src"
if str(LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(LOCAL_SRC))
import plc_loop  # noqa: E402,F401


SOURCE_CODES = Path(__file__).resolve().parents[2]
if str(SOURCE_CODES) not in sys.path:
    sys.path.insert(0, str(SOURCE_CODES))

from baseline4_claude_code import (  # noqa: E402
    ClaudeCallResult,
    ClaudeCodeCLI,
    ClaudeCodeBaselineHarness,
    _audit_tool_access,
    _models_from_events,
    _parse_stream,
    _usage_from_events,
)
from plc_loop.models import Evidence, GateResult  # noqa: E402


TASK = SOURCE_CODES / "datasets" / "tasks" / "C01_M01_two_out_of_three_vote"
CONFIG = SOURCE_CODES / "our_method" / "configs" / "claude_code_sonnet5_external_baseline.json"


class FakeClaudeAgent:
    requested_model = "claude-sonnet-5"
    expected_model = re.compile(r"^claude-sonnet-5$")

    def __init__(self, candidates: list[str]):
        self.candidates = list(candidates)
        self.invocations: list[dict] = []

    def preflight(self) -> str:
        return "fake-claude-code 1.0"

    def invoke(self, workspace, prompt, call_dir, session_id):
        self.invocations.append({
            "prompt": prompt,
            "resume": False,
            "session_id": session_id,
            "initial_candidate": (workspace / "candidate.st").read_text(encoding="utf-8"),
            "workspace_files": sorted(path.name for path in workspace.iterdir()),
        })
        if not self.candidates:
            raise AssertionError("unexpected Claude Code invocation")
        (workspace / "candidate.st").write_text(self.candidates.pop(0), encoding="utf-8")
        call_dir.mkdir(parents=True)
        (call_dir / "request.json").write_text("{}\n", encoding="utf-8")
        (call_dir / "access_audit.json").write_text('{"valid": true}\n', encoding="utf-8")
        return ClaudeCallResult(
            session_id=session_id,
            result_text="candidate ready",
            resolved_models=("claude-sonnet-5",),
            usage={"input_tokens": 10, "output_tokens": 5},
            duration_ms=1,
            agent_turns=1,
            total_cost_usd=0.01,
            access_audit_valid=True,
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
        self.inconclusive_is_blocking = True
        self.calls = 0

    def preflight(self, task):
        pass

    def run(self, task, candidate_path, artifact_dir):
        self.calls += 1
        if self.sealed:
            status = self.sealed_statuses.pop(0) if self.sealed_statuses else self.sealed_status
            return GateResult(self.name, status, "sealed result")
        source = candidate_path.read_text(encoding="utf-8")
        if "GOOD" in source:
            return GateResult(self.name, "pass", "visible pass")
        return GateResult(
            self.name,
            "fail",
            "visible failure",
            evidence=(Evidence(self.name, "compile_error", "expected GOOD"),),
        )


class ClaudeCodeBaselineTests(unittest.TestCase):
    def test_candidates_are_independent_and_early_stop_on_full_pass(self):
        agent = FakeClaudeAgent(["BAD", "GOOD"])
        compiler = FakeValidator("compiler")
        formal = FakeValidator("plcverif")
        sealed = FakeValidator("openplc", sealed=True)
        with tempfile.TemporaryDirectory() as directory:
            result = ClaudeCodeBaselineHarness(
                CONFIG,
                TASK,
                Path(directory) / "run",
                agent=agent,
                validators=[compiler, formal, sealed],
            ).run()
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["candidates_used"], 2)
        self.assertEqual(result["model_calls_used"], 2)
        self.assertEqual(result["candidate_policy"], "independent_pass_at_10")
        self.assertFalse(result["validator_feedback_to_model"])
        self.assertEqual(len(result["session_ids"]), len(set(result["session_ids"])))
        self.assertNotEqual(agent.invocations[0]["session_id"], agent.invocations[1]["session_id"])
        self.assertTrue(all(not item["resume"] for item in agent.invocations))
        self.assertEqual(agent.invocations[0]["prompt"], agent.invocations[1]["prompt"])
        self.assertEqual(
            agent.invocations[0]["initial_candidate"], agent.invocations[1]["initial_candidate"]
        )
        self.assertTrue(all("feedback.md" not in item["workspace_files"] for item in agent.invocations))
        self.assertEqual(sealed.calls, 1)

    def test_sealed_failure_is_not_disclosed_and_next_sample_is_independent(self):
        agent = FakeClaudeAgent(["GOOD", "GOOD"])
        sealed = FakeValidator("openplc", sealed=True, sealed_statuses=["fail", "pass"])
        with tempfile.TemporaryDirectory() as directory:
            result = ClaudeCodeBaselineHarness(
                CONFIG,
                TASK,
                Path(directory) / "run",
                agent=agent,
                validators=[FakeValidator("compiler"), FakeValidator("plcverif"), sealed],
            ).run()
        self.assertEqual(result["status"], "verified_success")
        self.assertEqual(result["candidates_used"], 2)
        self.assertEqual(len(agent.invocations), 2)
        self.assertEqual(agent.invocations[0]["prompt"], agent.invocations[1]["prompt"])

    def test_independent_candidate_budget_is_exactly_capped_at_ten(self):
        agent = FakeClaudeAgent(["BAD"] * 11)
        with tempfile.TemporaryDirectory() as directory:
            result = ClaudeCodeBaselineHarness(
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

    def test_stream_parser_extracts_model_usage_and_cost(self):
        lines = [
            {"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 12, "output_tokens": 3},
                    "content": [],
                },
            },
            {
                "type": "result",
                "subtype": "success",
                "session_id": "abc",
                "num_turns": 1,
                "total_cost_usd": 0.02,
                "result": "done",
            },
        ]
        events = _parse_stream("\n".join(json.dumps(item) for item in lines))
        self.assertEqual(_models_from_events(events), ("claude-sonnet-5",))
        self.assertEqual(
            _usage_from_events(events),
            {"input_tokens": 12, "output_tokens": 3, "total_cost_usd": 0.02},
        )

    def test_access_audit_rejects_private_or_external_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory).resolve()
            valid = [{
                "type": "assistant",
                "message": {"content": [{
                    "type": "tool_use", "name": "Edit", "input": {"file_path": "candidate.st"}
                }]},
            }]
            invalid = [{
                "type": "assistant",
                "message": {"content": [{
                    "type": "tool_use", "name": "Read", "input": {"file_path": "../reference.st"}
                }]},
            }]
            self.assertTrue(_audit_tool_access(valid, workspace)["valid"])
            self.assertFalse(_audit_tool_access(invalid, workspace)["valid"])

    def test_cli_adapter_uses_stream_audit_without_a_paid_call(self):
        fake_source = """#!/usr/bin/env python3
import json
import os
import pathlib
import sys
if '--version' in sys.argv:
    print('fake-claude-code 1.0')
    raise SystemExit(0)
if os.environ.get('ANTHROPIC_BASE_URL') != 'https://api.teamorouter.com':
    raise SystemExit('unexpected provider URL')
if os.environ.get('ANTHROPIC_AUTH_TOKEN') != 'test-teamorouter-token':
    raise SystemExit('missing isolated provider token')
if pathlib.Path(os.environ.get('CLAUDE_CONFIG_DIR', '')).resolve() == (pathlib.Path.home() / '.claude').resolve():
    raise SystemExit('user Claude configuration was not isolated')
args = sys.argv[1:]
session_flag = '--resume' if '--resume' in args else '--session-id'
session_id = args[args.index(session_flag) + 1]
model = args[args.index('--model') + 1]
pathlib.Path('candidate.st').write_text('GOOD', encoding='utf-8')
events = [
    {'type': 'system', 'subtype': 'init', 'model': model},
    {'type': 'assistant', 'message': {
        'model': model,
        'usage': {'input_tokens': 2, 'output_tokens': 1},
        'content': [{'type': 'tool_use', 'name': 'Write', 'input': {'file_path': 'candidate.st'}}],
    }},
    {'type': 'result', 'subtype': 'success', 'session_id': session_id,
     'num_turns': 1, 'total_cost_usd': 0.0, 'result': 'ready'},
]
for event in events:
    print(json.dumps(event))
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "fake_claude"
            executable.write_text(fake_source, encoding="utf-8")
            executable.chmod(0o755)
            workspace = root / "workspace"
            workspace.mkdir()
            for name in ("requirement.md", "interface.st", "candidate.st"):
                (workspace / name).write_text("public", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"TEAMOROUTER_API_KEY": "test-teamorouter-token"},
                clear=False,
            ):
                cli = ClaudeCodeCLI(
                    {
                        "executable": str(executable),
                        "model_selector": "claude-sonnet-5",
                        "expected_resolved_model_regex": r"^claude-sonnet-5$",
                        "timeout_seconds": 5,
                        "max_turns_per_candidate": 2,
                        "effort": "high",
                        "safe_mode": True,
                        "tools": ["Read", "Write", "Edit"],
                    },
                    {
                        "name": "teamorouter",
                        "base_url": "https://api.teamorouter.com",
                        "api_key_env": "TEAMOROUTER_API_KEY",
                    },
                )
                self.assertEqual(cli.preflight(), "fake-claude-code 1.0")
                result = cli.invoke(
                    workspace,
                    "write the candidate",
                    root / "call",
                    "00000000-0000-4000-8000-000000000001",
                )
            self.assertEqual(result.resolved_models, ("claude-sonnet-5",))
            self.assertTrue(result.access_audit_valid)
            self.assertEqual((workspace / "candidate.st").read_text(encoding="utf-8"), "GOOD")
            request = json.loads((root / "call/request.json").read_text(encoding="utf-8"))
            self.assertFalse(request["resume"])
            self.assertTrue(request["no_session_persistence"])
            self.assertTrue(request["safe_mode"])
            self.assertTrue(request["strict_mcp_config"])
            self.assertTrue(request["fresh_claude_config_dir"])
            self.assertFalse(request["user_settings_loaded"])
            self.assertEqual(request["provider"], "teamorouter")
            self.assertEqual(request["base_url"], "https://api.teamorouter.com")
            self.assertTrue(any("mcp__*" in option for option in request["command_options"]))


if __name__ == "__main__":
    unittest.main()
