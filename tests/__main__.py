"""Run the aiomarketstack test suite."""
import unittest

from . import ALL_TESTS

unittest.TextTestRunner().run(*ALL_TESTS)
