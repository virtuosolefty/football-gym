import unittest
from tools.prepare_public_labels import parse_boxes


class PublishedLabelsTests(unittest.TestCase):
    def test_empty_file_is_absent_but_malformed_or_nonfinite_boxes_are_refused(self):
        self.assertEqual(parse_boxes(""), [])
        self.assertEqual(parse_boxes("0 0.5 0.3 0.02 0.04\n"), [[0, .5, .3, .02, .04]])
        for text in ("0 .5 .3 .2", "0 nan .3 .2 .2", "0 .5 .3 -1 .2", "0 .5 2 .2 .2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_boxes(text)
