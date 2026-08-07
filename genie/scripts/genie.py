#!/usr/bin/env python3
"""Genie project history and development-stage helper.

Uses only the Python standard library. Run with ``--help`` for commands.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
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
PROJECT_CONFIG_DIR = ".genie"
PROJECT_CONFIG_NAME = "config.json"
PROJECT_CONFIG_SCHEMA_VERSION = 2
IGNORED_SCAN_DIRECTORIES = {
    ".dart_tool",
    ".git",
    ".genie",
    ".gradle",
    ".idea",
    ".next",
    ".turbo",
    ".venv",
    "build",
    "coverage",
    "dist",
    "docs",
    "node_modules",
    "target",
    "vendor",
}
MOBILE_PACKAGES = {
    "expo",
    "react-native",
}
WEB_FRAMEWORK_PACKAGES = {
    "@angular/core": "angular",
    "@remix-run/react": "remix",
    "@sveltejs/kit": "sveltekit",
    "astro": "astro",
    "next": "next",
    "nuxt": "nuxt",
    "react-dom": "react",
    "svelte": "svelte",
    "vue": "vue",
}
WEB_BUILD_PACKAGES = {"vite", "webpack", "parcel"}
SSR_FRAMEWORKS = {"next", "nuxt", "remix", "sveltekit"}
PWA_PACKAGES = {
    "@vite-pwa/plugin",
    "next-pwa",
    "vite-plugin-pwa",
    "workbox-build",
    "workbox-window",
}
OTA_PACKAGES = {
    "expo-updates",
    "react-native-code-push",
    "@revopush/react-native-code-push",
}
BACKEND_PACKAGES = {
    "@nestjs/core",
    "@vercel/node",
    "express",
    "fastify",
    "firebase-functions",
    "hono",
    "koa",
    "serverless",
}
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


def project_config_path(project: Path) -> Path:
    return project / PROJECT_CONFIG_DIR / PROJECT_CONFIG_NAME


def migrate_project_config(config: dict[str, Any]) -> dict[str, Any]:
    source_schema = config.get("schema_version")
    if source_schema == PROJECT_CONFIG_SCHEMA_VERSION:
        return config
    if source_schema != 1:
        raise ValueError("Unsupported Genie project config schema")

    migrated = dict(config)
    migrated["schema_version"] = PROJECT_CONFIG_SCHEMA_VERSION
    migrated["_source_schema_version"] = source_schema
    paths = dict(migrated.get("paths") or {})
    if "flutter" in paths and "mobile" not in paths:
        paths["mobile"] = paths.pop("flutter")
    migrated["paths"] = paths

    tracks = ["mobile" if track == "flutter" else track for track in migrated.get("tracks", [])]
    migrated["tracks"] = list(dict.fromkeys(tracks))
    detected = dict(migrated.get("detected") or {})
    surfaces = [
        "mobile" if surface == "flutter" else surface
        for surface in detected.get("surfaces", [])
    ]
    detected["surfaces"] = list(dict.fromkeys(surfaces))
    migrated["detected"] = detected
    technologies = set(detected.get("technologies") or [])
    mobile_frameworks = []
    if "flutter" in technologies:
        mobile_frameworks.append("flutter")
    if "react-native" in technologies:
        mobile_frameworks.append("react-native")
    migrated.setdefault("frameworks", {"mobile": mobile_frameworks} if mobile_frameworks else {})
    migrated.setdefault("targets", [])
    migrated.setdefault("capabilities", [])
    return migrated


def load_project_config(
    project: Path, manifest: dict[str, Any], required: bool = False
) -> dict[str, Any] | None:
    path = project_config_path(project)
    if not path.exists():
        if required:
            raise ValueError(
                "Genie 프로젝트 설정이 없습니다. 먼저 '지니 설정' 또는 "
                "'지니 프로젝트 설정'을 실행하세요."
            )
        return None
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("Genie project config must be a JSON object")
    config = migrate_project_config(config)
    known = {skill["id"] for skill in manifest["skills"]}
    enabled = config.get("enabled_skills")
    if not isinstance(enabled, list) or not all(isinstance(item, str) for item in enabled):
        raise ValueError("Genie project config requires enabled_skills")
    unknown = sorted(set(enabled) - known)
    if unknown:
        raise ValueError(f"Unknown skills in Genie project config: {', '.join(unknown)}")
    return config


def relative_directory_glob(project: Path, directory: Path) -> str:
    relative = directory.resolve().relative_to(project.resolve()).as_posix()
    return "**" if relative == "." else f"{relative}/**"


def add_path_group(groups: dict[str, set[str]], group: str, pattern: str) -> None:
    groups.setdefault(group, set()).add(pattern)


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def detect_project_structure(project: Path) -> dict[str, Any]:
    technologies: set[str] = set()
    surfaces: set[str] = set()
    frameworks: dict[str, set[str]] = {
        "mobile": set(),
        "web": set(),
        "backend": set(),
    }
    targets: set[str] = set()
    capabilities: set[str] = set()
    groups: dict[str, set[str]] = {
        "mobile": set(),
        "web": set(),
        "web_admin": set(),
        "backend": set(),
        "shared": set(),
    }
    evidence: list[str] = []

    for current, directories, files in os.walk(project):
        current_path = Path(current)
        relative = current_path.relative_to(project)
        depth = len(relative.parts)
        child_directories = {name.lower() for name in directories}
        directories[:] = [
            name
            for name in directories
            if name not in IGNORED_SCAN_DIRECTORIES and not name.startswith(".")
        ]
        if depth >= 4:
            directories[:] = []
        file_names = set(files)
        pattern = relative_directory_glob(project, current_path)
        lower_parts = {part.lower() for part in relative.parts}

        if "pubspec.yaml" in file_names:
            pubspec = current_path / "pubspec.yaml"
            try:
                content = pubspec.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = ""
            if "sdk: flutter" in content or re.search(r"(?m)^flutter\s*:", content):
                technologies.update({"dart", "flutter"})
                surfaces.add("mobile")
                frameworks["mobile"].add("flutter")
                capabilities.update({"device-e2e", "native-platform", "store-release"})
                add_path_group(groups, "mobile", pattern)
                for target in ("android", "ios", "web"):
                    if target in child_directories:
                        targets.add(target)
                evidence.append(pubspec.relative_to(project).as_posix())

        if "package.json" in file_names:
            package_path = current_path / "package.json"
            package = read_json_object(package_path)
            dependencies = set()
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                value = package.get(key)
                if isinstance(value, dict):
                    dependencies.update(str(name) for name in value)
            technologies.add("node")
            mobile_dependencies = dependencies & MOBILE_PACKAGES
            is_react_native = bool(mobile_dependencies)
            if is_react_native:
                technologies.update(sorted(mobile_dependencies | (dependencies & {"react"})))
                surfaces.add("mobile")
                frameworks["mobile"].add(
                    "expo" if "expo" in dependencies else "react-native"
                )
                capabilities.update({"device-e2e", "native-platform", "store-release"})
                add_path_group(groups, "mobile", pattern)
                for target in ("android", "ios"):
                    if target in child_directories:
                        targets.add(target)
                if "react-native-web" in dependencies or "expo" in dependencies:
                    targets.add("web")
                if dependencies & OTA_PACKAGES:
                    capabilities.add("ota")
                evidence.append(package_path.relative_to(project).as_posix())

            web_frameworks = {
                framework
                for package_name, framework in WEB_FRAMEWORK_PACKAGES.items()
                if package_name in dependencies
            }
            is_react_native_web_only = (
                is_react_native
                and web_frameworks <= {"react"}
                and ("react-native-web" in dependencies or "expo" in dependencies)
            )
            if web_frameworks and not is_react_native_web_only:
                technologies.update(sorted(web_frameworks | (dependencies & WEB_BUILD_PACKAGES)))
                frameworks["web"].update(web_frameworks)
                if lower_parts & {"admin", "backoffice", "console", "dashboard"}:
                    surfaces.add("web-admin")
                    add_path_group(groups, "web_admin", pattern)
                    capabilities.add("role-based-access")
                else:
                    surfaces.add("web")
                    add_path_group(groups, "web", pattern)
                targets.add("web")
                capabilities.add("browser-runtime")
                if web_frameworks & SSR_FRAMEWORKS:
                    capabilities.add("ssr")
                evidence.append(package_path.relative_to(project).as_posix())
            elif dependencies & WEB_BUILD_PACKAGES and not is_react_native:
                technologies.update(sorted(dependencies & WEB_BUILD_PACKAGES))
                frameworks["web"].update(sorted(dependencies & WEB_BUILD_PACKAGES))
                if lower_parts & {"admin", "backoffice", "console", "dashboard"}:
                    surfaces.add("web-admin")
                    add_path_group(groups, "web_admin", pattern)
                    capabilities.add("role-based-access")
                else:
                    surfaces.add("web")
                    add_path_group(groups, "web", pattern)
                targets.add("web")
                capabilities.add("browser-runtime")
                evidence.append(package_path.relative_to(project).as_posix())

            if dependencies & PWA_PACKAGES:
                capabilities.update({"offline", "pwa", "service-worker"})
            if dependencies & BACKEND_PACKAGES:
                technologies.update(sorted(dependencies & BACKEND_PACKAGES))
                frameworks["backend"].update(sorted(dependencies & BACKEND_PACKAGES))
                surfaces.add("backend")
                add_path_group(groups, "backend", pattern)
                capabilities.add("api")
                evidence.append(package_path.relative_to(project).as_posix())

        if file_names & {
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "vite.config.js",
            "vite.config.ts",
        }:
            if lower_parts & {"admin", "backoffice", "console", "dashboard"}:
                surfaces.add("web-admin")
                add_path_group(groups, "web_admin", pattern)
                capabilities.add("role-based-access")
            else:
                surfaces.add("web")
                add_path_group(groups, "web", pattern)
            targets.add("web")
            capabilities.add("browser-runtime")
            if file_names & {"next.config.js", "next.config.mjs", "next.config.ts"}:
                frameworks["web"].add("next")
                capabilities.add("ssr")
            elif file_names & {"vite.config.js", "vite.config.ts"}:
                frameworks["web"].add("vite")

        if "index.html" in file_names:
            if lower_parts & {"admin", "backoffice", "console", "dashboard"}:
                surfaces.add("web-admin")
                add_path_group(groups, "web_admin", pattern)
                capabilities.add("role-based-access")
            else:
                surfaces.add("web")
                add_path_group(groups, "web", pattern)
            targets.add("web")
            capabilities.add("browser-runtime")

        if file_names & {"manifest.webmanifest", "service-worker.js", "sw.js"}:
            capabilities.update({"offline", "pwa", "service-worker"})

        if file_names & {"firebase.json", "serverless.yml", "serverless.yaml"}:
            technologies.add("deployment-config")
            surfaces.add("backend")
            add_path_group(groups, "backend", pattern)
            capabilities.add("api")

        if lower_parts & {"api", "backend", "functions", "server"}:
            if file_names & {
                "package.json",
                "pyproject.toml",
                "requirements.txt",
                "go.mod",
                "Cargo.toml",
            }:
                surfaces.add("backend")
                add_path_group(groups, "backend", pattern)
                capabilities.add("api")

        if lower_parts & {"common", "packages", "shared"}:
            add_path_group(groups, "shared", pattern)

    if not surfaces:
        surfaces.add("library")

    if "mobile" in surfaces and not targets.intersection({"android", "ios"}):
        targets.update({"android", "ios"})

    tracks = ["core"]
    if surfaces & {"mobile", "web", "web-admin"}:
        tracks.append("ui")
    if "mobile" in surfaces:
        tracks.append("mobile")
    if surfaces & {"web", "web-admin"}:
        tracks.append("web")
    if "backend" in surfaces:
        tracks.append("backend")
    application_surface_count = sum(
        1
        for present in (
            "mobile" in surfaces,
            bool(surfaces & {"web", "web-admin"}),
            "backend" in surfaces,
        )
        if present
    )
    if application_surface_count >= 2:
        tracks.append("cross-surface")
        capabilities.add("cross-surface")
    if surfaces & {"mobile", "web", "web-admin", "backend"}:
        tracks.append("deploy")

    profile_parts = []
    if "mobile" in surfaces:
        mobile_frameworks = frameworks["mobile"]
        profile_parts.append(
            "flutter"
            if "flutter" in mobile_frameworks
            else "expo"
            if "expo" in mobile_frameworks
            else "react-native"
            if "react-native" in mobile_frameworks
            else "mobile"
        )
    if surfaces & {"web", "web-admin"}:
        profile_parts.append("web")
    if "backend" in surfaces:
        profile_parts.append("backend")
    profile = "-".join(profile_parts) if profile_parts else "library"

    normalized_groups = {
        key: sorted(values) for key, values in groups.items() if values
    }
    normalized_frameworks = {
        key: sorted(values) for key, values in frameworks.items() if values
    }
    fingerprint_source = {
        "technologies": sorted(technologies),
        "surfaces": sorted(surfaces),
        "frameworks": normalized_frameworks,
        "targets": sorted(targets),
        "capabilities": sorted(capabilities),
        "tracks": tracks,
        "paths": normalized_groups,
        "evidence": sorted(set(evidence)),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return {
        **fingerprint_source,
        "profile": profile,
        "structure_fingerprint": fingerprint,
    }


def normalize_skill_ids(
    manifest: dict[str, Any], values: list[str], field_name: str
) -> list[str]:
    result = []
    for value in values:
        try:
            skill_id = skill_lookup(manifest, value)["id"]
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc
        if skill_id not in result:
            result.append(skill_id)
    return result


def skill_path_patterns(skill: dict[str, Any], detected: dict[str, Any]) -> list[str]:
    groups = detected.get("paths", {})
    tracks = set(skill.get("tracks") or ["core"])
    patterns: set[str] = set()
    if "web" in tracks:
        for group in ("web", "web_admin", "backend", "shared"):
            patterns.update(groups.get(group, []))
    if "mobile" in tracks:
        for group in ("mobile", "backend", "shared"):
            patterns.update(groups.get(group, []))
    if "backend" in tracks:
        for group in ("backend", "shared"):
            patterns.update(groups.get(group, []))
    if "ui" in tracks:
        for group in ("mobile", "web", "web_admin", "shared"):
            patterns.update(groups.get(group, []))
    if "cross-surface" in tracks:
        for values in groups.values():
            patterns.update(values)
    if "deploy" in tracks:
        for values in groups.values():
            patterns.update(values)
        patterns.update({".github/**", ".genie/**", "Dockerfile*", "firebase.json"})
    if not patterns:
        patterns.update(skill.get("invalidated_by") or [])
    return sorted(patterns)


def proposed_project_config(
    project: Path,
    manifest: dict[str, Any],
    existing: dict[str, Any] | None = None,
    enable: list[str] | None = None,
    disable: list[str] | None = None,
) -> dict[str, Any]:
    detected = detect_project_structure(project)
    overrides = existing.get("overrides", {}) if existing else {}
    if not isinstance(overrides, dict):
        overrides = {}
    enabled_overrides = normalize_skill_ids(
        manifest, list(overrides.get("enable") or []), "enabled skill"
    )
    disabled_overrides = normalize_skill_ids(
        manifest, list(overrides.get("disable") or []), "disabled skill"
    )
    for skill_id in normalize_skill_ids(manifest, list(enable or []), "enabled skill"):
        if skill_id in disabled_overrides:
            disabled_overrides.remove(skill_id)
        if skill_id not in enabled_overrides:
            enabled_overrides.append(skill_id)
    for skill_id in normalize_skill_ids(manifest, list(disable or []), "disabled skill"):
        if skill_id in enabled_overrides:
            enabled_overrides.remove(skill_id)
        if skill_id not in disabled_overrides:
            disabled_overrides.append(skill_id)
    disabled_set = set(disabled_overrides)

    tracks = set(detected["tracks"])
    recommended = [
        skill["id"]
        for skill in sorted(manifest["skills"], key=lambda item: item["order"])
        if tracks.intersection(skill.get("tracks") or ["core"])
    ]
    enabled_set = (set(recommended) | set(enabled_overrides)) - disabled_set
    enabled_skills = [
        skill["id"]
        for skill in sorted(manifest["skills"], key=lambda item: item["order"])
        if skill["id"] in enabled_set
    ]
    required_skills = [
        skill["id"]
        for skill in manifest["skills"]
        if skill["id"] in enabled_set and skill.get("required_by_default")
    ]
    conditional_skills = [item for item in enabled_skills if item not in required_skills]
    skill_paths = {
        skill["id"]: skill_path_patterns(skill, detected)
        for skill in manifest["skills"]
        if skill["id"] in enabled_set
    }
    timestamp = now_local().isoformat(timespec="seconds")
    return {
        "schema_version": PROJECT_CONFIG_SCHEMA_VERSION,
        "catalog_version": manifest.get("catalog_version", 1),
        "profile": detected["profile"],
        "configured_at": existing.get("configured_at", timestamp) if existing else timestamp,
        "updated_at": timestamp,
        "structure_fingerprint": detected["structure_fingerprint"],
        "detected": {
            "technologies": detected["technologies"],
            "surfaces": detected["surfaces"],
            "evidence": detected["evidence"],
        },
        "frameworks": detected["frameworks"],
        "targets": detected["targets"],
        "capabilities": detected["capabilities"],
        "tracks": detected["tracks"],
        "paths": detected["paths"],
        "enabled_skills": enabled_skills,
        "required_skills": required_skills,
        "conditional_skills": conditional_skills,
        "skill_paths": skill_paths,
        "overrides": {
            "enable": enabled_overrides,
            "disable": disabled_overrides,
        },
    }


def config_changes(
    current: dict[str, Any] | None, proposed: dict[str, Any]
) -> dict[str, list[str]]:
    current_skills = set(current.get("enabled_skills", [])) if current else set()
    proposed_skills = set(proposed.get("enabled_skills", []))
    current_surfaces = set((current or {}).get("detected", {}).get("surfaces", []))
    proposed_surfaces = set(proposed.get("detected", {}).get("surfaces", []))
    current_frameworks = {
        f"{surface}:{framework}"
        for surface, values in ((current or {}).get("frameworks") or {}).items()
        for framework in values
    }
    proposed_frameworks = {
        f"{surface}:{framework}"
        for surface, values in (proposed.get("frameworks") or {}).items()
        for framework in values
    }
    current_targets = set((current or {}).get("targets") or [])
    proposed_targets = set(proposed.get("targets") or [])
    current_capabilities = set((current or {}).get("capabilities") or [])
    proposed_capabilities = set(proposed.get("capabilities") or [])
    return {
        "skills_added": sorted(proposed_skills - current_skills),
        "skills_removed": sorted(current_skills - proposed_skills),
        "surfaces_added": sorted(proposed_surfaces - current_surfaces),
        "surfaces_removed": sorted(current_surfaces - proposed_surfaces),
        "frameworks_added": sorted(proposed_frameworks - current_frameworks),
        "frameworks_removed": sorted(current_frameworks - proposed_frameworks),
        "targets_added": sorted(proposed_targets - current_targets),
        "targets_removed": sorted(current_targets - proposed_targets),
        "capabilities_added": sorted(proposed_capabilities - current_capabilities),
        "capabilities_removed": sorted(current_capabilities - proposed_capabilities),
    }


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


def print_setup_required(project: Path) -> None:
    print("Genie 프로젝트 설정이 없습니다. 설정부터 진행하겠습니다.")
    print(f"GENIE_SETUP_REQUIRED={project_config_path(project)}")


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
    config = load_project_config(project, manifest)
    if config is None:
        print_setup_required(project)
        return 0
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    print(f"GENIE_CONFIG={project_config_path(project)}")
    print(f"GENIE_HISTORY={root}")
    return 0


def print_config_report(
    project: Path,
    current: dict[str, Any] | None,
    proposed: dict[str, Any],
    changes: dict[str, list[str]],
) -> None:
    print(f"프로젝트: {project}")
    print(f"추천 프로필: {proposed['profile']}")
    print(f"감지 영역: {', '.join(proposed['detected']['surfaces'])}")
    technologies = proposed["detected"].get("technologies") or ["명확한 프레임워크 없음"]
    print(f"감지 기술: {', '.join(technologies)}")
    framework_values = [
        f"{surface}={','.join(values)}"
        for surface, values in proposed.get("frameworks", {}).items()
    ]
    print(f"프레임워크: {', '.join(framework_values) if framework_values else '-'}")
    print(f"대상 플랫폼: {', '.join(proposed.get('targets') or ['-'])}")
    print(f"기능 특성: {', '.join(proposed.get('capabilities') or ['-'])}")
    print(f"활성 트랙: {', '.join(proposed['tracks'])}")
    print(f"활성 스킬: {len(proposed['enabled_skills'])}개")
    for skill_id in proposed["enabled_skills"]:
        marker = "필수" if skill_id in proposed["required_skills"] else "조건부"
        print(f"- {skill_id} ({marker})")
    if current is None:
        print("\n현재 설정이 없습니다. 위 구성이 새로 생성됩니다.")
    elif any(changes.values()):
        print("\n현재 설정과 비교:")
        labels = {
            "surfaces_added": "추가 영역",
            "surfaces_removed": "제거 영역",
            "frameworks_added": "추가 프레임워크",
            "frameworks_removed": "제거 프레임워크",
            "targets_added": "추가 대상",
            "targets_removed": "제거 대상",
            "capabilities_added": "추가 기능 특성",
            "capabilities_removed": "제거 기능 특성",
            "skills_added": "추가 스킬",
            "skills_removed": "제거 스킬",
        }
        for key, label in labels.items():
            if changes[key]:
                print(f"- {label}: {', '.join(changes[key])}")
    else:
        print("\n현재 설정이 프로젝트 구조 및 스킬 카탈로그와 일치합니다.")


def command_configure(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    current = load_project_config(project, manifest)
    proposed = proposed_project_config(
        project,
        manifest,
        existing=current,
        enable=args.enable,
        disable=args.disable,
    )
    reject_sensitive_config(proposed)
    changes = config_changes(current, proposed)
    if args.format != "json":
        print_config_report(project, current, proposed, changes)
    if not args.apply:
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "project": str(project),
                        "applied": False,
                        "changes": changes,
                        "config": proposed,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print("\n검사만 수행했습니다. 확인 후 --apply를 사용하면 설정을 저장합니다.")
        return 0

    destination = project_config_path(project)
    atomic_write(destination, json.dumps(proposed, ensure_ascii=False, indent=2) + "\n")
    root, created = ensure_history(project, manifest)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "project": str(project),
                    "applied": True,
                    "changes": changes,
                    "config": proposed,
                    "config_path": str(destination),
                    "history_root": str(root),
                    "history_created": created,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_created_notice(created)
        print(f"GENIE_CONFIG={destination}")
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
    config = load_project_config(project, manifest, required=True)
    assert config is not None
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    payload = load_payload(args.payload)

    if not payload.get("skill"):
        raise ValueError("Payload field 'skill' is required")
    skill = skill_lookup(manifest, str(payload["skill"]))
    if skill["id"] not in config["enabled_skills"]:
        raise ValueError(
            f"{skill['id']} is not enabled for this project. "
            "Run '지니 프로젝트 설정' to review the active skill set."
        )
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
config_profile: {yaml_value(config.get('profile', 'custom'))}
config_fingerprint: {yaml_value(config.get('structure_fingerprint', 'unknown'))}
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


def freshness_state(
    project: Path,
    current_commit: str,
    skill: dict[str, Any],
    record: dict[str, Any] | None,
    config: dict[str, Any],
) -> str:
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
    files = changed_files(project, recorded_commit)
    if files is None:
        return "stale"
    patterns = list(
        (config.get("skill_paths") or {}).get(skill["id"])
        or skill.get("invalidated_by")
        or []
    )
    return "stale" if any(matches_any(path, patterns) for path in files) else "current"


def status_rows(
    project: Path,
    manifest: dict[str, Any],
    config: dict[str, Any],
    selected: str | None = None,
) -> list[dict[str, Any]]:
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    _, current_commit = git_context(project)
    rows = []
    enabled = set(config["enabled_skills"])
    wanted = skill_lookup(manifest, selected) if selected else None
    if wanted and wanted["id"] not in enabled:
        raise ValueError(
            f"{wanted['id']} is not enabled for profile {config.get('profile', 'custom')}. "
            "Run '지니 프로젝트 설정' to change the active skill set."
        )
    for skill in sorted(manifest["skills"], key=lambda item: item["order"]):
        if skill["id"] not in enabled:
            continue
        if wanted and skill["id"] != wanted["id"]:
            continue
        record = latest_record(root, skill)
        rows.append(
            {
                "stage": skill["stage"],
                "skill": skill["id"],
                "description": skill["description"],
                "last_run": record.get("finished_at", "-") if record else "-",
                "result": record.get("status", "-") if record else "-",
                "freshness": freshness_state(project, current_commit, skill, record, config),
                "work_item": record.get("work_item", "-") if record else "-",
                "required_by_default": skill["id"] in set(config.get("required_skills", [])),
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
    config = load_project_config(project, manifest)
    if config is None:
        print_setup_required(project)
        print(
            "다음: 프로젝트 구조를 검사한 뒤 configure --apply로 "
            ".genie/config.json을 생성하세요."
        )
        return 0
    rows = status_rows(project, manifest, config, args.skill)
    proposed = proposed_project_config(project, manifest, existing=config)
    changes = config_changes(config, proposed)
    config_drift = (
        config.get("_source_schema_version") is not None
        or config.get("structure_fingerprint") != proposed.get("structure_fingerprint")
        or config.get("catalog_version") != manifest.get("catalog_version", 1)
        or any(changes.values())
    )
    if args.format == "json":
        print(
            json.dumps(
                {
                    "profile": config.get("profile"),
                    "config_drift": config_drift,
                    "changes": changes,
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(
        f"Genie 프로필: {config.get('profile', 'custom')} "
        f"({len(config['enabled_skills'])}개 활성 스킬)"
    )
    if config_drift:
        print(
            "설정 점검 필요: 프로젝트 구조 또는 Genie 카탈로그가 변경됐습니다. "
            "'지니 프로젝트 설정'으로 다시 확인하세요.\n"
        )
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
        selected_state = rows[0]["freshness"] if rows else "unknown"
        if selected_state in {"current", "not-applicable"}:
            print("\n선택한 스킬의 최신 기록은 현재 유효합니다.")
        else:
            print(f"\n선택한 스킬 상태: {selected_state}")
    else:
        print("\n기본 필수 단계는 현재 기록 기준으로 유효합니다. 조건부 단계를 범위에 맞게 검토하세요.")
    return 0


def command_history(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    project = resolve_project(args.project)
    config = load_project_config(project, manifest)
    if config is None:
        print_setup_required(project)
        return 0
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
    config = load_project_config(project, manifest, required=True)
    assert config is not None
    deploy_skill = skill_lookup(manifest, "project-deploy")
    if deploy_skill["id"] not in config["enabled_skills"]:
        raise ValueError(
            "genie-project-deploy is not enabled for this project. "
            "Run '지니 프로젝트 설정' first."
        )
    root, created = ensure_history(project, manifest)
    print_created_notice(created)
    config = load_payload(args.payload)
    reject_sensitive_config(config)
    config["schema_version"] = 1
    config["updated_at"] = now_local().isoformat(timespec="seconds")
    destination = project / PROJECT_CONFIG_DIR / "deploy.json"
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
    expected_workers = int(manifest.get("worker_count", len(ids)))
    if len(ids) != expected_workers:
        errors.append(f"Expected {expected_workers} worker skills, found {len(ids)}")
    if len(ids) != len(set(ids)):
        errors.append("Duplicate worker skill ids")
    if not (GENIE_ROOT / "SKILL.md").exists():
        errors.append("Missing Genie orchestrator SKILL.md")
    if not (GENIE_ROOT / "references" / "project-config.md").exists():
        errors.append("Missing project config reference")
    for skill_id in ids:
        skill_file = GENIE_ROOT / "skills" / str(skill_id) / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"Missing worker skill: {skill_file}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Genie doctor: OK (1 orchestrator, {len(ids)} workers)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genie development workflow history helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="Initialize docs/genie after project configuration exists"
    )
    init_parser.add_argument("--project")
    init_parser.set_defaults(func=command_init)

    configure_parser = subparsers.add_parser(
        "configure", help="Detect project structure and propose or apply Genie configuration"
    )
    configure_parser.add_argument("--project")
    configure_parser.add_argument("--apply", action="store_true")
    configure_parser.add_argument("--enable", action="append", default=[])
    configure_parser.add_argument("--disable", action="append", default=[])
    configure_parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown"
    )
    configure_parser.set_defaults(func=command_configure)

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
