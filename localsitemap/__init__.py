"""LocalSiteMap - generate standard-compliant sitemaps from local files.

The package crawls a directory tree that mirrors a website and writes a
``sitemap.xml`` file (or a set of numbered sitemaps plus a ``sitemapindex``
when the URL limit is exceeded).

Only the Python standard library is used, so the package has no runtime
dependencies.
"""

import datetime
import fnmatch
import math
import os
import re
import tempfile
import warnings
from urllib.parse import quote

from ._version import __version__

__all__ = [
    "__version__",
    "generate_sitemap",
    "get_priority",
    "get_utc_lastmod",
    "is_excluded",
    "write_sitemap_file",
    "write_sitemap_index_file",
]

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SITEMAP_SCHEMA = SITEMAP_NS + "/sitemap.xsd"

#: Hard limit enforced by the sitemap protocol (and Google) per sitemap file.
MAX_URLS_PER_SITEMAP = 50000

DEFAULT_EXTENSIONS = (".html", ".htm")

_GLOB_CHARS = re.compile(r"[*?\[]")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _as_path_string(path):
    """Return *path* as a ``str`` (accepts ``os.PathLike`` objects)."""
    if hasattr(os, "fspath"):
        path = os.fspath(path)
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    return path


def _segment_matches(segment, pattern):
    """Compare one path segment with an exclusion pattern (glob aware)."""
    if _GLOB_CHARS.search(pattern):
        if fnmatch.fnmatchcase(segment, pattern):
            return True
        if _WINDOWS:
            return fnmatch.fnmatchcase(segment.lower(), pattern.lower())
        return False
    if _WINDOWS:
        return segment.lower() == pattern.lower()
    return segment == pattern


def _normalise_extension(extension):
    extension = str(extension).strip()
    if not extension:
        return ""
    if not extension.startswith("."):
        extension = "." + extension
    return extension.lower()


def _format_priority(value, default=None):
    """Format a priority in the ``0.00`` - ``1.00`` range used by sitemaps."""
    try:
        priority = float(value)
    except (TypeError, ValueError) as error:
        if default is None:
            raise ValueError(
                "priority values must be numbers, got %r" % (value,)
            ) from error
        priority = float(default)
    if math.isnan(priority):
        priority = float(default if default is not None else 0.5)
    # The sitemap protocol only allows values between 0.0 and 1.0.
    priority = min(1.0, max(0.0, priority))
    return "%.2f" % priority


