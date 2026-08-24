"""Translate IEC ST POUs into ISPSoft source-unit packages.

ISPSoft imports a function block from ``.FBU`` and a program from ``.MPU``.
Both files contain a small Delta header followed by a traditional ZipCrypto
archive whose only member is ``Unzipped.src``.  The package password is an
installation detail and is deliberately supplied by the caller; it is never
stored in the repository or in a generated manifest.
"""

from __future__ import annotations

import binascii
import datetime as dt
import hashlib
import re
import struct
import zlib
from dataclasses import dataclass


class SourceUnitError(ValueError):
    """The candidate cannot be represented as an ISPSoft ST source unit."""


@dataclass(frozen=True)
class Declaration:
    name: str
    type_text: str
    scope: str
    initializer: str | None = None


@dataclass(frozen=True)
class FunctionBlock:
    name: str
    declarations: tuple[Declaration, ...]
    body: str


_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_BLOCK_RE = re.compile(
    rf"(?is)^\s*FUNCTION_BLOCK\s+({_IDENTIFIER})\s*(.*?)\s*END_FUNCTION_BLOCK\s*$"
)
_VAR_RE = re.compile(
    r"(?ims)^\s*(VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT|VAR_TEMP|VAR)\b[^\r\n]*\r?\n(.*?)^\s*END_VAR\s*;?\s*$"
)
_DELTA_DEVICE_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])(?:M|X|Y|D|T|C|S)\d+(?![A-Za-z0-9_])")
_LOCATED_ADDRESS_RE = re.compile(r"(?i)%[IQM][XWDLB]?\d+(?:\.\d+)?")
_HARNESS_IDENTIFIER_RE = re.compile(r"(?i)\bEGBS_[A-Za-z0-9_]*\b")
# ISPSoft 3.24 reports error 200 ("symbol type does not exist") when IEC TON or
# TIME locals are declared for the DVP48ES300R/DVP-ES3 target.  Keep this list
# evidence-based: add another type only after an ISPSoft calibration proves it.
_UNSUPPORTED_DVP_ES3_TYPES = {"TIME", "TON"}


def _strip_comments(text: str) -> str:
    return re.sub(r"(?s)\(\*.*?\*\)", " ", text)


def _parse_declaration_statement(statement: str, scope: str) -> list[Declaration]:
    clean = _strip_comments(statement).strip()
    if not clean:
        return []
    match = re.match(
        rf"(?is)^({_IDENTIFIER}(?:\s*,\s*{_IDENTIFIER})*)\s*:\s*(.+)$",
        clean,
    )
    if not match:
        raise SourceUnitError(f"unsupported {scope} declaration: {clean[:160]}")
    names = [item.strip() for item in match.group(1).split(",")]
    rhs = match.group(2).strip()
    if ":=" in rhs:
        type_text, initializer = rhs.split(":=", 1)
        initializer = initializer.strip()
        if not initializer:
            raise SourceUnitError(f"empty initializer in declaration: {clean[:160]}")
    else:
        type_text, initializer = rhs, None
    type_text = " ".join(type_text.strip().split())
    if not type_text:
        raise SourceUnitError(f"empty type in declaration: {clean[:160]}")
    return [Declaration(name, type_text, scope, initializer) for name in names]


def _parse_declarations(block_text: str, scope: str) -> list[Declaration]:
    # Semicolons inside IEC comments have already been removed.  The supported
    # benchmark fragment has scalar declarations and scalar initializers, so a
    # semicolon is an unambiguous declaration terminator.
    clean = _strip_comments(block_text)
    statements = clean.split(";")
    trailing = statements.pop().strip()
    if trailing:
        raise SourceUnitError(f"unterminated {scope} declaration: {trailing[:160]}")
    declarations: list[Declaration] = []
    for statement in statements:
        declarations.extend(_parse_declaration_statement(statement, scope))
    return declarations


