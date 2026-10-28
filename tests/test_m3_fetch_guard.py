"""Downloader cannot use third-party mirrors without explicit permission."""

import tempfile
from pathlib import Path
import unittest

from research.m3_fetch_dev_data import fetch


class CommunityMirrorGateTests(unittest.TestCase):
    def test_mirror_must_be_explicitly_accepted_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "accept-community-mirror"):
                fetch(Path(d), accept_community_mirror=False)


if __name__ == "__main__":
    unittest.main()