def get_utc_lastmod(path):
    """Return the UTC modification time of *path* formatted for ``<lastmod>``.

    The value is an ISO-8601 date/time in UTC (``YYYY-MM-DDThh:mm:ss+00:00``).
    If the timestamp cannot be read (for example because the file vanished
    while the tree was being walked) the current UTC time is used instead.
    """
    try:
        mtime = os.path.getmtime(path)
        moment = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
    except (OSError, OverflowError, ValueError):
        moment = datetime.datetime.now(datetime.timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------

class _PathFilter(object):
    """Decides whether a path inside the site root is excluded.

    Rules are resolved relative to the site root, so an exclusion can never
    accidentally match a *parent* directory of the site (for example a site
    checked out in a folder called ``media`` while ``media`` is excluded).
    """

    def __init__(self, root_path, excluded_paths=None, exclude_hidden=False):
        self.root_path = os.path.abspath(_as_path_string(root_path))
        self.exclude_hidden = bool(exclude_hidden)
        if isinstance(excluded_paths, str):
            excluded_paths = [excluded_paths]
        self.rules = self._build_rules(excluded_paths or [])

    def _build_rules(self, excluded_paths):
        rules = []
        seen = set()
        for raw in excluded_paths:
            if raw is None:
                continue
            text = str(raw).strip()
            if not text:
                continue
            candidate = os.path.abspath(
                text if os.path.isabs(text)
                else os.path.join(self.root_path, text.replace("\\", "/"))
            )
            try:
                relative = os.path.relpath(candidate, self.root_path)
            except ValueError:  # pragma: no cover - different drives on Windows
                continue
            if relative == os.curdir:
                # Excluding the root itself is never useful: the site root is
                # always kept so the homepage is still emitted.
                continue
            parts = [part for part in relative.split(os.sep) if part not in ("", os.curdir)]
            if not parts or parts[0] == os.pardir:
                # Outside of the site root, therefore irrelevant.
                continue
            # A single relative name matches at any depth (e.g. "node_modules");
            # multi-segment patterns are anchored at the site root.
            anchor = len(parts) > 1 or os.path.isabs(text)
            key = (tuple(parts), anchor)
            if key in seen:
                continue
            seen.add(key)
            rules.append((parts, anchor))
        return rules

    def _segments(self, path):
        absolute = os.path.abspath(_as_path_string(path))
        try:
            relative = os.path.relpath(absolute, self.root_path)
        except ValueError:  # pragma: no cover - different drives on Windows
            return None
        if relative == os.curdir:
            return []
        parts = [part for part in relative.split(os.sep) if part not in ("", os.curdir)]
        if parts and parts[0] == os.pardir:
            return None
        return parts

    def excludes(self, path):
        segments = self._segments(path)
        if segments is None:
            return False
        if not segments:
            return False

        if self.exclude_hidden:
            for segment in segments:
                if segment.startswith("."):
                    return True

        for pattern, anchor in self.rules:
            if anchor:
                if len(segments) < len(pattern):
                    continue
                if all(
                    _segment_matches(segment, part)
                    for segment, part in zip(segments, pattern)
                ):
                    return True
            elif len(pattern) == 1:
                if any(_segment_matches(segment, pattern[0]) for segment in segments):
                    return True
        return False


def is_excluded(path, root_path, excluded_paths):
    """Return ``True`` when *path* should be skipped.

    ``path`` and ``root_path`` may be absolute or relative. Exclusions are
    interpreted relative to ``root_path``:

    * a plain name (``"node_modules"``) matches a file or folder with that
      name at any depth,
    * a relative path (``"blog/posts"``) matches that path and everything
      below it,
    * an absolute path matches only that path (and its contents) when it is
      inside ``root_path``,
    * shell-style wildcards (``"draft-*"``, ``"*.bak"``) are supported.
    """
    if not excluded_paths:
        return False
    return _PathFilter(root_path, excluded_paths).excludes(path)


# ---------------------------------------------------------------------------
# Priorities
# ---------------------------------------------------------------------------

def _normalise_priority_mapping(mapping):
    normalised = {}
    for key, value in mapping.items():
        if key is None:
            continue
        text = str(key).strip().replace("\\", "/").strip("/")
        if not text:
            continue
        normalised[text] = value
        if text.startswith(".") and "/" not in text:
            # Extension keys are matched case-insensitively.
            normalised.setdefault(text.lower(), value)
    return normalised


def _lookup_mapping_priority(mapping, relative_path, is_dir):
    """Look up ``relative_path`` in an already normalised mapping."""
    rel = str(relative_path).replace("\\", "/").strip("/")
    if not rel:
        return None, None
    basename = rel.rsplit("/", 1)[-1]
    _, extension = os.path.splitext(basename)
    candidates = [rel]
    if is_dir or not extension:
        candidates.append(rel + "/")
    candidates.extend([basename, extension])
    if extension:
        candidates.append(extension.lower())
        candidates.append(extension.lstrip(".").lower())
    for candidate in candidates:
        if candidate and candidate in mapping:
            return mapping[candidate], candidate
    return None, None


def _resolve_priority(relative_path, is_dir, default_priority, priority_mapping):
    """Resolve a priority; *priority_mapping* must already be normalised."""
    if priority_mapping:
        if callable(priority_mapping):
            value = None
            try:
                value = priority_mapping(relative_path, is_dir)
            except Exception:  # noqa: BLE001 - user supplied callables may fail
                value = None
            if value is not None:
                return _format_priority(value, default=default_priority)
        elif isinstance(priority_mapping, dict):
            value, _key = _lookup_mapping_priority(priority_mapping, relative_path, is_dir)
            if value is not None:
                return _format_priority(value, default=default_priority)
    return _format_priority(default_priority)


def get_priority(relative_path, is_dir, default_priority, priority_mapping=None):
    """Return the formatted priority for *relative_path*.

    ``priority_mapping`` may be a callable (``f(relative_path, is_dir)``) or a
    dict. Dict keys may be a relative path (``"about/index.html"``), a folder
    name, a file name, or an extension (``".php"``); folder keys may be
    written with or without a trailing slash and Windows separators are
    accepted. Priorities are clamped to the ``0.00`` - ``1.00`` range allowed
    by the sitemap protocol.
    """
    if isinstance(priority_mapping, dict):
        priority_mapping = _normalise_priority_mapping(priority_mapping)
    return _resolve_priority(relative_path, is_dir, default_priority, priority_mapping)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _normalise_base_url(base_url):
    base = str(base_url).strip()
    if not _SCHEME_RE.match(base):
        raise ValueError(
            "base_url must be an absolute URL including its scheme "
            "(for example 'https://example.com'), got %r" % (base_url,)
        )
    return base.rstrip("/")


def _quote_segment(segment):
    # ``quote`` never escapes unreserved characters, so "index.html" is left
    # untouched while spaces, "#", "&" and non-ASCII characters are encoded.
    return quote(segment, safe="")


def _url_for(base, relative_path, is_dir):
    """Build an absolute, percent-encoded URL for a relative filesystem path."""
    posix = str(relative_path).replace("\\", "/")
    parts = [part for part in posix.split("/") if part not in ("", ".")]
    encoded = "/".join(_quote_segment(part) for part in parts)
    if not encoded:
        return base
    url = base + "/" + encoded
    if is_dir:
        url += "/"
    return url


# ---------------------------------------------------------------------------
# XML writers
# ---------------------------------------------------------------------------

def _xml_escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _atomic_write(file_path, content):
    """Write *content* to *file_path* atomically (create parent directories)."""
    target = os.path.abspath(_as_path_string(file_path))
    directory = os.path.dirname(target) or os.curdir
    os.makedirs(directory, exist_ok=True)
    handle_fd, temporary = tempfile.mkstemp(
        prefix=".localsitemap-", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, target)
    except BaseException:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


def _render_urlset(entries):
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<urlset xmlns="%s" xmlns:xsi="%s" xsi:schemaLocation="%s %s">'
        % (SITEMAP_NS, XSI_NS, SITEMAP_NS, SITEMAP_SCHEMA),
    ]
    for entry in entries:
        lines.append("  <url>")
        lines.append("    <loc>%s</loc>" % _xml_escape(entry["loc"]))
        if entry.get("lastmod"):
            lines.append("    <lastmod>%s</lastmod>" % _xml_escape(entry["lastmod"]))
        if entry.get("priority") is not None:
            lines.append("    <priority>%s</priority>" % _xml_escape(entry["priority"]))
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _render_sitemapindex(sitemaps_info):
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<sitemapindex xmlns="%s">' % SITEMAP_NS,
    ]
    for info in sitemaps_info:
        lines.append("  <sitemap>")
        lines.append("    <loc>%s</loc>" % _xml_escape(info["loc"]))
        if info.get("lastmod"):
            lines.append("    <lastmod>%s</lastmod>" % _xml_escape(info["lastmod"]))
        lines.append("  </sitemap>")
    lines.append("</sitemapindex>")
    return "\n".join(lines) + "\n"


