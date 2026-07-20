# LocalSiteMap
![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)
[![Code Size](https://img.shields.io/github/languages/code-size/infinitode/localsitemap)](https://github.com/infinitode/localsitemap)
![Downloads](https://pepy.tech/badge/localsitemap)
![License Compliance](https://img.shields.io/badge/license-compliance-brightgreen.svg)
![PyPI Version](https://img.shields.io/pypi/v/localsitemap)

LocalSiteMap is an open-source Python package designed for generating sitemaps and sitemap indexes from local files. It crawls your root website directory and automatically builds standard-compliant sitemaps.

### Changes in version 2.0.0 (Major Release):
- **Precise Exclusions**: Rewrote exclusion matching so only exact folder or filename matches (not partial substring matches) are excluded.
- **Traversal Optimization**: Subdirectories matching the exclusion list are pruned in-place, eliminating the overhead of traversing skipped directories.
- **UTC Timestamps**: Fixed timezone bug to retrieve and format all file modification timestamps as true, accurate UTC standard dates.
- **Customizable File Extensions**: Added optional `allowed_extensions` parameter to let you specify any list of file types to index (defaults to `[".html", ".htm"]`).
- **Flexible Priority Mappings**: Custom mapping for directory/page priorities using a dictionary or callable mapping function.
- **Sitemap Splitting & Sitemap Indexing**: Automatically splits large sitemaps into chunks and creates a standard `<sitemapindex>` parent if the URL limit (`max_urls`, defaults to 50,000) is exceeded.

### Changes in version 1.0.2:
- Removed the unnecessary `install_requires` from the `setup.py` as the package utilizes none of the required packages.

### Changes in version 1.0.1:
- Added `show_progress` boolean to print out mapping progress, pages mapped, and files found.

### Changes in version 1.0.0:
- Added initial package code, with automatic directory crawling to generate the `sitemap.xml` file.

> [!IMPORTANT]
> `LocalSiteMap` crawls any directory found in the root folder, be sure to add exclusions for important directories, or hidden/resource/file directories.

## Installation

You can install LocalSiteMap using pip:

```bash
pip install localsitemap
```

## Supported Python Versions

LocalSiteMap supports the following Python versions:

- Python 3.6
- Python 3.7
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11/Later (Preferred)

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
generate_sitemap(root_directory, base_url_of_your_website, "sitemap.xml", excluded, show_progress=True)
print("Sitemap generated in sitemap.xml")
```

### Advanced Features (Extensions, Mappings & Splitting)

```python
from localsitemap import generate_sitemap

# Custom priority dictionary or callable mapper
priority_mapping = {
    "about/index.html": 0.95,
    "blog/": 0.70,
    ".php": 0.50
}

generate_sitemap(
    root_path=r"path/to/website",
    base_url="https://example.com",
    output_file="sitemap.xml",
    excluded_paths=["node_modules", ".git"],
    allowed_extensions=[".html", ".htm", ".php"],
    default_priority=0.80,
    homepage_priority=1.00,
    priority_mapping=priority_mapping,
    max_urls=1000  # Will automatically split and output a sitemap index if URLs exceed 1000
)
```

## Contributing

Contributions are welcome! If you encounter any issues, have suggestions, or want to contribute to LocalSiteMap, please open an issue or submit a pull request on [GitHub](https://github.com/infinitode/localsitemap).

## License

LocalSiteMap is released under the terms of the **MIT License (Modified)**. Please see the [LICENSE](https://github.com/infinitode/localsitemap/blob/main/LICENSE) file for the full text.

**Modified License Clause**

The modified license clause grants users the permission to make derivative works based on the LocalSiteMap software. However, it requires any substantial changes to the software to be clearly distinguished from the original work and distributed under a different name.
