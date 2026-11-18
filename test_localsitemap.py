import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from localsitemap import (
    __version__,
    generate_sitemap,
    get_priority,
    is_excluded,
    write_sitemap_file,
)

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


class TestLocalSitemap(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory structure
        self.test_dir = tempfile.mkdtemp()

        # Create some folders
        os.makedirs(os.path.join(self.test_dir, "about"))
        os.makedirs(os.path.join(self.test_dir, "blog"))
        os.makedirs(os.path.join(self.test_dir, "auth"))
        os.makedirs(os.path.join(self.test_dir, "authority"))
        os.makedirs(os.path.join(self.test_dir, "blog", "posts"))

        # Create some files
        self.write_dummy_file(os.path.join(self.test_dir, "index.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "about", "index.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "blog", "first-post.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "blog", "second-post.htm"))
        self.write_dummy_file(os.path.join(self.test_dir, "blog", "posts", "post1.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "auth", "login.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "authority", "page.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "custom.php"))
        self.write_dummy_file(os.path.join(self.test_dir, "custom.txt"))

        self.output_file = os.path.join(self.test_dir, "sitemap.xml")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # -- helpers ---------------------------------------------------------

    def write_dummy_file(self, path, content="<html><body>Test</body></html>"):
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def urls(self, path=None):
        tree = ET.parse(path or self.output_file)
        return [loc.text for loc in tree.getroot().findall("sm:url/sm:loc", SITEMAP_NS)]

    def entries(self, path=None):
        tree = ET.parse(path or self.output_file)
        result = {}
        for url_node in tree.getroot().findall("sm:url", SITEMAP_NS):
            loc = url_node.find("sm:loc", SITEMAP_NS).text
            priority_node = url_node.find("sm:priority", SITEMAP_NS)
            lastmod_node = url_node.find("sm:lastmod", SITEMAP_NS)
            result[loc] = {
                "priority": priority_node.text if priority_node is not None else None,
                "lastmod": lastmod_node.text if lastmod_node is not None else None,
            }
        return result

    # -- existing behaviour ----------------------------------------------

    def test_basic_sitemap_generation(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file
        )

        urls = self.urls()

        self.assertIn("https://example.com", urls)
        self.assertIn("https://example.com/about/", urls)
        self.assertIn("https://example.com/about/index.html", urls)
        self.assertIn("https://example.com/blog/second-post.htm", urls)

        # custom.php and custom.txt should NOT be included by default
        self.assertNotIn("https://example.com/custom.php", urls)
        self.assertNotIn("https://example.com/custom.txt", urls)

        # No duplicate <loc> entries are allowed in a sitemap
        self.assertEqual(len(urls), len(set(urls)))

    def test_exclusion_exact_match(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths=["auth"]
        )

        urls = self.urls()

        self.assertNotIn("https://example.com/auth/", urls)
        self.assertNotIn("https://example.com/auth/login.html", urls)

        self.assertIn("https://example.com/authority/", urls)
        self.assertIn("https://example.com/authority/page.html", urls)

    def test_custom_extensions(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            allowed_extensions=[".php", "txt"]
        )

        urls = self.urls()

        self.assertIn("https://example.com/custom.php", urls)
        self.assertIn("https://example.com/custom.txt", urls)
        self.assertNotIn("https://example.com/index.html", urls)

    def test_custom_priority_and_mapping(self):
        pm = {
            "about/index.html": 0.95,
            "blog/second-post.htm": 0.40,
            "posts": 0.15
        }

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            default_priority=0.55,
            homepage_priority=0.99,
            priority_mapping=pm
        )

        entries = self.entries()

        self.assertEqual(entries["https://example.com"]["priority"], "0.99")
        self.assertEqual(entries["https://example.com/about/index.html"]["priority"], "0.95")
        self.assertEqual(entries["https://example.com/blog/second-post.htm"]["priority"], "0.40")
        self.assertEqual(entries["https://example.com/blog/posts/"]["priority"], "0.15")
        self.assertEqual(entries["https://example.com/index.html"]["priority"], "0.55")

    def test_custom_priority_callable(self):
        def my_priority_mapper(relative_path, is_dir):
            if is_dir:
                return 0.11
            if "first" in relative_path:
                return 0.99
            return None

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            default_priority=0.75,
            priority_mapping=my_priority_mapper
        )

        entries = self.entries()

        self.assertEqual(entries["https://example.com/about/"]["priority"], "0.11")
        self.assertEqual(entries["https://example.com/blog/first-post.html"]["priority"], "0.99")
        self.assertEqual(entries["https://example.com/index.html"]["priority"], "0.75")

    def test_sitemap_splitting_and_index(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            max_urls=3
        )

        self.assertTrue(os.path.exists(self.output_file))

        root = ET.parse(self.output_file).getroot()
        self.assertEqual(root.tag, "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex")

        sitemap_locs = [loc.text for loc in root.findall("sm:sitemap/sm:loc", SITEMAP_NS)]

        self.assertGreater(len(sitemap_locs), 1)
        self.assertIn("https://example.com/sitemap_1.xml", sitemap_locs)

        part1_path = os.path.join(self.test_dir, "sitemap_1.xml")
        self.assertTrue(os.path.exists(part1_path))

        part_root = ET.parse(part1_path).getroot()
        self.assertEqual(part_root.tag, "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")

        part_urls = [loc.text for loc in part_root.findall("sm:url/sm:loc", SITEMAP_NS)]
        self.assertEqual(len(part_urls), 3)

    def test_utc_timezone_format(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file
        )

        lastmods = [value["lastmod"] for value in self.entries().values()]
        for lm in lastmods:
            self.assertTrue(lm.endswith("+00:00"))
            self.assertEqual(len(lm), 25)
            self.assertEqual(lm[10], 'T')
            self.assertEqual(lm[19], '+')

    # -- bug fixes / new behaviour ---------------------------------------

    def test_exclusion_does_not_match_parent_directories(self):
        """A site checked out below a folder named like an exclusion still works."""
        parent = tempfile.mkdtemp()
        try:
            site = os.path.join(parent, "media", "website")
            os.makedirs(site)
            self.write_dummy_file(os.path.join(site, "index.html"))
            output = os.path.join(site, "sitemap.xml")

            generate_sitemap(
                root_path=site,
                base_url="https://example.com",
                output_file=output,
                excluded_paths=["media"],
            )

            urls = self.urls(output)
            self.assertIn("https://example.com/index.html", urls)
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    def test_exclusion_of_nested_relative_path(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths=[os.path.join("blog", "posts")],
        )

        urls = self.urls()
        self.assertNotIn("https://example.com/blog/posts/", urls)
        self.assertNotIn("https://example.com/blog/posts/post1.html", urls)
        self.assertIn("https://example.com/blog/", urls)

    def test_exclusion_of_file_name(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths=["second-post.htm"],
        )
        self.assertNotIn("https://example.com/blog/second-post.htm", self.urls())

    def test_absolute_exclusion_path(self):
        excluded_dir = os.path.join(self.test_dir, "blog", "posts")
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths=[excluded_dir],
        )
        self.assertNotIn("https://example.com/blog/posts/post1.html", self.urls())

    def test_glob_exclusions(self):
        self.write_dummy_file(os.path.join(self.test_dir, "draft-page.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "blog", "draft-note.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "notes.tmp"))

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths=["draft-*", "*.tmp"],
            allowed_extensions=[".html", ".tmp"],
        )

        urls = self.urls()
        self.assertNotIn("https://example.com/draft-page.html", urls)
        self.assertNotIn("https://example.com/blog/draft-note.html", urls)
        self.assertNotIn("https://example.com/notes.tmp", urls)
        self.assertIn("https://example.com/index.html", urls)

    def test_is_excluded_helper(self):
        self.assertTrue(is_excluded(os.path.join(self.test_dir, "auth"), self.test_dir, ["auth"]))
        self.assertFalse(
            is_excluded(os.path.join(self.test_dir, "authority"), self.test_dir, ["auth"])
        )
        self.assertFalse(is_excluded(self.test_dir, self.test_dir, ["website"]))

    def test_extensions_are_case_insensitive(self):
        self.write_dummy_file(os.path.join(self.test_dir, "UPPER.HTML"))
        self.write_dummy_file(os.path.join(self.test_dir, "upper.PHP"))
        self.write_dummy_file(os.path.join(self.test_dir, "page.html.bak"))

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            allowed_extensions=[".HTML", "PHP"],
        )

        urls = self.urls()
        self.assertIn("https://example.com/UPPER.HTML", urls)
        self.assertIn("https://example.com/upper.PHP", urls)
        self.assertIn("https://example.com/custom.php", urls)
        self.assertNotIn("https://example.com/page.html.bak", urls)

    def test_urls_are_percent_encoded(self):
        self.write_dummy_file(os.path.join(self.test_dir, "my page.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "a&b.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "hash#1.html"))
        self.write_dummy_file(os.path.join(self.test_dir, "café", "index.html"))

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
        )

        urls = self.urls()
        self.assertIn("https://example.com/my%20page.html", urls)
        self.assertIn("https://example.com/a%26b.html", urls)
        self.assertIn("https://example.com/hash%231.html", urls)
        self.assertIn("https://example.com/caf%C3%A9/", urls)
        self.assertIn("https://example.com/caf%C3%A9/index.html", urls)
        for url in urls:
            self.assertNotIn(" ", url)
            self.assertNotIn("#", url)

    def test_priority_mapping_accepts_folder_and_extension_variants(self):
        mapping = {
            "blog/": 0.70,           # documented trailing slash folder key
            "posts\\": 0.20,         # Windows separator
            ".PHP": 0.35,            # upper case extension
            "about/index.html": 0.90,
        }

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            priority_mapping=mapping,
            allowed_extensions=[".html", ".php"],
        )

        entries = self.entries()
        self.assertEqual(entries["https://example.com/blog/"]["priority"], "0.70")
        self.assertEqual(entries["https://example.com/blog/posts/"]["priority"], "0.20")
        self.assertEqual(entries["https://example.com/custom.php"]["priority"], "0.35")
        self.assertEqual(entries["https://example.com/about/index.html"]["priority"], "0.90")

    def test_priorities_are_clamped_to_the_protocol_range(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            default_priority=0.5,
            priority_mapping={"about/index.html": 5, "index.html": -2},
        )
        entries = self.entries()
        self.assertEqual(entries["https://example.com/about/index.html"]["priority"], "1.00")
        self.assertEqual(entries["https://example.com/index.html"]["priority"], "0.00")

    def test_get_priority_public_helper(self):
        self.assertEqual(
            get_priority("blog/posts", True, 0.5, {"posts": 0.3}), "0.30"
        )
        self.assertEqual(get_priority("blog/posts", True, 0.5), "0.50")
        self.assertEqual(
            get_priority("blog/posts", True, 0.5, lambda rel, is_dir: 0.25), "0.25"
        )

    def test_missing_root_raises(self):
        with self.assertRaises(NotADirectoryError):
            generate_sitemap(
                os.path.join(self.test_dir, "does-not-exist"),
                "https://example.com",
                self.output_file,
            )

    def test_invalid_base_url_raises(self):
        with self.assertRaises(ValueError):
            generate_sitemap(self.test_dir, "example.com", self.output_file)

    def test_invalid_max_urls_raises(self):
        for value in (0, -5):
            with self.assertRaises(ValueError):
                generate_sitemap(
                    self.test_dir, "https://example.com", self.output_file, max_urls=value
                )

    def test_max_urls_above_protocol_limit_warns(self):
        with self.assertWarns(RuntimeWarning):
            generate_sitemap(
                self.test_dir, "https://example.com", self.output_file, max_urls=60000
            )
        self.assertEqual(
            ET.parse(self.output_file).getroot().tag,
            "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset",
        )

    def test_output_directory_is_created(self):
        nested = os.path.join(self.test_dir, "public", "seo", "sitemap.xml")
        created = generate_sitemap(self.test_dir, "https://example.com", nested)
        self.assertTrue(os.path.exists(nested))
        self.assertEqual(created, [nested])

    def test_string_arguments_are_accepted(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths="auth",
            allowed_extensions="html,php",
        )
        urls = self.urls()
        self.assertNotIn("https://example.com/auth/login.html", urls)
        self.assertIn("https://example.com/custom.php", urls)
        self.assertIn("https://example.com/index.html", urls)

    def test_exclude_hidden(self):
        self.write_dummy_file(os.path.join(self.test_dir, ".hidden.html"))
        self.write_dummy_file(os.path.join(self.test_dir, ".git", "config.html"))

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            exclude_hidden=True,
        )

        urls = self.urls()
        for url in urls:
            self.assertNotIn("/.", url)
        self.assertIn("https://example.com/index.html", urls)

    def test_include_homepage_false(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com/",
            output_file=self.output_file,
            include_homepage=False,
        )
        self.assertNotIn("https://example.com", self.urls())

    def test_base_url_trailing_slash_is_normalised(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com/",
            output_file=self.output_file,
        )
        urls = self.urls()
        self.assertIn("https://example.com", urls)
        self.assertIn("https://example.com/about/", urls)
        self.assertEqual(len(urls), len(set(urls)))

    def test_output_is_deterministic(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
        )
        with open(self.output_file, "rb") as handle:
            first = handle.read()

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
        )
        with open(self.output_file, "rb") as handle:
            second = handle.read()

        self.assertEqual(first, second)

    def test_output_is_pretty_and_parsable(self):
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
        )
        with open(self.output_file, "r", encoding="utf-8") as handle:
            content = handle.read()

        self.assertTrue(content.startswith('<?xml version="1.0" encoding="utf-8"?>'))
        self.assertNotIn("\n\n", content)
        self.assertIn('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"', content)
        ET.fromstring(content)  # must be well-formed

    def collect_urls(self, paths):
        collected = []
        for path in paths:
            collected.extend(self.urls(path))
        return collected

    def reference_urls(self):
        """Generate an unsplit sitemap elsewhere and return its URLs."""
        reference_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, reference_dir, ignore_errors=True)
        reference = os.path.join(reference_dir, "sitemap.xml")
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=reference,
        )
        return set(self.urls(reference))

    def test_split_covers_every_url_exactly_once(self):
        created = generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            max_urls=2,
        )

        self.assertEqual(created[-1], self.output_file)
        parts = [path for path in created if path != self.output_file]
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(os.path.exists(part) for part in parts))

        collected = self.collect_urls(parts)
        self.assertEqual(len(collected), len(set(collected)))
        self.assertEqual(set(collected), self.reference_urls())

    def test_split_index_lists_every_part(self):
        created = generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            max_urls=2,
        )
        parts = [path for path in created if path != self.output_file]

        root = ET.parse(self.output_file).getroot()
        index_locs = [loc.text for loc in root.findall("sm:sitemap/sm:loc", SITEMAP_NS)]

        expected = ["https://example.com/" + os.path.basename(part) for part in parts]
        self.assertEqual(index_locs, expected)
        self.assertEqual(len(index_locs), len(parts))

    def test_stale_split_parts_are_removed(self):
        stale = os.path.join(self.test_dir, "sitemap_9.xml")
        self.write_dummy_file(stale, content="<urlset/>")

        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            max_urls=3,
        )

        self.assertFalse(os.path.exists(stale))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "sitemap_1.xml")))

    def test_write_sitemap_file_helper(self):
        target = os.path.join(self.test_dir, "manual.xml")
        write_sitemap_file(
            target,
            [
                {
                    "loc": "https://example.com/a?b=1&c=2",
                    "lastmod": "2024-01-01T00:00:00+00:00",
                    "priority": "0.50",
                }
            ],
        )
        urls = self.urls(target)
        self.assertEqual(urls, ["https://example.com/a?b=1&c=2"])

    def test_version_is_exposed(self):
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+")

    # -- CLI -------------------------------------------------------------

    def run_cli(self, *args):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [REPO_ROOT, environment.get("PYTHONPATH", "")]
        ).strip(os.pathsep)
        return subprocess.run(
            [sys.executable, "-m", "localsitemap"] + list(args),
            cwd=self.test_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def test_cli_generates_sitemap(self):
        result = self.run_cli(
            self.test_dir,
            "https://example.com",
            "-o",
            "cli-sitemap.xml",
            "--exclude",
            "auth",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        target = os.path.join(self.test_dir, "cli-sitemap.xml")
        self.assertTrue(os.path.exists(target))
        urls = self.urls(target)
        self.assertIn("https://example.com/blog/first-post.html", urls)
        self.assertNotIn("https://example.com/auth/login.html", urls)

    def test_cli_priority_map_and_version(self):
        mapping_path = os.path.join(self.test_dir, "priorities.json")
        with open(mapping_path, "w", encoding="utf-8") as handle:
            json.dump({".html": 0.42}, handle)

        result = self.run_cli(
            self.test_dir,
            "https://example.com",
            "-o",
            "cli-sitemap.xml",
            "--priority-map",
            mapping_path,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = self.entries(os.path.join(self.test_dir, "cli-sitemap.xml"))
        self.assertEqual(entries["https://example.com/index.html"]["priority"], "0.42")

        version_result = self.run_cli("--version")
        self.assertEqual(version_result.returncode, 0)
        self.assertIn(__version__, version_result.stdout)

    def test_cli_reports_errors(self):
        result = self.run_cli("missing-directory", "https://example.com")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