def write_sitemap_file(file_path, entries):
    """Write *entries* to *file_path* as a sitemap ``<urlset>``."""
    _atomic_write(file_path, _render_urlset(entries))


def write_sitemap_index_file(file_path, sitemaps_info):
    """Write *sitemaps_info* to *file_path* as a ``<sitemapindex>``."""
    _atomic_write(file_path, _render_sitemapindex(sitemaps_info))


# ---------------------------------------------------------------------------
# Sitemap generation
# ---------------------------------------------------------------------------

def _walk_entries(root_path, base_url, path_filter, extensions, priority_mapping,
                  default_priority, show_progress):
    entries = []
    seen_locations = set()

    def add(loc, source_path, is_dir, priority=None):
        if loc in seen_locations:
            return
        seen_locations.add(loc)
        entries.append({
            "loc": loc,
            "lastmod": get_utc_lastmod(source_path),
            "priority": priority if priority is not None else _resolve_priority(
                _relative_posix(source_path, root_path),
                is_dir=is_dir,
                default_priority=default_priority,
                priority_mapping=priority_mapping,
            ),
        })

    for current_root, dirnames, filenames in os.walk(root_path):
        # Keep the walk deterministic and prune excluded directories in place
        # so their contents are never visited.
        dirnames[:] = sorted(
            name for name in dirnames
            if not path_filter.excludes(os.path.join(current_root, name))
        )
        filenames = sorted(filenames)

        for dir_name in dirnames:
            full_path = os.path.join(current_root, dir_name)
            if show_progress:
                print("Mapping directory: %s" % full_path)
            add(_url_for(base_url, _relative_posix(full_path, root_path), is_dir=True),
                full_path, True)

        for file_name in filenames:
            full_path = os.path.join(current_root, file_name)
            if path_filter.excludes(full_path):
                continue
            if not _has_allowed_extension(file_name, extensions):
                continue
            if show_progress:
                print("Found file: %s" % full_path)
            add(_url_for(base_url, _relative_posix(full_path, root_path), is_dir=False),
                full_path, False)

    return entries


