#!/usr/bin/env python3
"""Genie project history and development-stage helper.

Uses only the Python standard library. Run with ``--help`` for commands.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


GENIE_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = GENIE_ROOT / "manifest.json"
ALLOWED_STATUSES = {
    "completed",
    "passed",
    "partial",
    "failed",
    "blocked",
    "not-applicable",
}
SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|passwd|cookie|authorization)\b\s*[:=]\s*([^\s,;]+)"
)
URL_PATTERN = re.compile(r"https?://[^\s)>\]}]+")
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(secret|password|passwd|token|cookie|authorization|private[_-]?key|api[_-]?key)"
)


def now_local() -> datetime:
    return datetime.now().astimezone()


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported Genie manifest schema")
    return manifest


def run_git(project: Path, *args: str) -> str | None:
    try:
        process = subprocess.run(
            ["git", "-c", f"safe.directory={project.as_posix()}", "-C", str(project), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return process.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def resolve_project(value: str | None) -> Path:
    candidate = Path(value).expanduser().resolve() if value else Path.cwd().resolve()
    top = run_git(candidate, "rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else candidate


def history_root(project: Path, manifest: dict[str, Any]) -> Path:
    return project / manifest["history_root"]


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def ensure_history(project: Path, manifest: dict[str, Any]) -> tuple[Path, bool]:
    root = history_root(project, manifest)
    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    meta = root / "_meta.json"
    if not meta.exists():
        content = {
            "schema_version": 1,
            "created_at": now_local().isoformat(timespec="seconds"),
            "description": "Genie skill execution summaries. Full conversations are not stored.",
        }
        atomic_write(meta, json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    return root, created


def print_created_notice(created: bool) -> None:
    if created:
        print(
            "Genie 실행 기록 폴더 docs/genie가 없습니다. "
            "이번 실행부터 결과 요약을 보관하기 위해 폴더를 생성합니다."
        )


def sanitize_url(match: re.Match[str]) -> str:
    raw = match.group(0)
    trailing = ""
    while raw and raw[-1] in ".,;:":
        trailing = raw[-1] + trailing
        raw = raw[:-1]
    try:
        parts = urlsplit(raw)
        clean = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return clean + trailing
    except ValueError:
        return "[REDACTED_URL]" + trailing


def redact_text(value: str) -> str:
    value = SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)
    return URL_PATTERN.sub(sanitize_url, value)


def sanitize(value: Any, key: str = "") -> Any:
    if SENSITIVE_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item, key) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def skill_lookup(manifest: dict[str, Any], value: str) -> dict[str, Any]:
    normalized = value.strip().lower()
    for skill in manifest["skills"]:
        aliases = {skill["id"].lower(), skill["history_dir"].lower()}
        aliases.add(skill["id"].removeprefix("genie-").lower())
        if normalized in aliases:
            return skill
    raise ValueError(f"Unknown Genie skill: {value}")


def git_context(project: Path) -> tuple[str, str]:
    branch = run_git(project, "branch", "--show-current") or "not-a-git-repository"
    commit = run_git(project, "rev-parse", "--short=12", "HEAD") or "unknown"
    return branch, commit


def slugify(value: str) -> str:
    value = value.strip().lower().replace("_", "-").replace(" ", "-")
    value = re.sub(r"[^0-9a-z가-힣-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:64] or "general"


def yaml_value(value: Any) -> str:
    return json.dumps(value if value is not None else "", ensure_ascii=False)


def markdown_list(values: Any, empty: str) -> str:
    if not isinstance(values, list) or not values:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in values)


def command_init(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    print(f"GENIE_HISTORY={root}")
    return 0


def load_payload(path_value: str) -> dict[str, Any]:
    if path_value == "-":
        payload = json.load(sys.stdin)
    else:
        with Path(path_value).expanduser().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")
    return sanitize(payload)


def command_record(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    payload = load_payload(args.payload)

    if not payload.get("skill"):
        raise ValueError("Payload field 'skill' is required")
    skill = skill_lookup(manifest, str(payload["skill"]))
    status = str(payload.get("status", "completed"))
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported status: {status}")

    finished = now_local()
    started_at = str(payload.get("started_at") or finished.isoformat(timespec="seconds"))
    finished_at = finished.isoformat(timespec="seconds")
    branch, commit = git_context(project)
    work_item = slugify(str(payload.get("work_item") or "general"))
    scope = str(payload.get("scope") or "project")
    environment = str(payload.get("environment") or "local")
    stamp = finished.strftime("%Y-%m-%d_%H%M%S%z")
    filename = f"{stamp}__{work_item}__{slugify(commit)[:12]}.md"
    destination = root / skill["history_dir"] / filename

    optional_meta = []
    for key in ("tested_url", "deployment_revision", "release_id"):
        if payload.get(key):
            optional_meta.append(f"{key}: {yaml_value(payload[key])}")

    content = f"""---
