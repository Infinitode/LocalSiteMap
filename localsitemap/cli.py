"""Command line interface for LocalSiteMap.

Usage::

    localsitemap path/to/website https://example.com -o public/sitemap.xml
    python -m localsitemap path/to/website https://example.com --exclude auth
"""

import argparse
import json
import sys

from . import __version__, generate_sitemap


def _comma_separated(value):
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="localsitemap",
        description=(
            "Generate a sitemap (and sitemap index when needed) from a local "
            "directory that mirrors a website."
        ),
    )
    parser.add_argument("root_path", help="root directory of the website")
    parser.add_argument(
        "base_url",
        help="public base URL of the website, e.g. https://example.com",
    )
    parser.add_argument(
        "-o", "--output", default="sitemap.xml",
        help="sitemap file to write (default: sitemap.xml)",
    )
    parser.add_argument(
        "-e", "--exclude", action="append", default=[], metavar="PATTERN",
        help=(
            "name, relative/absolute path or glob pattern to exclude; "
            "repeat for multiple exclusions"
        ),
    )
    parser.add_argument(
        "--extensions", default=".html,.htm", metavar="LIST",
        help="comma separated extensions to include (default: .html,.htm)",
    )
    parser.add_argument(
        "--default-priority", type=float, default=0.80,
        help="priority used when no mapping matches (default: 0.80)",
    )
    parser.add_argument(
        "--homepage-priority", type=float, default=1.00,
        help="priority for the site root (default: 1.00)",
    )
    parser.add_argument(
        "--max-urls", type=int, default=50000,
        help="maximum URLs per sitemap file before splitting (default: 50000)",
    )
    parser.add_argument(
        "--priority-map", metavar="FILE",
        help="JSON file containing a priority mapping object",
    )
    parser.add_argument(
        "--exclude-hidden", action="store_true",
        help="skip files and folders whose name starts with a dot",
    )
    parser.add_argument(
        "--no-homepage", action="store_true",
        help="do not emit the site root URL",
    )
    parser.add_argument(
        "--no-sort", action="store_true",
        help="keep filesystem order instead of sorting URLs",
    )
    parser.add_argument(
        "-p", "--progress", action="store_true",
        help="print the traversal progress",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__,
    )
    return parser


def _load_priority_map(parser, path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            mapping = json.load(handle)
    except OSError as error:
        parser.error("could not read priority map %s: %s" % (path, error))
    except ValueError as error:
        parser.error("priority map %s is not valid JSON: %s" % (path, error))
    if not isinstance(mapping, dict):
        parser.error("priority map %s must contain a JSON object" % path)
    return mapping


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    priority_mapping = None
    if args.priority_map:
        priority_mapping = _load_priority_map(parser, args.priority_map)

    try:
        created = generate_sitemap(
            root_path=args.root_path,
            base_url=args.base_url,
            output_file=args.output,
            excluded_paths=args.exclude,
            show_progress=args.progress,
            allowed_extensions=_comma_separated(args.extensions),
            default_priority=args.default_priority,
            homepage_priority=args.homepage_priority,
            priority_mapping=priority_mapping,
            max_urls=args.max_urls,
            exclude_hidden=args.exclude_hidden,
            include_homepage=not args.no_homepage,
            sort_entries=not args.no_sort,
        )
    except (OSError, ValueError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    for path in created:
        print("Wrote %s" % path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