def _relative_posix(path, root_path):
    relative = os.path.relpath(path, root_path)
    return relative.replace(os.sep, "/")


def _has_allowed_extension(file_name, extensions):
    lowered = file_name.lower()
    return any(lowered.endswith(extension) for extension in extensions)


def _split_sitemaps(entries, output_file, base_url, max_urls, show_progress):
    """Write numbered sitemaps plus an index; return the created file paths."""
    output_file = _as_path_string(output_file)
    directory = os.path.dirname(output_file)
    base_name = os.path.basename(output_file)
    name, extension = os.path.splitext(base_name)

    part_count = int(math.ceil(len(entries) / float(max_urls)))
    created = []
    sitemaps_info = []

    for part_number in range(1, part_count + 1):
        chunk = entries[(part_number - 1) * max_urls:part_number * max_urls]
        part_filename = "%s_%d%s" % (name, part_number, extension)
        part_path = os.path.join(directory, part_filename) if directory else part_filename
        if show_progress:
            print("Saving split sitemap part %d to %s..." % (part_number, part_path))
        write_sitemap_file(part_path, chunk)
        created.append(part_path)
        sitemaps_info.append({
            "loc": base_url + "/" + _quote_segment(part_filename),
            "lastmod": get_utc_lastmod(part_path),
        })

    # Remove leftovers from a previous, larger run so stale sitemaps are not
    # left behind next to the freshly written index.
    stale_pattern = re.compile(r"^%s_([0-9]+)%s$" % (re.escape(name), re.escape(extension)))
    search_directory = directory or os.curdir
    if os.path.isdir(search_directory):
        for existing in sorted(os.listdir(search_directory)):
            match = stale_pattern.match(existing)
            if not match or int(match.group(1)) <= part_count:
                continue
            stale_path = os.path.join(search_directory, existing)
            try:
                os.remove(stale_path)
            except OSError:
                continue
            if show_progress:
                print("Removed stale sitemap part: %s" % stale_path)

    if show_progress:
        print("Saving sitemap index to %s..." % output_file)
    write_sitemap_index_file(output_file, sitemaps_info)
    created.append(output_file)
    return created