skill: {yaml_value(skill['id'])}
status: {yaml_value(status)}
started_at: {yaml_value(started_at)}
finished_at: {yaml_value(finished_at)}
branch: {yaml_value(branch)}
commit: {yaml_value(commit)}
work_item: {yaml_value(work_item)}
scope: {yaml_value(scope)}
environment: {yaml_value(environment)}
{"\n".join(optional_meta)}
---

# {skill['stage']} 실행 요약

## 목적과 대화 요약

{payload.get('summary') or '요약이 제공되지 않았습니다.'}

## 중요 결정

{markdown_list(payload.get('decisions'), '기록된 결정 없음')}

## 결과

{payload.get('result') or payload.get('summary') or '결과가 제공되지 않았습니다.'}

## 검증

{markdown_list(payload.get('validation'), '수행한 검증 없음')}

## 미완료·차단

{markdown_list(payload.get('incomplete'), '없음')}

## 다음 단계

{markdown_list(payload.get('next_steps'), '없음')}

## 관련 산출물

{markdown_list(payload.get('artifacts'), '없음')}
"""
    atomic_write(destination, content)
    print(f"GENIE_RECORD={destination}")
    return 0


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}
    result: dict[str, Any] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        raw = raw.strip()
        try:
            result[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            result[key.strip()] = raw.strip('"')
    result["_path"] = str(path)
    return result


def latest_record(root: Path, skill: dict[str, Any]) -> dict[str, Any] | None:
    directory = root / skill["history_dir"]
    if not directory.exists():
        return None
    files = sorted(directory.glob("*.md"), reverse=True)
    return parse_frontmatter(files[0]) if files else None


def changed_files(project: Path, old_commit: str) -> list[str] | None:
    output = run_git(project, "diff", "--name-only", f"{old_commit}..HEAD")
    if output is None:
        return None
    files = [line.replace("\\", "/") for line in output.splitlines() if line.strip()]
    return [
        path
        for path in files
        if not (
            path == "docs/genie/_meta.json"
            or (path.startswith("docs/genie/") and path.endswith(".md"))
        )
    ]


def matches_any(path: str, patterns: list[str]) -> bool:
    if "**" in patterns:
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def freshness_state(project: Path, current_commit: str, skill: dict[str, Any], record: dict[str, Any] | None) -> str:
    if record is None:
        return "never-run"
    status = str(record.get("status", "unknown"))
    if status not in {"completed", "passed", "not-applicable"}:
        return status
    if status == "not-applicable":
        return "not-applicable"
    policy = skill.get("freshness", "commit")
    if policy == "durable":
        return "current"
    recorded_commit = str(record.get("commit") or "unknown")
    if current_commit == "unknown" or recorded_commit == "unknown":
        return "unknown"
    if recorded_commit == current_commit or current_commit.startswith(recorded_commit):
        return "current"
    if policy == "commit":
        files = changed_files(project, recorded_commit)
        return "current" if files == [] else "stale"
    files = changed_files(project, recorded_commit)
    if files is None:
        return "stale"
    patterns = list(skill.get("invalidated_by") or [])
    return "stale" if any(matches_any(path, patterns) for path in files) else "current"


def status_rows(project: Path, manifest: dict[str, Any], selected: str | None = None) -> list[dict[str, Any]]:
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    _, current_commit = git_context(project)
    rows = []
    for skill in sorted(manifest["skills"], key=lambda item: item["order"]):
        if selected:
            wanted = skill_lookup(manifest, selected)
            if skill["id"] != wanted["id"]:
                continue
        record = latest_record(root, skill)
        rows.append(
            {
                "stage": skill["stage"],
                "skill": skill["id"],
                "description": skill["description"],
                "last_run": record.get("finished_at", "-") if record else "-",
                "result": record.get("status", "-") if record else "-",
                "freshness": freshness_state(project, current_commit, skill, record),
                "work_item": record.get("work_item", "-") if record else "-",
                "required_by_default": bool(skill.get("required_by_default")),
            }
        )
    return rows


def table_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def next_recommendation(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row["required_by_default"] and row["freshness"] in {
            "never-run",
            "stale",
            "failed",
            "partial",
            "blocked",
            "unknown",
        }:
            return row
    return None


def command_status(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    rows = status_rows(project, manifest, args.skill)
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print("| 단계 | 스킬 | 마지막 실행 | 결과 | 유효성 | 대상 |")
    print("| --- | --- | --- | --- | --- | --- |")
    for row in rows:
        print(
            "| {stage} | `{skill}` | {last_run} | {result} | {freshness} | {work_item} |".format(
                **{key: table_escape(value) for key, value in row.items()}
            )
        )
    recommendation = next_recommendation(rows)
    if recommendation:
        print(
            f"\n다음 권장: {recommendation['skill']} — "
            f"{recommendation['description']} ({recommendation['freshness']})"
        )
    elif args.skill:
        print("\n선택한 스킬의 최신 기록은 현재 유효합니다.")
    else:
        print("\n기본 필수 단계는 현재 기록 기준으로 유효합니다. 조건부 단계를 범위에 맞게 검토하세요.")
    return 0


def command_history(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    skill = skill_lookup(manifest, args.skill)
    directory = root / skill["history_dir"]
    files = sorted(directory.glob("*.md"), reverse=True) if directory.exists() else []
    print("| 실행일 | 결과 | 대상 | 커밋 | 파일 |")
    print("| --- | --- | --- | --- | --- |")
    for path in files[: args.limit]:
        record = parse_frontmatter(path)
        print(
            f"| {table_escape(record.get('finished_at', '-'))} | "
            f"{table_escape(record.get('status', '-'))} | "
            f"{table_escape(record.get('work_item', '-'))} | "
            f"{table_escape(record.get('commit', '-'))} | {path.name} |"
        )
    if not files:
        print(f"\n{skill['id']} 실행 기록이 없습니다.")
    return 0


def reject_sensitive_config(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                raise ValueError(f"Deploy config must not contain sensitive key: {child_path}")
            reject_sensitive_config(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_config(child, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_PATTERN.search(value):
        raise ValueError(f"Deploy config appears to contain a plaintext secret at: {path}")


def command_configure_deploy(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    config = load_payload(args.payload)
    reject_sensitive_config(config)
    config["schema_version"] = 1
    config["updated_at"] = now_local().isoformat(timespec="seconds")
    destination = root / "project-deploy" / "config.json"
    atomic_write(destination, json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    print(f"GENIE_DEPLOY_CONFIG={destination}")
    return 0


def command_doctor(_: argparse.Namespace) -> int:
    errors: list[str] = []
    try:
        manifest = load_manifest()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    ids = [skill.get("id") for skill in manifest.get("skills", [])]
    if len(ids) != 15:
        errors.append(f"Expected 15 worker skills, found {len(ids)}")
    if len(ids) != len(set(ids)):
        errors.append("Duplicate worker skill ids")
    if not (GENIE_ROOT / "SKILL.md").exists():
        errors.append("Missing Genie orchestrator SKILL.md")
    for skill_id in ids:
        skill_file = GENIE_ROOT / "skills" / str(skill_id) / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"Missing worker skill: {skill_file}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Genie doctor: OK (1 orchestrator, 15 workers)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genie development workflow history helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create docs/genie metadata when missing")
    init_parser.add_argument("--project")
    init_parser.set_defaults(func=command_init)

    record_parser = subparsers.add_parser("record", help="Write one immutable skill summary")
    record_parser.add_argument("--project")
    record_parser.add_argument("--payload", required=True, help="JSON file path or - for stdin")
    record_parser.set_defaults(func=command_record)

    status_parser = subparsers.add_parser("status", help="Show the latest state for Genie skills")
    status_parser.add_argument("--project")
    status_parser.add_argument("--skill")
    status_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    status_parser.set_defaults(func=command_status)

    history_parser = subparsers.add_parser("history", help="List past runs for one skill")
    history_parser.add_argument("--project")
    history_parser.add_argument("--skill", required=True)
    history_parser.add_argument("--limit", type=int, default=20)
    history_parser.set_defaults(func=command_history)

    deploy_parser = subparsers.add_parser(
        "configure-deploy", help="Persist a non-secret project deployment workflow"
    )
    deploy_parser.add_argument("--project")
    deploy_parser.add_argument("--payload", required=True)
    deploy_parser.set_defaults(func=command_configure_deploy)

    doctor_parser = subparsers.add_parser("doctor", help="Validate the installed Genie pack")
    doctor_parser.set_defaults(func=command_doctor)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
