import os
import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def is_excluded(path, root_path, excluded_paths):
    """
    Checks if a path is excluded based on a list of excluded paths/directories.
    Only direct matches or matching path components are excluded, preventing partial substring matches.
    """
    if not excluded_paths:
        return False

    # Get absolute path and split into segments
    abs_path = os.path.abspath(path)
    path_segments = abs_path.split(os.sep)

    for excl in excluded_paths:
        if not excl:
            continue
        # Standardize separators in excl
        excl_norm = excl.replace('/', os.sep).replace('\\', os.sep)

        # If it's a simple name (no separators)
        if os.sep not in excl_norm:
            if excl_norm in path_segments:
                return True
            continue

        # If it's a path (contains separators), we resolve it
        # Try both assuming it's an absolute path or relative to root_path
        if os.path.isabs(excl_norm):
            abs_excl = os.path.abspath(excl_norm)
        else:
            abs_excl = os.path.abspath(os.path.join(root_path, excl_norm))

        excl_segments = abs_excl.split(os.sep)
        # Check if excl_segments is a prefix of path_segments
        if len(path_segments) >= len(excl_segments):
            if path_segments[:len(excl_segments)] == excl_segments:
                return True

    return False

def get_utc_lastmod(path):
    """
    Returns the UTC last modified time of the path in YYYY-MM-DDThh:mm:ss+00:00 format.
    """
    try:
        mtime = os.path.getmtime(path)
        dt = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def get_priority(relative_path, is_dir, default_priority, priority_mapping=None):
    """
    Computes priority based on the relative path, directory status, default, and mapping.
    """
    if priority_mapping:
        if callable(priority_mapping):
            try:
                p = priority_mapping(relative_path, is_dir)
                if p is not None:
                    return f"{float(p):.2f}"
            except Exception:
                pass
        elif isinstance(priority_mapping, dict):
            # Standardize relative_path to use forward slashes
            norm_rel = relative_path.replace("\\", "/")
            if norm_rel in priority_mapping:
                return f"{float(priority_mapping[norm_rel]):.2f}"
            # Also try matching file/dir name (basename)
            basename = os.path.basename(relative_path)
            if basename in priority_mapping:
                return f"{float(priority_mapping[basename]):.2f}"
            # Try matching by extension
            _, ext = os.path.splitext(basename)
            if ext in priority_mapping:
                return f"{float(priority_mapping[ext]):.2f}"
    return f"{float(default_priority):.2f}"

