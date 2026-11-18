# LocalSiteMap

[![PyPI Version](https://img.shields.io/pypi/v/localsitemap)](https://pypi.org/project/localsitemap/)
[![PyPI - Python Versions](https://img.shields.io/pypi/pyversions/localsitemap)](https://pypi.org/project/localsitemap/)
[![PyPI provenance](https://img.shields.io/badge/PyPI%20provenance-attested-blueviolet?logo=pypi&logoColor=white)](https://pypi.org/project/localsitemap/#files)
[![Tests](https://github.com/Infinitode/LocalSiteMap/actions/workflows/tests.yml/badge.svg)](https://github.com/Infinitode/LocalSiteMap/actions/workflows/tests.yml)
[![Downloads](https://pepy.tech/badge/localsitemap)](https://pepy.tech/project/localsitemap)
[![Code Size](https://img.shields.io/github/languages/code-size/infinitode/localsitemap)](https://github.com/Infinitode/LocalSiteMap)
![License](https://img.shields.io/badge/license-MIT%20(modified)-brightgreen.svg)

LocalSiteMap is an open-source Python package designed for generating sitemaps and sitemap indexes from local files. It crawls your root website directory and automatically builds standard-compliant sitemaps. No third-party dependencies are required.

> [!IMPORTANT]
> `LocalSiteMap` crawls any directory found in the root folder, be sure to add exclusions for important directories, or hidden/resource/file directories.

## Changes in version 2.1.0

### Breaking change
- **Python 3.9 or newer is now required.** Python 3.6 – 3.8 are long past end-of-life and are no longer supported by modern packaging tooling. Version `2.0.0` on PyPI still serves those interpreters (pip selects it automatically), and the runtime code has no 3.9-only syntax.

### Bug fixes
- **Exclusions no longer match parent folders**: exclusions are now resolved *inside* the site root, so a site checked out in (for example) a folder called `media` is not wiped out when `media` is excluded.
- **Priority map keys now behave as documented**: folder keys may be written with a trailing slash (`"blog/"`), Windows separators are accepted, and extension keys are matched case-insensitively (`".PHP"` matches `.php`).
- **URLs are percent-encoded**: file and folder names containing spaces, `#`, `&`, `?` or non-ASCII characters (e.g. `my page.html`, `café/`) now produce valid, crawlable URLs.
- **Extension matching is case-insensitive**: `PAGE.HTML` is picked up by the default configuration, and `page.html.bak` is not mistaken for `page.html`.
- **Inputs are validated**: a missing `root_path`, a `base_url` without a scheme, or a non-positive `max_urls` now raise a clear error instead of silently writing a broken sitemap. `max_urls` above the protocol limit of 50 000 is clamped with a warning.
- **Priorities are clamped** to the `0.00`–`1.00` range required by the sitemap protocol.
- **Deterministic, deduplicated output**: entries are sorted, duplicate `<loc>` values are dropped, and repeated runs produce byte-identical files.
- **Stale split sitemaps are removed**: shrinking a site no longer leaves orphaned `sitemap_N.xml` parts behind.
- **Output is written atomically** and missing output directories are created, so an interrupted run cannot leave a truncated sitemap behind.
- **Much faster XML writing**: the DOM round-trip (`minidom`) was replaced with a streaming writer, which also removes the stray blank lines from the output.

### New features
- **Command line interface**: `localsitemap` / `python -m localsitemap` with exclusions, extensions, priorities and a JSON priority map.
- **Glob exclusions**: `["draft-*", "*.bak"]`.
- **New options**: `exclude_hidden`, `include_homepage`, `sort_entries`.
- **`generate_sitemap()` returns the written files**, which is handy for CI and build scripts.
- **Modern packaging**: metadata moved to `pyproject.toml` with the version read from `localsitemap/_version.py`.
- **Release pipeline**: published from GitHub Actions with PyPI Trusted Publishing (OIDC) and PEP 740 attestations — see [Release provenance](#release-provenance).

### Changes in version 2.0.0 (Major Release)
- **Precise Exclusions**: Rewrote exclusion matching so only exact folder or filename matches (not partial substring matches) are excluded.
- **Traversal Optimization**: Subdirectories matching the exclusion list are pruned in-place, eliminating the overhead of traversing skipped directories.
- **UTC Timestamps**: Fixed timezone bug to retrieve and format all file modification timestamps as true, accurate UTC standard dates.
- **Customizable File Extensions**: Added optional `allowed_extensions` parameter to let you specify any list of file types to index (defaults to `[".html", ".htm"]`).
- **Flexible Priority Mappings**: Custom mapping for directory/page priorities using a dictionary or callable mapping function.
- **Sitemap Splitting & Sitemap Indexing**: Automatically splits large sitemaps into chunks and creates a standard `<sitemapindex>` parent if the URL limit (`max_urls`, defaults to 50,000) is exceeded.

### Changes in version 1.0.2
- Removed the unnecessary `install_requires` from the `setup.py` as the package utilizes none of the required packages.

### Changes in version 1.0.1
- Added `show_progress` boolean to print out mapping progress, pages mapped, and files found.

### Changes in version 1.0.0
- Added initial package code, with automatic directory crawling to generate the `sitemap.xml` file.

## Installation

You can install LocalSiteMap using pip:

```bash
pip install localsitemap
```

## Supported Python Versions

LocalSiteMap supports Python 3.9 and newer, and every release is tested on CPython 3.9 – 3.14 on Linux, plus Windows:

- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13/Later (Preferred)
- Python 3.14

## Features

- **Directory Crawling**: `LocalSiteMap` automatically crawls all subdirectories and files under the root directory, recursively adding them to your sitemap.
- **Optimized Walking**: Excluded directories are completely skipped during traversal to ensure high performance even for large projects.
- **UTC Last Modified Checks**: Accurate file modification UTC timezone checks automatically update the `<lastmod>` metadata tag.
- **Sitemap Splitting & Indexes**: Automatically partitions large lists of pages/folders into multiple numbered sitemaps (e.g. `sitemap_1.xml`, `sitemap_2.xml`) and outputs a compliant `sitemap.xml` index.
- **Customizable Extensions**: Configure any extensions you want mapped instead of just standard HTML (e.g. php, pdf, txt).
- **Flexible Priority Mapping**: Map explicit paths to customized page weightings via custom definitions or callable filters.
- **Open Source**: Released under the terms of the Modified MIT License.

## Usage

### Generating a basic sitemap

```python
from localsitemap import generate_sitemap

# Root site directory
root_directory = r"path/to/your/website/directory"

# Domain of your website (where it is hosted)
base_url_of_your_website = "https://example.com"

# Only exact folder names or complete relative paths will be skipped
excluded = ["auth", "forms", "template.html", "media", ".git", ".vscode", "node_modules"]

# Generate the sitemap
written = generate_sitemap(
    root_directory,
    base_url_of_your_website,
    "sitemap.xml",
    excluded,
    show_progress=True,
)
print("Sitemap generated:", ", ".join(written))
```

### Advanced Features (Extensions, Mappings & Splitting)

```python
from localsitemap import generate_sitemap

# Custom priority dictionary or callable mapper.
# Keys may be a relative path, a folder name (trailing slash optional),
# a file name, or an extension (case-insensitive).
priority_mapping = {
    "about/index.html": 0.95,
    "blog/": 0.70,
    ".php": 0.50,
}

generate_sitemap(
    root_path=r"path/to/website",
    base_url="https://example.com",
    output_file="sitemap.xml",
    excluded_paths=["node_modules", ".git", "draft-*", "*.bak"],
    allowed_extensions=[".html", ".htm", ".php"],
    default_priority=0.80,
    homepage_priority=1.00,
    priority_mapping=priority_mapping,
    max_urls=1000,  # Automatically splits and writes a sitemap index above 1000 URLs
)
```

### Exclusions

Exclusions are always interpreted relative to `root_path`:

| Pattern | Meaning |
| --- | --- |
| `"node_modules"` | any file or folder with that name, at any depth |
| `"blog/posts"` | that relative path and everything below it |
| `"/srv/site/private"` | an absolute path inside the site root |
| `"draft-*"`, `"*.bak"` | shell-style glob patterns |

`excluded_paths=["auth"]` therefore excludes `auth/` but keeps `authority/`.

### Command line

```bash
# After pip install localsitemap (or with `python -m localsitemap`)
localsitemap path/to/website https://example.com \
    -o public/sitemap.xml \
    --exclude auth --exclude "draft-*" \
    --extensions .html,.htm,.php \
    --max-urls 1000 \
    --progress
```

Run `localsitemap --help` for every option, including `--priority-map priorities.json` and `--exclude-hidden`.

### Release provenance

Releases are built and published by GitHub Actions through [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — there is no long-lived PyPI API token in this repository. Every uploaded file is signed with a [PEP 740](https://peps.python.org/pep-0740/) digital attestation, which is what makes PyPI display the *provenance* indicator for the release. You can verify it yourself with the bundled script:

```bash
python .github/scripts/verify_provenance.py --project localsitemap --version 2.1.0
```

or straight from the public Integrity API:

```bash
curl -s "https://pypi.org/integrity/localsitemap/2.1.0/localsitemap-2.1.0-py3-none-any.whl/provenance" \
  | python -m json.tool
```

A non-`404` response containing an `attestation_bundles` entry proves the file was built by this repository's workflow.

## Contributing

Contributions are welcome! If you encounter any issues, have suggestions, or want to contribute to LocalSiteMap, please open an issue or submit a pull request on [GitHub](https://github.com/Infinitode/LocalSiteMap). See [CONTRIBUTING.md](CONTRIBUTING.md) for the test and release workflow.

## License

LocalSiteMap is released under the terms of the **MIT License (Modified)**. Please see the [LICENSE](https://github.com/Infinitode/LocalSiteMap/blob/main/LICENSE) file for the full text.

**Modified License Clause**

The modified license clause grants users the permission to make derivative works based on the LocalSiteMap software. However, it requires any substantial changes to the software to be clearly distinguished from the original work and distributed under a different name.