def parse_function_block(source: str) -> FunctionBlock:
    """Parse the single-function-block fragment used by Balanced-100."""
    source = source.replace("\ufeff", "", 1)
    portable_source = _strip_comments(source)
    if _LOCATED_ADDRESS_RE.search(portable_source):
        raise SourceUnitError("located I/O addresses are forbidden in the isolated candidate")
    harness_name = _HARNESS_IDENTIFIER_RE.search(portable_source)
    if harness_name is not None:
        raise SourceUnitError(
            f"reserved harness identifier {harness_name.group(0)} is forbidden"
        )
    match = _BLOCK_RE.match(source)
    if not match:
        raise SourceUnitError("expected exactly one complete FUNCTION_BLOCK")
    name, content = match.group(1), match.group(2)
    declarations: list[Declaration] = []
    spans: list[tuple[int, int]] = []
    for item in _VAR_RE.finditer(content):
        scope = item.group(1).upper()
        declarations.extend(_parse_declarations(item.group(2), scope))
        spans.append(item.span())
    body_parts: list[str] = []
    cursor = 0
    for start, end in spans:
        body_parts.append(content[cursor:start])
        cursor = end
    body_parts.append(content[cursor:])
    body = "".join(body_parts).strip()
    if re.search(r"(?im)^\s*(?:FUNCTION_BLOCK|END_FUNCTION_BLOCK)\b", body):
        raise SourceUnitError("expected exactly one FUNCTION_BLOCK")
    if re.search(r"(?im)^\s*VAR(?:_|\b)", body):
        raise SourceUnitError("unsupported or unterminated variable block")
    if not body:
        raise SourceUnitError("function block body is empty")
    seen: set[str] = set()
    for declaration in declarations:
        folded = declaration.name.casefold()
        if folded in seen:
            raise SourceUnitError(f"duplicate declaration {declaration.name}")
        seen.add(folded)
        declared_type = declaration.type_text.upper()
        if declared_type in _UNSUPPORTED_DVP_ES3_TYPES:
            raise SourceUnitError(
                f"ISPSoft DVP-ES3 does not provide IEC {declared_type} as a local type; "
                "use a saturating scan counter derived from metadata.scan.period_ms"
            )
    public_port_names = {
        item.name.casefold() for item in declarations
        if item.scope in {"VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT"}
    }
    device = next(
        (
            item for item in _DELTA_DEVICE_RE.finditer(portable_source)
            if item.group(0).casefold() not in public_port_names
        ),
        None,
    )
    if device is not None:
        raise SourceUnitError(
            f"direct Delta device {device.group(0)} is forbidden in the isolated candidate"
        )
    return FunctionBlock(name, tuple(declarations), body)


def _increment_has_upper_bound_guard(body: str, name: str) -> bool:
    """Return whether every direct self-increment is under ``name < bound``.

    This intentionally checks a small, auditable ST pattern instead of trying
    to prove arbitrary data-flow properties.  A candidate can always express a
    bounded elapsed counter as ``IF counter < threshold THEN counter := counter
    + 1; END_IF``.  Requiring that form prevents a bounded test suite from
    accepting an integer that would overflow only after a long deployment.
    """
    escaped = re.escape(name)
    token_re = re.compile(
        rf"(?is)"
        rf"(?P<end_if>\bEND_IF\b)"
        rf"|(?P<elsif>\bELSIF\b(?P<elsif_condition>.*?)\bTHEN\b)"
        rf"|(?P<else>\bELSE\b)"
        rf"|(?P<if>\bIF\b(?P<if_condition>.*?)\bTHEN\b)"
        rf"|(?P<increment>\b{escaped}\s*:=\s*{escaped}\s*\+\s*[1-9][0-9]*\s*;)"
    )
    upper_bound_re = re.compile(
        rf"(?i)\b{escaped}\s*<\s*(?:[0-9]+|{_IDENTIFIER})\b"
    )
    active_conditions: list[str | None] = []
    saw_increment = False
    for token in token_re.finditer(body):
        if token.group("end_if") is not None:
            if active_conditions:
                active_conditions.pop()
            continue
        if token.group("elsif") is not None:
            if active_conditions:
                active_conditions[-1] = token.group("elsif_condition")
            continue
        if token.group("else") is not None:
            if active_conditions:
                active_conditions[-1] = None
            continue
        if token.group("if") is not None:
            active_conditions.append(token.group("if_condition"))
            continue
        saw_increment = True
        protected = any(
            condition is not None
            and re.search(r"(?i)\bOR\b", condition) is None
            and upper_bound_re.search(condition) is not None
            for condition in active_conditions
        )
        if not protected:
            return False
    return saw_increment


