"""aiomarketstack's testing package."""

import unittest

from . import test_aiomarketstack

ALL_TESTS = [
    unittest.defaultTestLoader.loadTestsFromModule(test_aiomarketstack),
]
