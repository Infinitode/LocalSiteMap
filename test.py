"""Small manual demo of LocalSiteMap.

Point ``root_directory`` at any local website checkout and run:

    python test.py

For automated checks use ``python -m unittest -v test_localsitemap`` instead.
"""

from localsitemap import generate_sitemap

# Root site directory
root_directory = r"path/to/your/website/directory"

# Domain of your website (where it is hosted)
base_url_of_your_website = "https://example.com"

# Only exact folder names, relative paths, absolute paths or glob patterns
# will be skipped
excluded = ["auth", "forms", "template.html", "media", ".git", ".vscode", "node_modules"]

# Generate the sitemap
written = generate_sitemap(
    root_path=root_directory,
    base_url=base_url_of_your_website,
    output_file="sitemap.xml",
    excluded_paths=excluded,
    show_progress=True,
)
print("Sitemap generated:", ", ".join(written))