def _increments_have_dominating_literal_resets(body: str, name: str) -> bool:
    """Recognise per-scan accumulators initialized on every increment path.

    Variables declared in ``VAR`` retain storage on a PLC, but a literal reset
    that syntactically dominates each later increment makes channel counts and
    similar accumulators scan-local in behavior.  A reset can be at function
    block level or in the same enclosing IF branch as its increments.  Branch
    identities are tracked so a reset in ``IF NOT Enable`` cannot justify an
    increment in the corresponding ``ELSE`` branch.
    """
    escaped = re.escape(name)
    token_re = re.compile(
        rf"(?is)"
        rf"(?P<end_if>\bEND_IF\b)"
        rf"|(?P<end_case>\bEND_CASE\b)"
        rf"|(?P<end_while>\bEND_WHILE\b)"
        rf"|(?P<end_for>\bEND_FOR\b)"
        rf"|(?P<until>\bUNTIL\b)"
        rf"|(?P<elsif>\bELSIF\b.*?\bTHEN\b)"
        rf"|(?P<else>\bELSE\b)"
        rf"|(?P<if>\bIF\b.*?\bTHEN\b)"
        rf"|(?P<case>\bCASE\b.*?\bOF\b)"
        rf"|(?P<while>\bWHILE\b.*?\bDO\b)"
        rf"|(?P<for>\bFOR\b.*?\bDO\b)"
        rf"|(?P<repeat>\bREPEAT\b)"
        rf"|(?P<assignment>\b{escaped}\s*:=\s*(?P<rhs>[^;]+);)"
    )
    frames: list[list[object]] = []
    next_frame = 0
    reset_paths: list[tuple[tuple[int, int], ...]] = []
    saw_increment = False
    for token in token_re.finditer(body):
        if any(token.group(label) is not None for label in (
            "end_if", "end_case", "end_while", "end_for", "until"
        )):
            if frames:
                frames.pop()
            continue
        if token.group("elsif") is not None or token.group("else") is not None:
            if frames and frames[-1][2] == "if":
                frames[-1][1] = int(frames[-1][1]) + 1
            continue
        opened = next(
            (label for label in ("if", "case", "while", "for", "repeat")
             if token.group(label) is not None),
            None,
        )
        if opened is not None:
            frames.append([next_frame, 0, opened])
            next_frame += 1
            continue
        rhs = str(token.group("rhs")).strip()
        path = tuple((int(frame[0]), int(frame[1])) for frame in frames)
        if re.fullmatch(r"[+-]?[0-9]+", rhs) is not None:
            # CASE alternatives and loop iterations are not represented by the
            # deliberately small dominance model, so resets inside them are
            # not used as evidence.  A reset outside them may still dominate.
            if all(frame[2] == "if" for frame in frames):
                reset_paths.append(path)
            continue
        if re.fullmatch(
            rf"(?i){escaped}\s*\+\s*[1-9][0-9]*",
            rhs,
        ) is None:
            continue
        saw_increment = True
        if not any(path[:len(reset)] == reset for reset in reset_paths):
            return False
    return saw_increment


def unsaturated_retained_integer_names(block: FunctionBlock) -> tuple[str, ...]:
    """Return retained-INT names that lack a simple syntactic bound pattern.

    This is an advisory pattern check, not a semantic proof.  A state-machine
    transition can bound a counter without using the recognised syntax, so the
    result must not by itself reject a DVP candidate.
    """
    body = _strip_comments(block.body)
    unsafe: list[str] = []
    for declaration in block.declarations:
        if declaration.scope != "VAR" or declaration.type_text.upper() != "INT":
            continue
        escaped = re.escape(declaration.name)
        if re.search(
            rf"(?i)\b{escaped}\s*:=\s*{escaped}\s*\+\s*[1-9][0-9]*\s*;",
            body,
        ) is None:
            continue
        if _increments_have_dominating_literal_resets(body, declaration.name):
            continue
        if not _increment_has_upper_bound_guard(body, declaration.name):
            unsafe.append(declaration.name)
    return tuple(sorted(unsafe, key=str.casefold))


