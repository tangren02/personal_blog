# Adopt a Markdown-first static generation pipeline

The site currently maintains complete pages as hand-written HTML, which makes content changes repeat navigation and layout structure. The upgrade will make Markdown with front matter the canonical content source, use reusable templates plus a small Python static generator to produce the site, and write build output to a separate `dist/` directory for local preview and later publishing. Generated entries will use clean URLs such as `/projects/hstring/`; backward compatibility with the current `.html` paths is not a requirement. The first vertical slice will migrate HString before the home and category pages, while trusted Markdown may retain controlled HTML for its existing learning diagrams.

## Considered Options

- Keep hand-written HTML and add Markdown only for new entries.
- Use a heavier frontend framework and runtime.
- Use a small Python-based generator with Markdown and templates.

The small generator matches the local-first learning goal and keeps the content-to-output data flow inspectable. Separating `dist/` makes the generated files reviewable and replaceable without turning them into the editing source.

The build will validate required front matter, local links and resources, and basic HTML structure before the generated output is previewed over HTTP. Existing hand-written pages stay available as a comparison during migration and are removed only after the home and category pages also come from the pipeline.

Category pages will discover entries from front matter and use an explicit `order`; each entry will provide a stable `slug` that is independent of its source filename. The site map and the copy that describes the three learning directions live in a small site-level data source, while entry bodies and entry metadata remain Markdown. Reusable templates render the home page, knowledge index, and all three category pages; empty categories use a shared empty-state block instead of placeholder entries. The build copies shared assets unchanged, keeps theme-candidate pages outside the main build, and places only publishable HTML and assets in `dist/`. Legacy HTML pages are no longer copied once their generated replacements pass the same structural and link checks.
