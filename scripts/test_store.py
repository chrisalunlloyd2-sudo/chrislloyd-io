import json, os, re, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


class StoreLint(unittest.TestCase):
    def setUp(self):
        self.cur = json.loads(read("data/store-curation.json"))
        self.rules = json.loads(read("data/store-rules.json"))
        self.store = json.loads(read("data/store.json"))

    def test_disclosure_present_on_both_pages(self):
        for page in ("products.html", "index.html"):
            html = read(page).lower()
            self.assertIn("commission" if page == "products.html" else "affiliate", html, page)
            self.assertRegex(html, r"1%", page)

    def test_store_items_are_valid(self):
        urls = [i["url"] for i in self.store["items"]]
        self.assertEqual(len(urls), len(set(urls)), "duplicate product")
        ids = [i["id"] for i in self.store["items"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate image id")
        cats = [c["name"] for c in self.rules["categories"]] + [self.rules["default"]]
        self.assertEqual(self.store["categories"], cats)
        for item in self.store["items"]:
            self.assertIn(item["category"], cats)
            self.assertTrue(item["url"].startswith(self.cur["store_base"] + "/products/"), item["url"])

    def test_no_invented_fields(self):
        allowed = {"id", "title", "category", "desc", "features", "image", "url"}
        for item in self.store["items"]:
            self.assertEqual(set(item) - {"price", "price_from"}, allowed)
            blob = json.dumps(item).lower()
            for word in ("rating", "stars", "reviews", "bestseller", "best seller", "tested by", "guarantee"):
                self.assertIsNone(re.search(r"\b" + re.escape(word) + r"\b", blob), (word, item["title"]))
            self.assertTrue(item["image"].startswith(("assets/store/", "https://cdn.shopify.com/")), item["title"])
            if item["image"].startswith("assets/"):
                self.assertTrue(os.path.getsize(os.path.join(ROOT, item["image"])) > 1000, item["image"])

    def test_no_off_niche_or_placeholder_products(self):
        banned = ("example product",)
        for item in self.store["items"]:
            for w in banned:
                self.assertNotIn(w, item["title"].lower(), item["title"])

    def test_every_card_has_image_and_text(self):
        for item in self.store["items"]:
            self.assertTrue(item["image"], item["title"])

    def test_every_card_has_text(self):
        for item in self.store["items"]:
            self.assertTrue(item["desc"].strip(), item["title"])
            self.assertLessEqual(len(item["desc"]), 125, item["title"])

    def test_lidar_uses_labelled_concepts(self):
        uses = json.loads(read("data/lidar.json"))
        self.assertEqual(len(uses), 5)
        for u in uses:
            self.assertEqual(u["category"], "Concept idea")
        self.assertRegex(read("index.html").lower(), r"concept")


class VoiceLint(unittest.TestCase):
    def test_voice_uses_labelled_in_development(self):
        uses = json.loads(read("data/voice.json"))
        self.assertEqual(len(uses), 5)
        for u in uses:
            self.assertEqual(u["category"], "In development")
        self.assertIn("not released", read("index.html"))


class PingLint(unittest.TestCase):
    PAGES = ("index.html", "blog.html", "products.html", "leduc.html", "sherwood-park.html", "spruce-grove.html", "st-albert.html")

    def test_every_page_has_script_and_disclosure(self):
        for page in self.PAGES:
            html = read(page)
            self.assertIn("assets/visit-ping.js", html, page)
            self.assertIn("notification when a page is opened", html, page)
            self.assertIn("Do Not Track", html, page)

    def test_config_url_is_https_and_script_asks_for_no_location(self):
        url = json.loads(read("data/config.json")).get("visitPingUrl", "")
        self.assertTrue(url == "" or url.startswith("https://"), url)
        self.assertNotIn("geolocation", read("assets/visit-ping.js"))


if __name__ == "__main__":
    unittest.main()
