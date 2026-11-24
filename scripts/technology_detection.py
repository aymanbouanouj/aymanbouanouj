"""Recognize technologies from trusted types of public repository evidence."""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from engineering import FRAMEWORKS, dependency_names
from live_portfolio import FRAMEWORK_DEPENDENCIES

DEPENDENCIES = {
    **FRAMEWORKS, **FRAMEWORK_DEPENDENCIES, "php": "PHP", "typescript": "TypeScript",
    "playwright": "Playwright", "@biomejs/biome": "Biome", "eslint": "ESLint",
    "prettier": "Prettier", "webpack": "webpack", "rollup": "Rollup",
    "pytest": "pytest", "pestphp/pest": "Pest", "djangorestframework": "Django REST Framework",
}
PYTHON_PACKAGES = {key: DEPENDENCIES[key] for key in ("fastapi", "flask", "django", "pytest", "djangorestframework")}
COMPOSER_PACKAGES = {key: DEPENDENCIES[key] for key in (
    "php", "laravel/framework", "laravel/sanctum", "symfony/framework-bundle", "codeigniter4/framework",
    "livewire/livewire", "inertiajs/inertia-laravel", "phpunit/phpunit", "pestphp/pest",
)}
NODE_PACKAGES = {key: label for key, label in DEPENDENCIES.items()
                 if key not in PYTHON_PACKAGES and key not in COMPOSER_PACKAGES}
PACKAGE_RULES = {"package.json": NODE_PACKAGES, "composer.json": COMPOSER_PACKAGES,
                 "requirements.txt": PYTHON_PACKAGES, "pyproject.toml": PYTHON_PACKAGES}
MANAGERS = {"npm": "npm", "pnpm": "pnpm", "yarn": "Yarn", "bun": "Bun"}
LOCKFILES = {
    "package-lock.json": "npm", "npm-shrinkwrap.json": "npm", "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn", "bun.lock": "Bun", "bun.lockb": "Bun", "composer.lock": "Composer",
    "poetry.lock": "Poetry", "uv.lock": "uv", "pdm.lock": "PDM", "Pipfile.lock": "Pipenv",
}
DATABASES = {"mysql": "MySQL", "mysql2": "MySQL", "mariadb": "MariaDB", "pg": "PostgreSQL",
             "pgsql": "PostgreSQL", "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
             "sqlite": "SQLite", "sqlite3": "SQLite", "sqlsrv": "SQL Server", "mongodb": "MongoDB"}
DATABASE_EXAMPLES = {".env.example", ".env.sample", ".env.template", "database.yml.example", "database.yaml.example"}
MANIFESTS = {"package.json", "composer.json", "requirements.txt", "pyproject.toml", "Pipfile",
             "go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle", "build.gradle.kts"}
WORKFLOW_LABELS = {"GitHub Actions", "Node.js", "Python", "Go", "Docker", "pnpm"}
CI_FILES = {".gitlab-ci.yml": "GitLab CI", ".circleci/config.yml": "CircleCI", "azure-pipelines.yml": "Azure Pipelines"}
MANIFEST_LABELS = {
    "package.json": {*NODE_PACKAGES.values(), *MANAGERS.values(), "Node.js"},
    "composer.json": {*COMPOSER_PACKAGES.values(), "Composer"},
    "requirements.txt": set(PYTHON_PACKAGES.values()),
    "pyproject.toml": {*PYTHON_PACKAGES.values(), "Python", "Poetry", "uv", "PDM"},
    "Pipfile": {*PYTHON_PACKAGES.values(), "Pipenv", "Python"},
    "go.mod": {"Go"}, "Cargo.toml": {"Rust", "Cargo"}, "Gemfile": {"Ruby", "Bundler", "Rails"},
    "pom.xml": {"Maven"}, "build.gradle": {"Gradle"}, "build.gradle.kts": {"Gradle"},
}
IGNORED_DIRS = {".git", "node_modules", "vendor", ".venv", "site-packages", "dist", "fixtures", "testdata"}
LABEL = re.compile(r"[\w+.#][\w +.#/&'’()*:,@-]{0,69}")


def safe_label(label) -> bool:
    return isinstance(label, str) and label == label.strip() and LABEL.fullmatch(label) is not None


def evidence_kind(path: str) -> str | None:
    parts = path.split("/")
    if (len(path) > 240 or "\\" in path or any(part in {"", ".", ".."} for part in parts)
            or any(ord(ch) < 32 for ch in path) or IGNORED_DIRS.intersection(p.lower() for p in parts[:-1])):
        return None
    name = parts[-1]
    if name in LOCKFILES:
        return "lock"
    if name in MANIFESTS:
        return "manifest"
    if name in DATABASE_EXAMPLES:
        return "database"
    if re.fullmatch(r"Dockerfile(?:\.[\w.-]+)?|[\w.-]+\.Dockerfile", name):
        return "dockerfile"
    if re.fullmatch(r"(?:docker-)?compose(?:\.[\w.-]+)?\.ya?ml", name):
        return "compose"
    if re.fullmatch(r"\.github/workflows/[-\w.]+\.ya?ml", path):
        return "github"
    if path in CI_FILES:
        return "ci"
    return None