def validate_saturating_retained_integers(block: FunctionBlock) -> None:
    """Apply the advisory saturation pattern as an optional strict policy."""
    unsafe = unsaturated_retained_integer_names(block)
    if unsafe:
        names = ", ".join(sorted(unsafe, key=str.casefold))
        raise SourceUnitError(
            "retained INT self-increment lacks an explicit saturation guard "
            f"(IF counter < bound THEN ...): {names}"
        )


def _render_variable_section(declarations: tuple[Declaration, ...]) -> str:
    if not declarations:
        return "<LOCAL_VAR>\r\n</LOCAL_VAR>"
    rows = ["<LOCAL_VAR>", "<VAR>"]
    for declaration in declarations:
        value = declaration.initializer if declaration.initializer is not None else ""
        rows.extend(
            [
                "{",
                f"{declaration.name} : {declaration.type_text} := {value} [@@] {{{declaration.scope}}}",
                "(*",
                "",
                "*)",
                "}",
            ]
        )
    rows.extend(["</VAR>", "</LOCAL_VAR>"])
    return "\r\n".join(rows)


def _render_source(name: str, content_type: int, kind: str, declarations: tuple[Declaration, ...], body: str) -> bytes:
    if not re.fullmatch(_IDENTIFIER, name):
        raise SourceUnitError(f"invalid POU name {name!r}")
    if kind not in {"FB", "PRG"}:
        raise SourceUnitError(f"invalid POU kind {kind!r}")
    folder = "FBFolder" if kind == "FB" else "ProgramFolder"
    path = "FB" if kind == "FB" else "Program"
    pou_type = 1 if kind == "FB" else 0
    rows = [
        "<GroupPOUFolder>",
        f"<{folder}>",
        "<FolderContent>",
        f"ContentType={content_type}",
        f"ContentName={name} [{kind},ST]",
        f"ContentPath={path}/{name} [{kind},ST]",
        "</FolderContent>",
        f"</{folder}>",
        "</GroupPOUFolder>",
        "<POU>",
        f"P_Name={name}",
        "P_En_Eno=TRUE",
        "P_Last_Chg=",
        f"P_type={pou_type}",
        "P_Rtn_Type=",
        "P_Lang=4",
        "P_Step=0",
        "P_Version=1.00",
        "P_DeltaFB=FALSE",
        "P_Security=",
        "P_Active=TRUE",
        "P_Priority=9999",
        "P_DFBName=",
        "(*",
        "",
        "*)",
        _render_variable_section(declarations),
        "<VAR_EXTERN>",
        "</VAR_EXTERN>",
        "<VAR_EXTERN_C>",
        "</VAR_EXTERN_C>",
        "<IL_ST_CODE>",
        body.strip(),
        "</IL_ST_CODE>",
        "</POU>",
        "",
    ]
    return "\r\n".join(rows).encode("utf-8")


def render_function_block_source(block: FunctionBlock) -> bytes:
    return _render_source(block.name, 1, "FB", block.declarations, block.body)


def render_program_source(name: str, declarations: tuple[Declaration, ...], body: str) -> bytes:
    return _render_source(name, 0, "PRG", declarations, body)


def _crc_update(crc_value: int, value: int) -> int:
    return (crc_value >> 8) ^ _CRC_TABLE[(crc_value ^ value) & 0xFF]


# Expand the table without depending on private zipfile implementation details.
_table = []
for _index in range(256):
    _value = _index
    for _ in range(8):
        _value = (_value >> 1) ^ 0xEDB88320 if _value & 1 else _value >> 1
    _table.append(_value)
_CRC_TABLE = tuple(_table)
del _table, _index, _value


