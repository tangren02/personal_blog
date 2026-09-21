from __future__ import annotations

import argparse
import sys

from .build import BuildError, build_site, check_site


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m generator")
    parser.add_argument("command", choices=("build", "check"))
    args = parser.parse_args()

    try:
        if args.command == "build":
            result = build_site()
            print(f"built {result.entry_count} entry(ies) into {result.dist_dir}")
        else:
            result = check_site()
            print(
                f"checked {result.html_count} HTML file(s), "
                f"{result.link_count} local link(s), no errors"
            )
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
