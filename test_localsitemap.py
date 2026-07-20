import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from localsitemap import generate_sitemap

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
        shutil.rmtree(self.test_dir)

    def write_dummy_file(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("<html><body>Test</body></html>")

    def test_basic_sitemap_generation(self):
        # Generate with defaults
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file
        )

        # Parse XML and verify entries
        tree = ET.parse(self.output_file)
        root = tree.getroot()

        # Standard sitemap namespace
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall("sm:url/sm:loc", ns)]

        # We expect root directory, subdirectories, html/htm files
        # Directories included: about, blog, auth, authority, blog/posts
        # Files included: index.html, about/index.html, blog/first-post.html, blog/second-post.htm, blog/posts/post1.html, auth/login.html, authority/page.html
        # Plus the homepage itself

        self.assertIn("https://example.com", urls)
        self.assertIn("https://example.com/about/", urls)
        self.assertIn("https://example.com/about/index.html", urls)
        self.assertIn("https://example.com/blog/second-post.htm", urls)

        # Custom.php and custom.txt should NOT be included by default
        self.assertNotIn("https://example.com/custom.php", urls)
        self.assertNotIn("https://example.com/custom.txt", urls)

    def test_exclusion_exact_match(self):
        # Exclude "auth" only.
        # "authority" and "authority/page.html" should NOT be excluded.
        # "auth" directory and "auth/login.html" SHOULD be excluded.
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            excluded_paths=["auth"]
        )

        tree = ET.parse(self.output_file)
        root = tree.getroot()
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall("sm:url/sm:loc", ns)]

        # "auth" segments should be excluded
        self.assertNotIn("https://example.com/auth/", urls)
        self.assertNotIn("https://example.com/auth/login.html", urls)

        # "authority" segments should remain
        self.assertIn("https://example.com/authority/", urls)
        self.assertIn("https://example.com/authority/page.html", urls)

    def test_custom_extensions(self):
        # Generate with custom extensions [".php", "txt"]
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            allowed_extensions=[".php", "txt"]
        )

        tree = ET.parse(self.output_file)
        root = tree.getroot()
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall("sm:url/sm:loc", ns)]

        self.assertIn("https://example.com/custom.php", urls)
        self.assertIn("https://example.com/custom.txt", urls)
        # HTML files should not be present now
        self.assertNotIn("https://example.com/index.html", urls)

    def test_custom_priority_and_mapping(self):
        # Test default values and priority mapping as dict
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

        tree = ET.parse(self.output_file)
        root = tree.getroot()
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        entries = {}
        for url_node in root.findall("sm:url", ns):
            loc = url_node.find("sm:loc", ns).text
            prio = url_node.find("sm:priority", ns).text
            entries[loc] = prio

        self.assertEqual(entries["https://example.com"], "0.99")
        self.assertEqual(entries["https://example.com/about/index.html"], "0.95")
        self.assertEqual(entries["https://example.com/blog/second-post.htm"], "0.40")
        self.assertEqual(entries["https://example.com/blog/posts/"], "0.15")
        self.assertEqual(entries["https://example.com/index.html"], "0.55")

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

        tree = ET.parse(self.output_file)
        root = tree.getroot()
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        entries = {}
        for url_node in root.findall("sm:url", ns):
            loc = url_node.find("sm:loc", ns).text
            prio = url_node.find("sm:priority", ns).text
            entries[loc] = prio

        self.assertEqual(entries["https://example.com/about/"], "0.11")
        self.assertEqual(entries["https://example.com/blog/first-post.html"], "0.99")
        self.assertEqual(entries["https://example.com/index.html"], "0.75")

    def test_sitemap_splitting_and_index(self):
        # Set max_urls to 3. Since there are more than 3 entries total,
        # it should generate split sitemaps (sitemap_1.xml, sitemap_2.xml, etc)
        # and a sitemap.xml index.
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file,
            max_urls=3
        )

        # Verify index sitemap.xml is created
        self.assertTrue(os.path.exists(self.output_file))

        tree = ET.parse(self.output_file)
        root = tree.getroot()

        # It should be a sitemapindex root
        self.assertEqual(root.tag, "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex")

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        sitemap_locs = [loc.text for loc in root.findall("sm:sitemap/sm:loc", ns)]

        self.assertGreater(len(sitemap_locs), 1)
        self.assertIn("https://example.com/sitemap_1.xml", sitemap_locs)

        # Check that part 1 contains url entries
        part1_path = os.path.join(self.test_dir, "sitemap_1.xml")
        self.assertTrue(os.path.exists(part1_path))

        part_tree = ET.parse(part1_path)
        part_root = part_tree.getroot()
        self.assertEqual(part_root.tag, "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")

        part_urls = [loc.text for loc in part_root.findall("sm:url/sm:loc", ns)]
        self.assertEqual(len(part_urls), 3)

    def test_utc_timezone_format(self):
        # Ensure that timestamps end in +00:00 and are in correct ISO 8601 format
        generate_sitemap(
            root_path=self.test_dir,
            base_url="https://example.com",
            output_file=self.output_file
        )

        tree = ET.parse(self.output_file)
        root = tree.getroot()
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        lastmods = [lm.text for lm in root.findall("sm:url/sm:lastmod", ns)]
        for lm in lastmods:
            self.assertTrue(lm.endswith("+00:00"))
            # Format: YYYY-MM-DDThh:mm:ss+00:00
            self.assertEqual(len(lm), 25)
            self.assertEqual(lm[10], 'T')
            self.assertEqual(lm[19], '+')

if __name__ == "__main__":
    unittest.main()