def generate_sitemap(
    root_path,
    base_url,
    output_file="sitemap.xml",
    excluded_paths=None,
    show_progress=False,
    allowed_extensions=None,
    default_priority=0.80,
    homepage_priority=1.00,
    priority_mapping=None,
    max_urls=50000,
    exclude_hidden=False,
    include_homepage=True,
    sort_entries=True,
):
    """Generate a sitemap for a local website directory.

    Parameters
    ----------
    root_path:
        Root directory of the website.
    base_url:
        Public base URL of the website (for example ``https://example.com``).
    output_file:
        Sitemap path to write. When the URL limit is exceeded numbered parts
        (``sitemap_1.xml``, ...) plus a ``sitemap.xml`` index are written.
    excluded_paths:
        File/folder names, relative paths, absolute paths or glob patterns to
        skip. Matching is relative to ``root_path``.
    show_progress:
        Print the traversal progress.
    allowed_extensions:
        Extensions to include (default: ``[".html", ".htm"]``). Matching is
        case-insensitive and the leading dot is optional.
    default_priority:
        Priority used when no mapping matches (default ``0.80``).
    homepage_priority:
        Priority for the site root (default ``1.00``).
    priority_mapping:
        Dict or callable mapping paths/folders/extensions to priorities.
    max_urls:
        Maximum number of URLs per sitemap file before splitting (max 50000).
    exclude_hidden:
        Skip files and folders starting with a dot.
    include_homepage:
        Emit the site root URL (default ``True``).
    sort_entries:
        Sort entries by URL for reproducible output (default ``True``).

    Returns
    -------
    list of str
        The paths that were written, in the order they were written. When the
        sitemap is split, the numbered parts come first and the index last.
    """
    root_path = _as_path_string(root_path)
    if not os.path.isdir(root_path):
        raise NotADirectoryError(
            "root_path must point to an existing directory, got %r" % (root_path,)
        )

    base_url = _normalise_base_url(base_url)

    max_urls = int(max_urls)
    if max_urls < 1:
        raise ValueError("max_urls must be a positive integer, got %r" % (max_urls,))
    if max_urls > MAX_URLS_PER_SITEMAP:
        warnings.warn(
            "max_urls=%d exceeds the sitemap protocol limit of %d; "
            "the limit will be used instead." % (max_urls, MAX_URLS_PER_SITEMAP),
            RuntimeWarning,
            stacklevel=2,
        )
        max_urls = MAX_URLS_PER_SITEMAP

    if allowed_extensions is None:
        extensions = list(DEFAULT_EXTENSIONS)
    else:
        if isinstance(allowed_extensions, str):
            allowed_extensions = [
                item.strip() for item in allowed_extensions.split(",") if item.strip()
            ]
        extensions = [ext for ext in (_normalise_extension(e) for e in allowed_extensions) if ext]
    if not extensions:
        raise ValueError("allowed_extensions must contain at least one extension")

    if isinstance(priority_mapping, dict):
        priority_mapping = _normalise_priority_mapping(priority_mapping)

    path_filter = _PathFilter(root_path, excluded_paths, exclude_hidden=exclude_hidden)

    entries = _walk_entries(
        root_path=root_path,
        base_url=base_url,
        path_filter=path_filter,
        extensions=extensions,
        priority_mapping=priority_mapping,
        default_priority=default_priority,
        show_progress=show_progress,
    )

    if include_homepage:
        homepage = {
            "loc": base_url,
            "lastmod": get_utc_lastmod(root_path),
            "priority": _format_priority(homepage_priority),
        }
        if any(entry["loc"] == homepage["loc"] for entry in entries):
            for entry in entries:
                if entry["loc"] == homepage["loc"]:
                    entry.update(homepage)
                    break
        else:
            entries.append(homepage)

    if sort_entries:
        entries.sort(key=lambda entry: entry["loc"])

    if show_progress:
        print("Total pages mapped: %d" % len(entries))

    if len(entries) <= max_urls:
        if show_progress:
            print("Saving sitemap to %s..." % output_file)
        write_sitemap_file(output_file, entries)
        return [_as_path_string(output_file)]

    if show_progress:
        print("URL limit is %d. Splitting into multiple sitemaps..." % max_urls)
    return _split_sitemaps(entries, output_file, base_url, max_urls, show_progress)
