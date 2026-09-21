# Agent instructions for personal_blog

## Project boundary

This repository is a private, local-first learning site. Keep technical learning, project records, and research records as separate content directions. Markdown entries and their front matter are the content source; `content/site.yaml` holds site-map and direction-level copy; `dist/` is generated output and is never an editing source.

Preserve the existing visual language unless the user explicitly requests a redesign. HString documents a completed historical project. Keep its GitHub source snapshot and implementation limitations accurate; do not turn it into a repair or continuation project.

## Branch policy

- `develop` is the local development branch. Make code, content, template, and documentation changes here.
- `main` is the stable branch allowed to publish to the website. Deploy only from a clean `main` checkout.
- Do not deploy `develop` directly.
- When the current effect is stable, finish validation on `develop`, commit the intended changes, merge `develop` into `main`, and publish from `main`.
- After a successful publish and remote verification, return the local checkout to `develop` for continued development.
- Preserve unrelated or uncommitted work. Inspect `git status` before branch changes and never reset, clean, or discard it implicitly.

## Local validation before release

From the repository root, run all of the following on `develop` before merging:

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m generator check
.venv/bin/python -m compileall -q generator tests
git diff --check
```

The release candidate must generate the five site routes and the HString detail route, pass local-link checks, and preserve the generated visual structure. Start a local server and inspect the pages when a template or CSS change affects layout.

## Website release process

The server hosts generated artifacts, not a Git checkout. GitHub and the local repository are the source of truth. Build `dist/` from the clean stable `main` commit, then upload the generated files over the configured SSH alias `fund` (`fund@124.221.116.78`).

Use a new immutable release directory on the server:

```text
/srv/personal-blog/releases/<release-id>/
/srv/personal-blog/current -> /srv/personal-blog/releases/<release-id>
```

After uploading and setting `current`, configure Caddy to serve `/srv/personal-blog/current` for `ljjfund.online`, validate the Caddyfile, reload Caddy, and verify HTTPS responses for `/`, `/knowledge/`, `/knowledge/projects/`, and `/projects/hstring/`. Keep prior release directories for rollback. Back up `/etc/caddy/Caddyfile` before changing it.

The deployment is a static artifact transfer; it does not push to GitHub, clone GitHub onto the server, or require Python dependencies on the server. If automated deployment is added later, GitHub Actions should build and validate `dist/`, upload a versioned artifact over SSH, switch `current`, and verify HTTPS before reporting success.

Do not delete Fund System data volumes or old releases as part of a blog deployment. If Fund System is stopped, keep its database volume and release history intact unless the user separately authorizes cleanup.

## Completion report

Report the source commit, release directory, active `current` target, validation commands, HTTP/HTTPS verification, and any preserved rollback or backup path. State clearly whether the release came from committed `main` or from an uncommitted working tree.
