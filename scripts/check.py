#!/usr/bin/env python3
"""Deterministic repo gate, no LLM: run before every commit and in CI.

PX001 en or em dash             PX005 broken relative link in Markdown
PX002 secret-shaped string      PX006 JSON file does not parse
PX003 skill frontmatter         PX007 plugin.json, marketplace.json and CHANGELOG versions differ
PX004 absolute home path        PX008 CR line end (every text file is LF)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DASHES = (chr(0x2013), chr(0x2014))
TEXT = {".md", ".py", ".sh", ".json", ".yml", ".yaml", ".toml", ".txt", ".svg", ".in"}
TEXT_NAMES = {"LICENSE", "CODEOWNERS", ".gitignore", ".gitattributes", ".editorconfig"}
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".ruff_cache",
    "videos",
    "outputs",
    "frames",
    "review",
}
SECRETS = [
    ("aws access key", re.compile(r"\bA(?:KIA|SIA)[0-9A-Z]{16}\b")),
    (
        "github token",
        re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|\bgithub_pat_\w{40,}"),
    ),
    ("api key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{24,}")),
]
HOME_PATH = re.compile(
    r"\b[A-Za-z]:[\\/]Users[\\/](?!\.\.\.)[\w.-]+|/c/Users/(?!\.\.\.)[\w.-]+"
    r"|/home/(?!runner\b)[a-z][\w.-]*/|/Users/(?!Shared\b)[A-Z][\w.-]+/"
)
MD_LINK = re.compile(r"\]\((?!https?:|mailto:|#|\{\{)([^)\s]+)\)")
INLINE_CODE = re.compile(r"`[^`]*`")
HTML_REF = re.compile(r"\b(?:src|srcset|href)=\"(?!https?:|mailto:|#|data:)([^\"]+)\"")
CHANGELOG_HEAD = re.compile(r"^## (\d+\.\d+\.\d+)\b", re.MULTILINE)


def files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT).parts
        textual = p.suffix in TEXT or p.name in TEXT_NAMES
        if p.is_file() and not SKIP_DIRS.intersection(rel) and textual:
            out.append(p)
    return sorted(out)


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Flat key: value frontmatter with folded (>-) values joined; returns (meta, raw head)."""
    if not text.startswith("---"):
        return {}, ""
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, ""
    meta: dict[str, str] = {}
    key = None
    for raw in lines[1:end]:
        if key and raw.startswith((" ", "\t")):
            meta[key] = f"{meta[key]} {raw.strip()}".strip()
            continue
        key = None
        name, sep, value = raw.partition(":")
        if not sep or raw.startswith((" ", "\t", "#")):
            continue
        name, value = name.strip(), value.strip()
        meta[name] = "" if value in (">", ">-", "|", "|-") else value.strip("\"'")
        if value in (">", ">-", "|", "|-", ""):
            key = name
    return meta, "\n".join(lines[1:end])


def check_skill(p: Path, rel: str, text: str) -> list[str]:
    meta, head = frontmatter(text)
    problems = []
    if meta.get("name") != p.parent.name:
        problems.append(
            f"{rel}:1 PX003 name {meta.get('name')!r} must equal folder {p.parent.name!r}"
        )
    desc = meta.get("description", "")
    if not desc:
        problems.append(f"{rel}:1 PX003 missing description")
        return problems
    if not re.search(r"^description:\s*>-?\s*$", head, re.MULTILINE):
        problems.append(f"{rel}:1 PX003 description must be a folded block scalar (>-)")
    if len(desc) > 1024:
        problems.append(f"{rel}:1 PX003 description is {len(desc)} chars (max 1024)")
    if "Use when" not in desc:
        problems.append(
            f'{rel}:1 PX003 description needs "Use when ..." trigger phrases'
        )
    return problems


def check_links(p: Path, rel: str, n: int, line: str) -> list[str]:
    problems = []
    for target in MD_LINK.findall(line) + HTML_REF.findall(line):
        clean = target.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        resolved = (p.parent / clean).resolve()
        if not resolved.is_relative_to(ROOT):
            continue  # workspace stacking links point outside the repo; not checkable here
        if not resolved.exists():
            problems.append(f"{rel}:{n} PX005 broken link {target}")
    return problems


def check_versions() -> list[str]:
    try:
        plugin = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        market = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []  # PX006 already reports the parse error
    entries = [
        e for e in market.get("plugins", []) if e.get("name") == plugin.get("name")
    ]
    if not entries:
        return [
            f".claude-plugin/marketplace.json:1 PX007 no entry for {plugin.get('name')!r}"
        ]
    versions = {plugin.get("version")} | {e.get("version") for e in entries}
    changelog = ROOT / "CHANGELOG.md"
    head = (
        CHANGELOG_HEAD.search(changelog.read_text(encoding="utf-8"))
        if changelog.exists()
        else None
    )
    versions.add(head.group(1) if head else "missing")
    if len(versions) != 1:
        return [
            f".claude-plugin/plugin.json:1 PX007 versions differ: {sorted(map(str, versions))}"
        ]
    return []


def main() -> int:
    problems: list[str] = []
    me = Path(__file__).resolve()
    checked = files()
    for p in checked:
        rel = p.relative_to(ROOT).as_posix()
        raw = p.read_bytes()
        if b"\r" in raw:
            problems.append(f"{rel}:1 PX008 {raw.count(b'\r')} CR bytes; files are LF")
        text = raw.decode("utf-8", errors="replace")
        fenced = False
        for n, line in enumerate(text.splitlines(), 1):
            if p.suffix == ".md" and line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
            elif p.suffix == ".md" and not fenced:
                # snippets in inline code are examples, not links
                problems += check_links(p, rel, n, INLINE_CODE.sub("", line))
            if any(d in line for d in DASHES):
                problems.append(f"{rel}:{n} PX001 en or em dash; use - or --")
            for label, rx in SECRETS:
                if rx.search(line):
                    problems.append(f"{rel}:{n} PX002 looks like a {label}")
            home = HOME_PATH.search(line) if p != me else None
            if home:
                problems.append(f"{rel}:{n} PX004 absolute home path {home.group(0)!r}")
        if p.suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                problems.append(f"{rel}:{exc.lineno} PX006 invalid JSON: {exc.msg}")
        if p.name == "SKILL.md":
            problems += check_skill(p, rel, text)
    problems += check_versions()
    for line in problems:
        print(line)
    print(f"{len(checked)} files checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
