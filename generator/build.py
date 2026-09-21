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
SITE_CONFIG = CONTENT_DIR / "site.yaml"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
DIST_DIR = ROOT / "dist"

REQUIRED_FIELDS = ("kind", "status", "title", "slug", "summary", "updated", "order")
ALLOWED_KINDS = {"project", "knowledge", "research"}
ALLOWED_STATUSES = {"preparing", "active", "completed"}
KIND_PATHS = {"project": "projects", "knowledge": "knowledge", "research": "research"}


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
    for field in ("card_kicker", "card_script"):
        if field in metadata and not isinstance(metadata[field], str):
            raise BuildError(f"{path}: {field} must be a string")


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


def _load_site_config() -> dict:
    if not SITE_CONFIG.exists():
        raise BuildError(f"site config is missing: {SITE_CONFIG}")
    try:
        config = yaml.safe_load(SITE_CONFIG.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise BuildError(f"{SITE_CONFIG}: invalid YAML ({exc})") from exc
    if not isinstance(config, dict) or not isinstance(config.get("site"), dict):
        raise BuildError(f"{SITE_CONFIG}: site must be a mapping")
    tracks = config.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise BuildError(f"{SITE_CONFIG}: tracks must be a non-empty list")
    required = {"id", "kind", "title", "route", "theme", "number", "tag"}
    seen_ids: set[str] = set()
    seen_kinds: set[str] = set()
    seen_routes: set[str] = set()
    for track in tracks:
        if not isinstance(track, dict) or not required.issubset(track):
            raise BuildError(f"{SITE_CONFIG}: each track needs {sorted(required)}")
        if track["id"] in seen_ids:
            raise BuildError(f"{SITE_CONFIG}: duplicate track id {track['id']}")
        if track["route"] in seen_routes:
            raise BuildError(f"{SITE_CONFIG}: duplicate track route {track['route']}")
        if track["kind"] not in ALLOWED_KINDS:
            raise BuildError(f"{SITE_CONFIG}: track kind must be one of {sorted(ALLOWED_KINDS)}")
        if track["kind"] in seen_kinds:
            raise BuildError(f"{SITE_CONFIG}: duplicate track kind {track['kind']}")
        seen_ids.add(track["id"])
        seen_kinds.add(track["kind"])
        seen_routes.add(track["route"])
    missing_kinds = ALLOWED_KINDS - seen_kinds
    if missing_kinds:
        raise BuildError(f"{SITE_CONFIG}: missing track kind(s): {sorted(missing_kinds)}")
    for key in ("home", "knowledge_index"):
        if not isinstance(config.get(key), dict):
            raise BuildError(f"{SITE_CONFIG}: {key} must be a mapping")
    return config


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        undefined=StrictUndefined,
    )


def _render_entry(environment: Environment, entry: Entry, site: dict) -> str:
    body_html = markdown.markdown(
        entry.body,
        extensions=["fenced_code", "tables", "attr_list"],
        output_format="html5",
    )
    template_name = "project.html" if entry.metadata["kind"] == "project" else "entry.html"
    template = environment.get_template(template_name)
    page = {
        "title": entry.metadata["title"],
        "title_tag": entry.metadata["title"],
        "description": entry.metadata["summary"],
        "active_nav": "projects" if entry.metadata["kind"] == "project" else "knowledge",
        "body_class": "project-page" if entry.metadata["kind"] == "project" else "entry-page",
        "footer_route": "/knowledge/projects/" if entry.metadata["kind"] == "project" else "/knowledge/",
        "footer_label": "← 返回项目记录" if entry.metadata["kind"] == "project" else "← 返回知识学习",
        "footer_right": f"{entry.metadata['slug']} · generated",
    }
    return template.render(
        site=site,
        page=page,
        entry=entry.metadata,
        body_html=body_html,
    )


def _decorate_tracks(config: dict, entries: list[Entry]) -> list[dict]:
    tracks = []
    for raw_track in config["tracks"]:
        track = dict(raw_track)
        track["entries"] = [entry for entry in entries if entry.metadata["kind"] == track["kind"]]
        track["count_label"] = f"{len(track['entries'])} 个条目" if track["entries"] else "准备中"
        tracks.append(track)
    return tracks


def _write_route(route: str, html: str) -> None:
    output = DIST_DIR / route.strip("/") / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def _render_site_pages(environment: Environment, config: dict, entries: list[Entry]) -> None:
    site = config["site"]
    tracks = _decorate_tracks(config, entries)
    home_page = {
        "title": "首页",
        "title_tag": f"{site['name']} · 首页",
        "description": site["description"],
        "active_nav": "home",
        "body_class": "home-page",
    }
    _write_route("/", environment.get_template("home.html").render(site=site, page=home_page, home=config["home"], tracks=tracks, action_context="home"))

    overview = config["knowledge_index"]
    overview_page = {
        "title": "知识学习",
        "title_tag": f"知识学习 · {site['name']}",
        "description": site["description"],
        "active_nav": "knowledge",
        "body_class": "category-page",
        "footer_route": "/",
        "footer_label": "← 返回首页",
        "footer_right": "知识学习 · index",
    }
    _write_route("/knowledge/", environment.get_template("knowledge_index.html").render(site=site, page=overview_page, overview=overview, tracks=tracks, action_context="overview"))

    for track in tracks:
        page = {
            "title": track["title"],
            "title_tag": f"{track['title']} · {site['name']}",
            "description": track["category_lede"],
            "active_nav": "projects" if track["kind"] == "project" else "knowledge",
            "body_class": "category-page",
            "footer_route": "/knowledge/",
            "footer_label": "← 返回知识学习",
            "footer_right": f"{track['title']} · index",
        }
        _write_route(track["route"], environment.get_template("category.html").render(site=site, page=page, track=track))


def build_site() -> BuildResult:
    config = _load_site_config()
    entries = _load_entries()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for child in DIST_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(ASSETS_DIR, DIST_DIR / "assets")

    environment = _environment()
    _render_site_pages(environment, config, entries)
    for entry in entries:
        output = entry.output_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_render_entry(environment, entry, config["site"]), encoding="utf-8")
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
