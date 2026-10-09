"""The Cascadeur character catalog. Stdlib only, no Cascadeur."""

import os
import unittest

from skeldar_cascadeur import characters


class Catalog(unittest.TestCase):

    def test_every_character_has_its_asset_on_disk(self):
        for character in characters.CHARACTERS:
            self.assertTrue(os.path.isfile(character.path), character.path)

    def test_labels_are_unique_and_match_the_rows(self):
        labels = characters.labels()
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels, [c.label for c in characters.CHARACTERS])

    def test_by_label_finds_and_refuses(self):
        self.assertEqual(characters.by_label("Manny UE5").key, "manny_ue5")
        self.assertIsNone(characters.by_label("Nobody"))

    def test_default_is_the_first_row(self):
        self.assertIs(characters.default(), characters.CHARACTERS[0])


if __name__ == "__main__":
    unittest.main()
