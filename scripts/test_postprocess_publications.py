import tempfile
import unittest
from pathlib import Path

from postprocess_publications import process_publication_dir


class FeaturedPublicationTests(unittest.TestCase):
    def test_featured_images_survive_regeneration(self):
        for filename in ("featured.jpg", "featured.jpeg", "featured.png", "FEATURED.PNG"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                pub = Path(tmp)
                (pub / "cite.bib").write_text('@article{test,\n journal = {Test Journal},\n}\n')
                index = pub / "index.md"
                generated = '---\ntitle: Test\npublication_types:\n- article-journal\n---\nBody\n'
                (pub / filename).touch()
                for source in (generated, generated.replace("title: Test", "title: Test\nfeatured: false")):
                    index.write_text(source)
                    self.assertTrue(process_publication_dir(pub))
                    result = index.read_text()
                    self.assertEqual(result.count("featured: true"), 1)
                    self.assertNotIn("featured: false", result)
                    self.assertTrue(result.endswith("---\nBody\n"))
                    self.assertFalse(process_publication_dir(pub))

    def test_no_image_does_not_select_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            pub = Path(tmp)
            (pub / "cite.bib").write_text('@article{test,\n}\n')
            index = pub / "index.md"
            index.write_text('---\ntitle: Test\n---\n')
            process_publication_dir(pub)
            self.assertNotIn("featured:", index.read_text())


if __name__ == "__main__":
    unittest.main()
