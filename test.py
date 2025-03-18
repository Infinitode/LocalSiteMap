from localsitemap import generate_sitemap

# Example usage
root_directory = r"path/to/your/website/directory"

# Domain of your website (where it is hosted)
base_url_of_your_website = "https://example.com"

# List of file paths or directories to exclude from the sitemap
excluded = ["auth", "forms", "template.html", "media", ".git", ".vscode", "node_modules"]  # Example exclusions

# Generate the sitemap
generate_sitemap(root_directory, base_url_of_your_website, "sitemap.xml", excluded)
print("Sitemap generated in sitemap.xml")