def file_labels(path: str) -> set[str]:
    kind = evidence_kind(path)
    name = PurePosixPath(path).name
    if kind == "manifest":
        return MANIFEST_LABELS[name]
    if kind == "lock":
        return {LOCKFILES[name]}
    if kind == "database":
        return set(DATABASES.values())
    if kind == "ci":
        return {CI_FILES[path]}
    return {"dockerfile": {"Docker"}, "compose": {"Docker", "Docker Compose"}, "github": WORKFLOW_LABELS}.get(kind, set())


def container_service(text: str, *, compose=False) -> bool:
    for services in re.finditer(r"(?m)^( *)services:[ \t]*(?:#.*)?$", text):
        indent = len(services[1])
        for line in text[services.end():].splitlines():
            value = line.lstrip(" ")
            if not value or value.startswith("#"):
                continue
            if len(line) - len(value) <= indent:
                break
            if re.fullmatch(r"image:[ \t]+['\"]?[\w./-]+(?::[\w.-]+)?['\"]?[ \t]*(?:#.*)?", value):
                return True
            if compose and re.match(r"build:[ \t]*(?:\S|$)", value):
                return True
    return False


def manifest_technologies(name: str, text: str) -> set[str]:
    if name in {"package.json", "composer.json", "requirements.txt", "pyproject.toml"}:
        declared = dependency_names(name, text)
        rules = PACKAGE_RULES[name]
        detected = {rules[dep] for dep in declared if dep in rules}
        if name == "composer.json":
            metadata = json.loads(text)
            dev = metadata.get("require-dev", {})
            if not isinstance(dev, dict):
                raise ValueError("Invalid Composer development dependencies")
            return detected | {"Composer"} | {rules[d.lower()] for d in dev if d.lower() in rules}
        if name == "package.json":
            metadata = json.loads(text)
            engines = metadata.get("engines")
            if isinstance(engines, dict) and isinstance(engines.get("node"), str) and engines["node"].strip():
                detected.add("Node.js")
            manager = metadata.get("packageManager")
            if isinstance(manager, str) and (match := re.fullmatch(r"(npm|pnpm|yarn|bun)@\d[^\s]*", manager)):
                detected.add(MANAGERS[match[1]])
        if name == "pyproject.toml":
            config = tomllib.loads(text).get("tool", {})
            detected.update(label for key, label in (("poetry", "Poetry"), ("uv", "uv"), ("pdm", "PDM"))
                            if isinstance(config.get(key), dict))
            detected.add("Python")
        return detected
    if name == "Pipfile":
        document = tomllib.loads(text)
        regular, development = document.get("packages", {}), document.get("dev-packages", {})
        if not isinstance(regular, dict) or not isinstance(development, dict):
            raise ValueError("Invalid Pipfile dependency table")
        packages = regular.keys() | development.keys()
        return {"Pipenv", "Python"} | {PYTHON_PACKAGES[d.lower()] for d in packages if d.lower() in PYTHON_PACKAGES}
    if name == "go.mod":
        return {"Go"} if re.search(r"(?m)^module\s+\S+", text) else set()
    if name == "Cargo.toml":
        config = tomllib.loads(text)
        return {"Rust", "Cargo"} if {"package", "workspace"}.intersection(config) else set()
    if name == "Gemfile":
        gems = set(re.findall(r"(?m)^\s*gem[ \t]+['\"]([\w-]+)['\"]", text))
        result = {"Ruby", "Bundler"} if gems else set()
        return result | ({"Rails"} if "rails" in gems else set())
    if name == "pom.xml":
        if "<!DOCTYPE" in text.upper():
            raise ValueError("Unexpected document type in Maven manifest")
        return {"Maven"} if ET.fromstring(text).tag.rsplit("}", 1)[-1] == "project" else set()
    if name in {"build.gradle", "build.gradle.kts"}:
        return {"Gradle"} if re.search(r"(?m)^\s*(?:plugins|dependencies)\s*\{", text) else set()
    return set()


def detect(path: str, text: str) -> set[str]:
    kind = evidence_kind(path)
    name = PurePosixPath(path).name
    if kind == "manifest":
        return manifest_technologies(name, text)
    if kind == "database":
        adapters = re.findall(r"(?mi)^[ \t]*(?:DB_CONNECTION[ \t]*=|adapter[ \t]*:)[ \t]*"
                              r"['\"]?([\w]+)['\"]?[ \t]*(?:#.*)?$", text)
        return {DATABASES[adapter.lower()] for adapter in adapters if adapter.lower() in DATABASES}
    if kind == "dockerfile":
        return {"Docker"} if re.search(r"(?mi)^\s*FROM[ \t]+\S+", text) else set()
    if kind == "compose":
        return {"Docker", "Docker Compose"} if container_service(text, compose=True) else set()
    if kind == "github" and re.search(r"(?m)^jobs:[ \t]*(?:#.*)?$", text):
        setup = {"actions/setup-node": "Node.js", "actions/setup-python": "Python", "actions/setup-go": "Go",
                 "pnpm/action-setup": "pnpm"}
        uses = re.findall(r"(?m)^[ \t]*-?[ \t]*uses:[ \t]+['\"]?([\w.-]+/[\w.-]+)@", text)
        detected = {"GitHub Actions"} | {setup[action] for action in uses if action in setup}
        if container_service(text):
            detected.add("Docker")
        return detected
    if kind == "ci":
        if re.search(r"(?m)^(?:stages|jobs|workflows|steps|include):", text):
            return {CI_FILES[path]}
    return set()
