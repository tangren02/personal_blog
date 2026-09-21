from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
from urllib.parse import urldefrag, urlparse

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
DIST_DIR = ROOT / "dist"

REQUIRED_FIELDS = ("kind", "status", "title", "slug", "summary", "updated", "order")
ALLOWED_KINDS = {"project", "knowledge", "research"}
ALLOWED_STATUSES = {"preparing", "active", "completed"}
KIND_PATHS = {"project": "projects", "knowledge": "knowledge", "research": "research"}
LEGACY_PAGES = (
    "index.html",
    "knowledge/index.html",
    "knowledge/programming-knowledge/index.html",
    "knowledge/projects/index.html",
    "knowledge/research/index.html",
)


class BuildError(RuntimeError):
    """A user-facing build or validation error."""


@dataclass(frozen=True)
class Entry:
    source: Path
    metadata: dict
    body: str

    @property
    def route(self) -> str:
        return f"/{KIND_PATHS[self.metadata['kind']]}/{self.metadata['slug']}/"

    @property
    def output_path(self) -> Path:
        return DIST_DIR / self.route.strip("/") / "index.html"


@dataclass(frozen=True)
class BuildResult:
    dist_dir: Path
    entry_count: int


@dataclass(frozen=True)
class CheckResult:
    html_count: int
    link_count: int


def _read_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise BuildError(f"{path}: missing front matter")
    try:
        _, front_matter, body = text.split("---\n", 2)
    except ValueError as exc:
        raise BuildError(f"{path}: malformed front matter") from exc
    metadata = yaml.safe_load(front_matter) or {}
    if not isinstance(metadata, dict):
        raise BuildError(f"{path}: front matter must be a mapping")
    return metadata, body.lstrip()


def _validate_metadata(path: Path, metadata: dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    if missing:
        raise BuildError(f"{path}: missing required field(s): {', '.join(missing)}")
    if metadata["kind"] not in ALLOWED_KINDS:
        raise BuildError(f"{path}: kind must be one of {sorted(ALLOWED_KINDS)}")
    if metadata["status"] not in ALLOWED_STATUSES:
        raise BuildError(f"{path}: status must be one of {sorted(ALLOWED_STATUSES)}")
    if not isinstance(metadata["order"], int):
        raise BuildError(f"{path}: order must be an integer")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(metadata["slug"])):
        raise BuildError(f"{path}: slug must use lowercase kebab-case")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(metadata["updated"])):
        raise BuildError(f"{path}: updated must use YYYY-MM-DD")
    if not isinstance(metadata["title"], str) or not metadata["title"].strip():
        raise BuildError(f"{path}: title must be a non-empty string")
    if not isinstance(metadata["summary"], str) or not metadata["summary"].strip():
        raise BuildError(f"{path}: summary must be a non-empty string")


class ContentHTMLPolicy(HTMLParser):
    """Reject executable or externally embedded HTML in Markdown content."""

    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "iframe", "object", "embed"}:
            self.errors.append(f"{self.source}: <{lowered}> is not allowed in content")
        for name, value in attrs:
            if name.lower().startswith("on"):
                self.errors.append(f"{self.source}: event attribute {name} is not allowed")
            if name.lower() in {"src", "srcset"} and value:
                resource = urlparse(value)
                if resource.scheme or resource.netloc or value.startswith("//"):
                    self.errors.append(f"{self.source}: external resource {value} is not allowed")


def _load_entries() -> list[Entry]:
    entries: list[Entry] = []
    seen_routes: set[str] = set()
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        metadata, body = _read_markdown(path)
        _validate_metadata(path, metadata)
        policy = ContentHTMLPolicy(path)
        policy.feed(body)
        if policy.errors:
            raise BuildError("\n".join(policy.errors))
        entry = Entry(path, metadata, body)
        if entry.route in seen_routes:
            raise BuildError(f"duplicate route: {entry.route}")
        seen_routes.add(entry.route)
        entries.append(entry)
    return sorted(entries, key=lambda item: (item.metadata["kind"], item.metadata["order"], item.metadata["title"]))


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        undefined=StrictUndefined,
    )


def _render_entry(environment: Environment, entry: Entry) -> str:
    body_html = markdown.markdown(
        entry.body,
        extensions=["fenced_code", "tables", "attr_list"],
        output_format="html5",
    )
    template_name = "project.html" if entry.metadata["kind"] == "project" else "entry.html"
    template = environment.get_template(template_name)
    return template.render(
        site={"name": "个人学习图谱"},
        entry=entry.metadata,
        body_html=body_html,
    )


def _copy_legacy_pages() -> None:
    for relative in LEGACY_PAGES:
        source = ROOT / relative
        if not source.exists():
            raise BuildError(f"legacy page is missing: {source}")
        destination = DIST_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build_site() -> BuildResult:
    entries = _load_entries()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for child in DIST_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(ASSETS_DIR, DIST_DIR / "assets")
    _copy_legacy_pages()

    environment = _environment()
    for entry in entries:
        output = entry.output_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_render_entry(environment, entry), encoding="utf-8")
    return BuildResult(DIST_DIR, len(entries))


class DocumentStructure(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag.lower())
        for name, value in attrs:
            if name.lower() in {"href", "src"} and value:
                self.links.append(value)


def _resolve_local_link(document: Path, raw_link: str) -> Path | None:
    link, _ = urldefrag(raw_link)
    parsed = urlparse(link)
    if not link or parsed.scheme or parsed.netloc or link.startswith("mailto:"):
        return None
    link = parsed.path
    if link.startswith("/"):
        target = DIST_DIR / link.lstrip("/")
    else:
        target = document.parent / link
    if target.suffix == "" or target.name == "":
        target = target / "index.html"
    return target


def check_site() -> CheckResult:
    build_site()
    html_files = sorted(DIST_DIR.rglob("*.html"))
    errors: list[str] = []
    link_count = 0
    for path in html_files:
        parser = DocumentStructure()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - parser errors are input-specific
            errors.append(f"{path}: invalid HTML ({exc})")
            continue
        if not {"html", "head", "body"}.issubset(parser.tags):
            errors.append(f"{path}: missing basic HTML structure")
        for raw_link in parser.links:
            target = _resolve_local_link(path, raw_link)
            if target is None:
                continue
            link_count += 1
            if not target.exists():
                errors.append(f"{path}: missing local link target {raw_link}")
    if errors:
        raise BuildError("\n".join(errors))
    return CheckResult(len(html_files), link_count)
