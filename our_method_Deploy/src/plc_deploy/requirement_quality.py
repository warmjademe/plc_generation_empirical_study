from __future__ import annotations

import re
import unicodedata
import zlib
from typing import Any


TYPE_PATTERN = re.compile(r"\b(?:BOOL|INT|REAL)\b", re.IGNORECASE)
NUMERIC_TYPE_PATTERN = re.compile(r"\b(?:INT|REAL)\b", re.IGNORECASE)
INPUT_PATTERN = re.compile(r"(?:输入(?:变量|信号)?|\binputs?\b)", re.IGNORECASE)
OUTPUT_PATTERN = re.compile(r"(?:输出(?:变量|信号)?|\boutputs?\b)", re.IGNORECASE)
BEHAVIOR_PATTERN = re.compile(
    r"(?:当|如果|若|则|时|启动|停止|打开|关闭|置位|清除|计数|定时|"
    r"\bwhen\b|\bif\b|\bthen\b|\bstart\b|\bstop\b|\bopen\b|\bclose\b|"
    r"=>|:=|=\s*(?:TRUE|FALSE|[-+]?\d+(?:\.\d+)?))",
    re.IGNORECASE,
)
INITIAL_PATTERN = re.compile(
    r"(?:初始|首次运行|上电|启动时|默认值|安全默认|\binitial(?:ly)?\b|\bstartup\b|\bpower[- ]?up\b)",
    re.IGNORECASE,
)
PRIORITY_PATTERN = re.compile(
    r"(?:优先|同时|互锁|不得同时|冲突|无冲突|无需优先|"
    r"\bpriority\b|\bsimultaneous\b|\binterlock\b|\bmutual(?:ly)? exclusive\b|"
    r"\bno conflict\b|\bnot applicable\b|\bN/?A\b)",
    re.IGNORECASE,
)
STATEFUL_PATTERN = re.compile(
    r"(?:保持|锁存|直到|持续|累计|计数|定时|延时|脉冲|边沿|"
    r"\blatch(?:ed)?\b|\bretain(?:ed)?\b|\bremain\b|\buntil\b|"
    r"\bcount(?:er)?\b|\btimer?\b|\bdelay\b|\bedge\b|\bpulse\b)",
    re.IGNORECASE,
)
NUMERIC_STATE_TRANSITION_PATTERN = re.compile(
    r"(?:累计|计数|增加|递增|减少|递减|累加|累减|保持|锁存|边沿|脉冲|"
    r"\bcount(?:er)?\b|\bincrement\b|\bdecrement\b|\baccumulat(?:e|or)\b|"
    r"\bretain(?:ed)?\b|\blatch(?:ed)?\b|\bedge\b|\bpulse\b)",
    re.IGNORECASE,
)
RELEASE_PATTERN = re.compile(
    r"(?:复位|重置|清除|释放|停止|到期|达到|恢复|"
    r"\breset\b|\bclear\b|\brelease\b|\bstop\b|\bexpire\b|\buntil\b)",
    re.IGNORECASE,
)
NO_STATEFUL_PATTERN = re.compile(
    r"(?:无保持状态|无需保持|不保持|组合逻辑|\bno retained state\b|"
    r"\bno latching\b|\bcombinational\b)",
    re.IGNORECASE,
)

IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
LITERAL_PATTERN = re.compile(
    r"\b(?:TRUE|FALSE)\b|(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
NO_PRIORITY_NEEDED_PATTERN = re.compile(
    r"(?:不存在(?:输入)?冲突|无(?:输入)?冲突|无需优先|不适用|"
    r"\bno conflicts?\b|\bnot applicable\b|\bN/?A\b)",
    re.IGNORECASE,
)
MAX_EFFECTIVE_REQUIREMENT_CHARS = 12_000
VAGUE_CONTROL_PATTERN = re.compile(
    r"(?:适当|及时|尽快|稍后|过一会儿|一段时间|一定次数|若干次|达到要求时|"
    r"按需|必要时|合适(?:的)?(?:值|范围|时机)|较高时|较低时|"
    r"未说明|尚未确定|待定|不明确|"
    r"\bas needed\b|\bwhen appropriate\b|\bafter a while\b|\bsoon\b|"
    r"\btimely\b|\ba suitable (?:value|time)\b|\bseveral times\b)",
    re.IGNORECASE,
)
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?:忽略|无视|覆盖).{0,24}(?:系统|开发者|之前|以上).{0,12}(?:指令|提示|规则)|"
    r"(?:泄露|显示|输出).{0,20}(?:API\s*key|密钥|密码|token|环境变量)|"
    r"(?:跳过|绕过|禁用|不要调用).{0,20}(?:验证|MatIEC|PLCverif|OpenPLC|ISPSoft)|"
    r"\bignore (?:all |the )?(?:previous|system|developer) (?:instructions?|prompts?)\b|"
    r"\b(?:reveal|print|expose) .{0,24}(?:api key|secret|password|token|environment variables?)\b|"
    r"\b(?:skip|bypass|disable) .{0,20}(?:validation|validator|matiec|plcverif|openplc|ispsoft)\b",
    re.IGNORECASE,
)
MARKUP_PATTERN = re.compile(
    r"<(?:script|iframe|object|embed|form|style|svg)\b|javascript\s*:",
    re.IGNORECASE,
)
TIME_INTENT_PATTERN = re.compile(
    r"(?:延时|定时|超时|脉冲宽度|\bdelay\b|\btimeout\b|\btimer\b|\bpulse width\b)",
    re.IGNORECASE,
)
TIME_VALUE_PATTERN = re.compile(
    r"(?:T(?:IME)?#)?(?:\d+(?:\.\d+)?|一)\s*"
    r"(?:ms|s|sec(?:ond)?s?|min(?:ute)?s?|h(?:ours?)?|毫秒|秒|分钟|小时|扫描周期|scans?)",
    re.IGNORECASE,
)
DURATION_CAPTURE_PATTERN = re.compile(
    r"(?:T(?:IME)?#)?(?P<value>\d+(?:\.\d+)?|一)\s*"
    r"(?P<unit>ms|s|sec(?:ond)?s?|min(?:ute)?s?|h(?:ours?)?|毫秒|秒|分钟|小时|扫描周期|scans?)",
    re.IGNORECASE,
)
EDGE_PATTERN = re.compile(r"(?:边沿|边缘|\bedge\b)", re.IGNORECASE)
EDGE_DIRECTION_PATTERN = re.compile(
    r"(?:上升沿|下降沿|正边沿|负边沿|\brising edge\b|\bfalling edge\b|\bpositive edge\b|\bnegative edge\b)",
    re.IGNORECASE,
)
RETAIN_PATTERN = re.compile(
    r"(?:保持|锁存|置位并保持|\blatch(?:ed)?\b|\bretain(?:ed)?\b|\bremain\b)",
    re.IGNORECASE,
)
NEXT_SCAN_CLEAR_PATTERN = re.compile(
    r"(?:下一|下一个|次一)(?:个)?扫描周期.{0,36}(?:FALSE|关闭|清零|复位)|"
    r"(?:FALSE|关闭|清零|复位).{0,36}(?:下一|下一个|次一)(?:个)?扫描周期|"
    r"\bnext scan\b.{0,36}(?:FALSE|off|clear|reset)",
    re.IGNORECASE,
)
RESERVED_INTERFACE_WORDS = {
    "input", "inputs", "output", "outputs", "variable", "variables",
    "signal", "signals", "type", "bool", "int", "real", "are", "is",
    "of", "and", "or", "not", "true", "false", "when", "if", "then",
    "initial", "initially", "logic", "control", "priority", "otherwise",
    "name", "description", "default", "value",
}


def _interface_section(
    text: str, marker: re.Pattern[str], boundary: re.Pattern[str]
) -> str:
    for match in marker.finditer(text):
        start = match.end()
        next_boundary = boundary.search(text, start)
        end = min(len(text), start + 500)
        if next_boundary is not None:
            end = min(end, next_boundary.start())
        section = text[start:end]
        if TYPE_PATTERN.search(section):
            return section
    return ""