def write_sitemap_file(file_path, entries):
    """
    Writes a list of entries to a sitemap XML file.
    """
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    urlset.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    urlset.set("xsi:schemaLocation", "http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd")

    for entry in entries:
        url_entry = SubElement(urlset, "url")
        SubElement(url_entry, "loc").text = entry["loc"]
        SubElement(url_entry, "lastmod").text = entry["lastmod"]
        SubElement(url_entry, "priority").text = entry["priority"]

    xml_string = tostring(urlset, "utf-8")
    reparsed = minidom.parseString(xml_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

def write_sitemap_index_file(file_path, sitemaps_info):
    """
    Writes a list of sitemap files to a sitemap index XML file.
    """
    sitemapindex = Element("sitemapindex")
    sitemapindex.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    for info in sitemaps_info:
        sitemap_entry = SubElement(sitemapindex, "sitemap")
        SubElement(sitemap_entry, "loc").text = info["loc"]
        SubElement(sitemap_entry, "lastmod").text = info["lastmod"]

    xml_string = tostring(sitemapindex, "utf-8")
    reparsed = minidom.parseString(xml_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

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
    max_urls=50000
):
    """
    Generates a sitemap XML file or multiple files plus an index if URLs exceed max_urls.

    Parameters:
        root_path: The root directory of your website.
        base_url: The base URL of your website (e.g., "https://example.com").
        output_file: The name of the output XML file (default: "sitemap.xml").
        excluded_paths: A list of file paths or directories to exclude from the sitemap.
        show_progress: Boolean to print mapping progress.
        allowed_extensions: List of allowed file extensions (default: [".html", ".htm"]).
        default_priority: Default priority for paths (default: 0.80).
        homepage_priority: Priority for the root directory (default: 1.00).
        priority_mapping: Dict or callable to map specific paths to priorities.
        max_urls: Max URLs per single sitemap file before splitting (default: 50000).
    """
    if excluded_paths is None:
        excluded_paths = []

    if allowed_extensions is None:
        allowed_extensions = [".html", ".htm"]
    else:
        # Normalize allowed_extensions to start with "."
        allowed_extensions = [ext if ext.startswith(".") else f".{ext}" for ext in allowed_extensions]

    entries = []

    for root, dirs, files in os.walk(root_path):
        # Optimize by pruning excluded directories in-place
        dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d), root_path, excluded_paths)]

        # Add directories to entries
        for dir_name in dirs:
            full_dir_path = os.path.join(root, dir_name)
            if show_progress:
                print(f"Mapping directory: {full_dir_path}")

            relative_dir_path = os.path.relpath(full_dir_path, root_path)
            base = base_url.rstrip("/")
            url = (base + "/" + relative_dir_path.replace("\\", "/")).rstrip("/") + "/"

            lastmod = get_utc_lastmod(full_dir_path)
            priority = get_priority(relative_dir_path, is_dir=True, default_priority=default_priority, priority_mapping=priority_mapping)

            entries.append({
                "loc": url,
                "lastmod": lastmod,
                "priority": priority
            })

        for file in files:
            if file.endswith(tuple(allowed_extensions)):
                full_path = os.path.join(root, file)

                if is_excluded(full_path, root_path, excluded_paths):
                    continue

                if show_progress:
                    print(f"Found file: {full_path}")

                relative_path = os.path.relpath(full_path, root_path)
                base = base_url.rstrip("/")
                url = base + "/" + relative_path.replace("\\", "/")

                lastmod = get_utc_lastmod(full_path)
                priority = get_priority(relative_path, is_dir=False, default_priority=default_priority, priority_mapping=priority_mapping)

                entries.append({
                    "loc": url,
                    "lastmod": lastmod,
                    "priority": priority
                })

    # Add homepage to entries
    homepage_url = base_url
    homepage_lastmod = get_utc_lastmod(root_path)
    entries.append({
        "loc": homepage_url,
        "lastmod": homepage_lastmod,
        "priority": f"{float(homepage_priority):.2f}"
    })

    # Write the XML output
    if len(entries) <= max_urls:
        if show_progress:
            print(f"Total pages mapped: {len(entries)}")
            print(f"Saving sitemap to {output_file}...")
        write_sitemap_file(output_file, entries)
    else:
        if show_progress:
            print(f"Total pages mapped: {len(entries)}. Limit is {max_urls}. Splitting into multiple sitemaps...")

        dir_name = os.path.dirname(output_file)
        base_name = os.path.basename(output_file)
        name, ext = os.path.splitext(base_name)

        sitemaps_info = []

        # Split into chunks of size max_urls
        for i in range(0, len(entries), max_urls):
            chunk = entries[i:i + max_urls]
            part_num = (i // max_urls) + 1
            part_filename = f"{name}_{part_num}{ext}"
            part_file_path = os.path.join(dir_name, part_filename) if dir_name else part_filename

            if show_progress:
                print(f"Saving split sitemap part {part_num} to {part_file_path}...")

            write_sitemap_file(part_file_path, chunk)

            base = base_url.rstrip("/")
            part_url = f"{base}/{part_filename}"
            part_lastmod = get_utc_lastmod(part_file_path)

            sitemaps_info.append({
                "loc": part_url,
                "lastmod": part_lastmod
            })

        if show_progress:
            print(f"Saving sitemap index to {output_file}...")
        write_sitemap_index_file(output_file, sitemaps_info)