class _ZipCrypto:
    def __init__(self, password: bytes):
        if not password:
            raise SourceUnitError("ISPSoft source-unit password is empty")
        self.key0 = 0x12345678
        self.key1 = 0x23456789
        self.key2 = 0x34567890
        for value in password:
            self._update(value)

    def _update(self, value: int) -> None:
        self.key0 = _crc_update(self.key0, value)
        self.key1 = ((self.key1 + (self.key0 & 0xFF)) * 134775813 + 1) & 0xFFFFFFFF
        self.key2 = _crc_update(self.key2, (self.key1 >> 24) & 0xFF)

    def encrypt(self, data: bytes) -> bytes:
        result = bytearray()
        for value in data:
            temporary = (self.key2 | 2) & 0xFFFFFFFF
            encrypted = value ^ (((temporary * (temporary ^ 1)) >> 8) & 0xFF)
            result.append(encrypted)
            self._update(value)
        return bytes(result)


def _dos_datetime(moment: dt.datetime | None = None) -> tuple[int, int]:
    # ISPSoft's own ZipBuilder stores the current local DOS timestamp.  Its
    # importer rejects otherwise valid, newly named source units produced with
    # the 1980 epoch value, so reproduce the vendor writer rather than forcing
    # byte-level determinism on this transport container.  Source and manifest
    # hashes remain deterministic and are the identities used by the ledger.
    now = moment or dt.datetime.now()
    year = min(2107, max(1980, now.year))
    dos_time = (now.hour << 11) | (now.minute << 5) | (now.second // 2)
    dos_date = ((year - 1980) << 9) | (now.month << 5) | now.day
    return dos_time, dos_date


def _encrypted_zip(
    source: bytes,
    password: str,
    timestamp: dt.datetime | None = None,
) -> bytes:
    filename = b"Unzipped.src"
    crc = binascii.crc32(source) & 0xFFFFFFFF
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(source) + compressor.flush()
    # Traditional ZipCrypto validates the high CRC byte when bit 3 is clear.
    encryption_header = hashlib.sha256(source).digest()[:11] + bytes([(crc >> 24) & 0xFF])
    crypto = _ZipCrypto(password.encode("utf-8"))
    encrypted = crypto.encrypt(encryption_header + compressed)
    flags = 0x0003  # encrypted, maximum compression
    method = 8
    dos_time, dos_date = _dos_datetime(timestamp)
    local = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,
        20,
        flags,
        method,
        dos_time,
        dos_date,
        crc,
        len(encrypted),
        len(source),
        len(filename),
        0,
    ) + filename + encrypted
    # ISPSoft 3.24 writes (and, for a new POU, expects) the signed 16-byte data
    # descriptor even though its general-purpose flag does not set bit 3.  A
    # standards-compliant ZIP reader tolerates its absence, but ISPSoft only
    # got as far as reading the POU identity and then reported "import failed".
    # Preserve Delta's exact package dialect instead of normalising it away.
    descriptor = struct.pack("<IIII", 0x08074B50, crc, len(encrypted), len(source))
    external_attributes = 0x21 if b"<FBFolder>" in source else 0x20
    central = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        0x02014B50,
        20,
        20,
        flags,
        method,
        dos_time,
        dos_date,
        crc,
        len(encrypted),
        len(source),
        len(filename),
        0,
        0,
        0,
        1,
        external_attributes,
        0,
    ) + filename
    eocd = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(central),
        len(local) + len(descriptor),
        0,
    )
    return local + descriptor + central + eocd


def build_ispsoft_package(
    source: bytes,
    password: str,
    *,
    timestamp: dt.datetime | None = None,
) -> bytes:
    """Return an ISPSoft-compatible FBU/MPU container.

    ``timestamp`` is exposed because ISPSoft extracts every source unit to the
    same temporary member name.  Consecutive FBU and MPU imports with identical
    two-second DOS timestamps can cause the importer to reuse the first member.
    The submitter therefore assigns adjacent units distinct timestamps.
    """
    archive = _encrypted_zip(source, password, timestamp)
    header = bytearray(152)
    struct.pack_into("<I", header, 12, 0x3FC)
    struct.pack_into("<I", header, 16, 0xED8)
    struct.pack_into("<I", header, 148, len(archive))
    return bytes(header) + archive