def _declared_names(section: str) -> set[str]:
    """Extract IEC identifiers immediately associated with declared types.

    The accepted UI syntax is intentionally flexible (``Start : BOOL``,
    ``Start、Stop 均为 BOOL`` and ``Start and Stop are BOOL``), but a bare type
    word is not treated as an interface declaration.
    """

    names: set[str] = set()
    previous_type_end = 0
    for match in TYPE_PATTERN.finditer(section):
        clause_start = previous_type_end
        # Colon is deliberately not a boundary because ``Motor : BOOL`` and
        # the common Chinese ``Motor：BOOL`` notation place it immediately
        # between the identifier and its type.
        separators = [section.rfind(token, previous_type_end, match.start()) for token in ("；", ";", "。", ".")]
        clause_start = max([clause_start, *(position + 1 for position in separators)])
        clause = section[clause_start:match.start()]
        for token in IDENTIFIER_PATTERN.findall(clause):
            if token.casefold() not in RESERVED_INTERFACE_WORDS:
                names.add(token)
        previous_type_end = match.end()
    return names


def _declared_types(section: str) -> dict[str, set[str]]:
    declarations: dict[str, set[str]] = {}
    previous_type_end = 0
    for match in TYPE_PATTERN.finditer(section):
        separators = [
            section.rfind(token, previous_type_end, match.start())
            for token in ("；", ";", "。", ".")
        ]
        clause_start = max([previous_type_end, *(position + 1 for position in separators)])
        clause = section[clause_start:match.start()]
        for token in IDENTIFIER_PATTERN.findall(clause):
            if token.casefold() in RESERVED_INTERFACE_WORDS:
                continue
            declarations.setdefault(token.casefold(), set()).add(match.group(0).upper())
        previous_type_end = match.end()
    return declarations


def _clauses(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。.;；\n]+", text) if item.strip()]


def _retained_numeric_outputs(
    text: str, output_names: set[str], output_types: dict[str, set[str]]
) -> set[str]:
    """Return numeric outputs whose requested value depends on a prior scan.

    The frozen contract schema currently has deterministic transition semantics
    only for retained BOOL outputs.  Reject retained INT/REAL outputs before an
    API call instead of spending the ten-attempt contract budget on an oracle
    that the schema cannot represent faithfully.
    """

    numeric = {
        name
        for name in output_names
        if output_types.get(name.casefold(), set()) & {"INT", "REAL"}
    }
    retained: set[str] = set()
    for clause in _clauses(text):
        if NO_STATEFUL_PATTERN.search(clause):
            continue
        if not NUMERIC_STATE_TRANSITION_PATTERN.search(clause):
            continue
        retained.update(
            name
            for name in numeric
            if re.search(_identifier_ref(name), clause, re.IGNORECASE)
        )
    return retained


def _identifier_ref(name: str) -> str:
    # Python's ``\b`` treats Chinese characters as word characters, so
    # ``Stage1Run并...`` has no Unicode word boundary after the IEC name.
    return rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"


def _assignment_values(text: str, name: str) -> set[str]:
    return {
        match.group(1).upper()
        for match in re.finditer(
            rf"{_identifier_ref(name)}\s*(?::=|=|均为|为|becomes?|is)\s*"
            rf"(TRUE|FALSE|[-+]?\d+(?:\.\d+)?)\b",
            text,
            re.IGNORECASE,
        )
    }


def _initial_state_audit(
    text: str, output_names: set[str]
) -> tuple[set[str], list[str]]:
    values = {name: set() for name in output_names}
    for clause in _clauses(text):
        if not INITIAL_PATTERN.search(clause):
            continue
        aggregate = re.search(
            r"(?:(?:所有|全部|各|[一二三四五六七八九十\d]+个)(?:的)?)?输出(?:均|全部)?"
            r"\s*(?:=|为)\s*(TRUE|FALSE|[-+]?\d+(?:\.\d+)?)\b",
            clause,
            re.IGNORECASE,
        )
        if aggregate:
            for name in output_names:
                values[name].add(aggregate.group(1).upper())
        for name in output_names:
            values[name].update(_assignment_values(clause, name))
    missing = {name for name, assigned in values.items() if not assigned}
    conflicts = [
        f"{name} 的初始值同时被定义为 {', '.join(sorted(assigned))}"
        for name, assigned in values.items()
        if len(assigned) > 1
    ]
    return missing, conflicts


def _normalized_condition(clause: str) -> tuple[str, str] | None:
    boundary = re.search(r"(?:时|则|\bthen\b)", clause, re.IGNORECASE)
    if boundary is None:
        return None
    condition = clause[:boundary.start()]
    condition = re.sub(r"^(?:当|若|如果|when|if)\s*", "", condition, flags=re.IGNORECASE)
    condition = re.sub(r"(?:并且|而且|且|\band\b)", "&", condition, flags=re.IGNORECASE)
    condition = re.sub(r"(?:或者|或|\bor\b)", "|", condition, flags=re.IGNORECASE)
    condition = re.sub(r"\s+", "", condition).casefold()
    return condition, clause[boundary.end():]


def _priority_cycles(text: str, interface_names: set[str]) -> list[str]:
    canonical = {name.casefold(): name for name in interface_names}
    edges: set[tuple[str, str]] = set()
    for match in re.finditer(
        r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])"
        r"\s*(?:具有)?(?:最高)?\s*(?:优先于|has priority over)\s*"
        r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])",
        text,
        re.IGNORECASE,
    ):
        higher, lower = match.group(1).casefold(), match.group(2).casefold()
        if higher in canonical and lower in canonical and higher != lower:
            edges.add((higher, lower))
    for match in re.finditer(
        r"(?:优先级|priority order)\s*(?:从高到低)?\s*(?:为|是|[:：])([^。；;\n]+)",
        text,
        re.IGNORECASE,
    ):
        order = [
            token.casefold()
            for token in IDENTIFIER_PATTERN.findall(match.group(1))
            if token.casefold() in canonical
        ]
        edges.update(zip(order, order[1:]))

    graph: dict[str, set[str]] = {name: set() for name in canonical}
    for higher, lower in edges:
        graph[higher].add(lower)
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = path.index(node)
            return path[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        path.append(node)
        for target in graph[node]:
            cycle = visit(target)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in graph:
        cycle = visit(node)
        if cycle:
            return ["优先级形成环：" + " > ".join(canonical[item] for item in cycle)]
    return []


def _unknown_references(text: str, declared_names: set[str]) -> set[str]:
    candidates = {
        match.group(1)
        for match in re.finditer(
            r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])"
            r"\s*(?::=|=|<>|<=|>=|<|>)",
            text,
        )
    }
    declared = {name.casefold() for name in declared_names}
    return {
        name for name in candidates
        if name.casefold() not in declared
        and name.casefold() not in RESERVED_INTERFACE_WORDS
    }


def _stateful_outputs_missing_release(text: str, output_names: set[str]) -> set[str]:
    clauses = _clauses(text)
    missing: set[str] = set()
    for output in output_names:
        related = [
            clause for clause in clauses
            if re.search(_identifier_ref(output), clause, re.IGNORECASE)
        ]
        if not any(STATEFUL_PATTERN.search(clause) for clause in related):
            continue
        released = False
        for clause in related:
            if INITIAL_PATTERN.search(clause):
                continue
            assigned = _assignment_values(clause, output)
            if RELEASE_PATTERN.search(clause) or ({"FALSE", "0"} & assigned):
                released = True
                break
        if not released:
            missing.add(output)
    return missing


def _normalized_duration(match: re.Match[str]) -> tuple[str, float]:
    raw_value = match.group("value")
    value = 1.0 if raw_value == "一" else float(raw_value)
    unit = match.group("unit").casefold()
    if unit in {"ms", "毫秒"}:
        return "seconds", value / 1_000
    if unit in {"s", "sec", "second", "seconds", "秒"}:
        return "seconds", value
    if unit in {"min", "minute", "minutes", "分钟"}:
        return "seconds", value * 60
    if unit in {"h", "hour", "hours", "小时"}:
        return "seconds", value * 3_600
    return "scans", value


def _timing_conflicts(text: str, output_names: set[str]) -> list[str]:
    observations: dict[tuple[str, str, str], set[tuple[str, float]]] = {}
    for clause in _clauses(text):
        marker = TIME_INTENT_PATTERN.search(clause)
        durations = {
            _normalized_duration(match)
            for match in DURATION_CAPTURE_PATTERN.finditer(clause)
        }
        if marker is None or not durations:
            continue
        trigger = re.sub(r"^(?:当|若|如果|when|if)\s*", "", clause[:marker.start()], flags=re.IGNORECASE)
        trigger = re.sub(r"(?:之后|以后|后)\s*$", "", trigger)
        trigger = re.sub(r"\s+", "", trigger).casefold()
        for output in sorted(output_names, key=str.casefold):
            for value in _assignment_values(clause, output):
                observations.setdefault((trigger, output, value), set()).update(durations)
    return [
        f"相同触发条件对 {output}={value} 给出了不同的时间参数"
        for (_trigger, output, value), durations in observations.items()
        if len(durations) > 1
    ]


def _excessive_repetition(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 1_000:
        return False
    compressed_ratio = len(zlib.compress(compact.encode("utf-8"))) / max(
        1, len(compact.encode("utf-8"))
    )
    return compressed_ratio < 0.06


def _text_safety_issues(text: str) -> list[str]:
    issues: list[str] = []
    if len(text) > MAX_EFFECTIVE_REQUIREMENT_CHARS:
        issues.append(f"正文超过 {MAX_EFFECTIVE_REQUIREMENT_CHARS} 个字符")
    if any(
        unicodedata.category(character) in {"Cc", "Cf"} and character not in "\n\r\t"
        for character in text
    ):
        issues.append("正文包含不可见或不受支持的控制字符")
    if _excessive_repetition(text):
        issues.append("正文包含大段重复内容")
    if MARKUP_PATTERN.search(text):
        issues.append("正文包含脚本或可执行标记")
    if PROMPT_INJECTION_PATTERN.search(text):
        issues.append("正文包含要求覆盖系统规则、泄露凭据或绕过验证的指令")
    return issues


def _name_occurrences(text: str, name: str) -> int:
    return len(re.findall(_identifier_ref(name), text, re.IGNORECASE))


def _has_deterministic_initial_state(text: str, output_names: set[str]) -> bool:
    for match in INITIAL_PATTERN.finditer(text):
        window = text[match.start():match.start() + 320]
        identifies_outputs = any(
            re.search(_identifier_ref(name), window, re.IGNORECASE)
            for name in output_names
        ) or bool(re.search(r"(?:所有|全部|各)(?:的)?输出|\ball outputs?\b", window, re.IGNORECASE))
        if identifies_outputs and LITERAL_PATTERN.search(window):
            return True
    return False


def _has_deterministic_priority(text: str, input_names: set[str], output_names: set[str]) -> bool:
    if NO_PRIORITY_NEEDED_PATTERN.search(text):
        return True
    names = input_names | output_names
    # Accept an explicit named order such as ``Stop 优先于 Start`` or
    # ``EmergencyStop has priority over Start``.
    clauses = re.split(r"[。.;；\n]+", text)
    for clause in clauses:
        for name in names:
            named_priority = re.compile(
                rf"{_identifier_ref(name)}.{{0,32}}(?:优先|priority)", re.IGNORECASE
            )
            if named_priority.search(clause):
                return True
    # A complete order may be written once as ``优先级为 Reset、Stop、Start``.
    for match in re.finditer(r"(?:优先级|priority order)\s*(?:为|是|从高到低|[:：])", text, re.IGNORECASE):
        window = text[match.start():match.end() + 180]
        if sum(
            bool(re.search(_identifier_ref(name), window, re.IGNORECASE))
            for name in names
        ) >= 2:
            return True
    # Deterministic simultaneous/interlock rules are also sufficient when the
    # clause names at least two interface variables and fixes an output value.
    for clause in clauses:
        if not re.search(r"(?:同时|冲突|互锁|simultaneous|interlock)", clause, re.IGNORECASE):
            continue
        mentioned = sum(
            bool(re.search(_identifier_ref(name), clause, re.IGNORECASE))
            for name in names
        )
        if mentioned >= 2 and LITERAL_PATTERN.search(clause):
            return True
    return False


def _has_grounded_behavior(
    text: str, input_names: set[str], output_names: set[str]
) -> bool:
    """Require every output to occur in an executable, interface-grounded rule."""

    interface_names = input_names | output_names
    clauses = [item.strip() for item in re.split(r"[。.;；\n]+", text) if item.strip()]
    for output in output_names:
        grounded = False
        for clause in clauses:
            if not re.search(_identifier_ref(output), clause, re.IGNORECASE):
                continue
            if not BEHAVIOR_PATTERN.search(clause):
                continue
            if INITIAL_PATTERN.search(clause):
                continue
            peers = interface_names - {output}
            if any(
                re.search(_identifier_ref(name), clause, re.IGNORECASE)
                for name in peers
            ):
                grounded = True
                break
        if not grounded:
            return False
    return bool(output_names)


def _explicit_contradictions(
    text: str, output_names: set[str], interface_names: set[str]
) -> list[str]:
    """Find direct contradictions that should be clarified before any API call."""

    conflicts: list[str] = []
    observations: dict[tuple[str, str], str] = {}
    coarse_clauses = [item.strip() for item in re.split(r"[。.;；\n]+", text) if item.strip()]
    clauses: list[str] = []
    for coarse in coarse_clauses:
        clauses.extend(
            item.strip()
            for item in re.split(
                r"[,，]\s*(?=(?:当|若|如果|否则|\bwhen\b|\bif\b|\botherwise\b|"
                r"[A-Za-z_][A-Za-z0-9_]*\s*(?:=|<>|<=|>=|<|>)))",
                coarse,
                flags=re.IGNORECASE,
            )
            if item.strip()
        )
    for clause in clauses:
        normalized = _normalized_condition(clause)
        for output in output_names:
            consequent = normalized[1] if normalized is not None else clause
            values = _assignment_values(consequent, output)
            if len(values) > 1:
                conflicts.append(
                    f"同一规则同时要求 {output} 取不同值：{', '.join(sorted(values))}"
                )
                continue
            if not values or normalized is None:
                continue
            condition = normalized[0]
            key = (condition, output.casefold())
            value = next(iter(values))
            prior = observations.get(key)
            if prior is not None and prior != value:
                conflicts.append(f"相同条件对 {output} 给出了相反结果")
            observations[key] = value

    _, initial_conflicts = _initial_state_audit(text, output_names)
    conflicts.extend(initial_conflicts)
    conflicts.extend(_priority_cycles(text, interface_names))
    conflicts.extend(_timing_conflicts(text, output_names))

    for output in output_names:
        absolute_values: set[str] = set()
        for clause in _clauses(text):
            output_match = re.search(_identifier_ref(output), clause, re.IGNORECASE)
            if output_match is None or re.search(r"(?:时|\bwhen\b)", clause[:output_match.start()], re.IGNORECASE):
                continue
            match = re.search(
                rf"{_identifier_ref(output)}.{{0,24}}(?:始终|永远|\balways\b).{{0,12}}"
                rf"(?:=|为|保持|is)?\s*(TRUE|FALSE|[-+]?\d+(?:\.\d+)?)\b",
                clause,
                re.IGNORECASE,
            )
            if match:
                absolute_values.add(match.group(1).upper())
        assigned_values = _assignment_values(text, output)
        if absolute_values and any(value not in absolute_values for value in assigned_values):
            conflicts.append(f"{output} 的恒定值要求与其他行为赋值冲突")

        related = [
            clause for clause in _clauses(text)
            if re.search(_identifier_ref(output), clause, re.IGNORECASE)
        ]
        if any(RETAIN_PATTERN.search(clause) for clause in related) and any(
            NEXT_SCAN_CLEAR_PATTERN.search(clause) for clause in related
        ):
            conflicts.append(f"{output} 同时被要求保持并在下一扫描周期自动清除")

    # Stable order keeps API diagnostics and tests deterministic.
    return list(dict.fromkeys(conflicts))


def assess_requirement(requirement: str) -> dict[str, Any]:
    text = re.sub(r"[ \t]+", " ", requirement.strip())
    checks: list[dict[str, Any]] = []
    input_section = _interface_section(text, INPUT_PATTERN, OUTPUT_PATTERN)
    output_section = _interface_section(text, OUTPUT_PATTERN, INPUT_PATTERN)
    input_names = _declared_names(input_section)
    output_names = _declared_names(output_section)
    input_names_folded = {name.casefold() for name in input_names}
    output_names_folded = {name.casefold() for name in output_names}
    interface_names = input_names | output_names
    input_types = _declared_types(input_section)
    output_types = _declared_types(output_section)

    def add(
        check_id: str,
        label: str,
        passed: bool,
        detail: str,
        evidence: list[str] | None = None,
    ) -> None:
        checks.append({
            "id": check_id,
            "label": label,
            "passed": passed,
            "required": True,
            "detail": detail,
            "severity": "blocking" if not passed else "none",
            "evidence": list(evidence or []),
        })

    safety_issues = _text_safety_issues(text)
    add(
        "input_safety",
        "文本与资源安全",
        not safety_issues,
        (
            "；".join(safety_issues[:3])
            if safety_issues
            else "请只描述控制需求，不要加入脚本、提示注入、验证绕过指令或大量重复内容。"
        ),
        safety_issues[:3],
    )

    add(
        "inputs",
        "输入接口",
        bool(input_names),
        "请使用 IEC 变量名列出至少一个输入，并给出 BOOL、INT 或 REAL 类型，例如 Start : BOOL。",
    )
    add(
        "outputs",
        "输出接口",
        bool(output_names),
        "请使用 IEC 变量名列出至少一个输出，并给出 BOOL、INT 或 REAL 类型，例如 Motor : BOOL。",
    )
    add(
        "interface_consistency",
        "接口一致性",
        bool(
            input_names
            and output_names
            and input_names_folded.isdisjoint(output_names_folded)
        ),
        "同一变量不能同时声明为输入和输出；请分别命名输入信号与输出信号。",
    )
    type_conflicts = [
        name for name, types in {**input_types, **output_types}.items()
        if len(types) > 1
    ]
    add(
        "interface_types",
        "接口类型一致性",
        not type_conflicts,
        (
            "以下变量被声明为多个类型：" + "、".join(sorted(type_conflicts))
            if type_conflicts
            else "同一接口变量只能声明一种 IEC 类型。"
        ),
        sorted(type_conflicts),
    )
    retained_numeric_outputs = _retained_numeric_outputs(
        text, output_names, output_types
    )
    add(
        "supported_state_model",
        "跨扫描数值状态支持",
        not retained_numeric_outputs,
        (
            "当前确定性验证契约只能描述 BOOL 跨扫描状态；以下 INT/REAL 输出需要计数、累加或保持："
            + "、".join(sorted(retained_numeric_outputs))
            + "。请改为不保持的数值组合逻辑，或等待数值状态 Oracle 支持。"
            if retained_numeric_outputs
            else "当前接口未要求验证器尚不能可靠表达的 INT/REAL 跨扫描状态。"
        ),
        sorted(retained_numeric_outputs),
    )
    unknown_references = _unknown_references(text, interface_names)
    add(
        "declared_references",
        "规则变量已声明",
        not unknown_references,
        (
            "规则引用了未声明变量：" + "、".join(sorted(unknown_references))
            if unknown_references
            else "控制条件和赋值中使用的变量必须先在输入或输出接口中声明。"
        ),
        sorted(unknown_references),
    )
    contradictions = _explicit_contradictions(text, output_names, interface_names)
    add(
        "requirement_consistency",
        "需求一致性",
        not contradictions,
        (
            "；".join(contradictions[:3])
            if contradictions
            else "请消除同一条件下的相反输出要求或相互冲突的优先级。"
        ),
        contradictions[:3],
    )
    vague_terms = list(dict.fromkeys(match.group(0) for match in VAGUE_CONTROL_PATTERN.finditer(text)))
    add(
        "quantified_behavior",
        "条件与边界可量化",
        not vague_terms,
        (
            "以下表述无法形成确定测试：" + "、".join(vague_terms[:5])
            if vague_terms
            else "请把时间、阈值、次数和触发条件写成可判定的值。"
        ),
        vague_terms[:5],
    )
    behavior_is_grounded = bool(
        input_names
        and output_names
        and any(_name_occurrences(text, name) >= 2 for name in input_names)
        and _has_grounded_behavior(text, input_names, output_names)
    )
    add(
        "behavior",
        "控制逻辑",
        behavior_is_grounded,
        "请逐项说明输入条件与每个输出的确定变化关系，不能只写“系统自动控制”或“按需要运行”。",
    )
    missing_initial_outputs, _ = _initial_state_audit(text, output_names)
    add(
        "initial_state",
        "初始状态",
        bool(output_names)
        and _has_deterministic_initial_state(text, output_names)
        and not missing_initial_outputs,
        (
            "以下输出缺少明确初值：" + "、".join(sorted(missing_initial_outputs))
            if missing_initial_outputs
            else "请给出上电或首次运行时每个输出的明确值；仅写“安全初始状态”不够。"
        ),
        sorted(missing_initial_outputs),
    )
    add(
        "priority",
        "冲突与优先级",
        bool(input_names or output_names)
        and _has_deterministic_priority(text, input_names, output_names),
        "请用变量名说明同时输入时的确定优先级；若确实不存在冲突，请明确写“无输入冲突”。",
    )
    stateful_outputs_without_release = (
        set()
        if NO_STATEFUL_PATTERN.search(text)
        else _stateful_outputs_missing_release(text, output_names)
    )
    add(
        "state_release",
        "保持状态的退出条件",
        not stateful_outputs_without_release,
        (
            "以下状态输出缺少退出条件：" + "、".join(sorted(stateful_outputs_without_release))
            if stateful_outputs_without_release
            else "保持、锁存、定时、计数或边沿状态必须逐项给出复位、清除、停止或到期条件。"
        ),
        sorted(stateful_outputs_without_release),
    )
    timing_incomplete = bool(TIME_INTENT_PATTERN.search(text)) and not bool(
        TIME_VALUE_PATTERN.search(text)
    )
    add(
        "timing_semantics",
        "时间参数",
        not timing_incomplete,
        "需求包含延时、定时、超时或脉冲宽度，请给出数值和单位，例如 500 ms 或 5 秒。",
    )
    edge_incomplete = bool(EDGE_PATTERN.search(text)) and not bool(
        EDGE_DIRECTION_PATTERN.search(text)
    )
    add(
        "edge_semantics",
        "边沿方向",
        not edge_incomplete,
        "需求包含边沿触发，请明确是上升沿还是下降沿。",
    )

    missing = [item for item in checks if not item["passed"]]
    return {
        "ready": not missing,
        "character_count": len(text),
        "checks": checks,
        "missing": [
            {
                "id": item["id"],
                "label": item["label"],
                "message": item["detail"],
                "severity": item["severity"],
                "evidence": item["evidence"],
            }
            for item in missing
        ],
        "message": (
            "需求信息完整，可以进入验证契约生成。"
            if not missing
            else "控制需求信息不足；请先补充缺失内容，系统尚未调用大语言模型。"
        ),
    }


def requirement_uses_numeric_types(requirement: str) -> bool:
    return bool(NUMERIC_TYPE_PATTERN.search(requirement))
