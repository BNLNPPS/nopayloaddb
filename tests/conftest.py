"""Make the repo root importable. These tests cover the pure logic -- statistics,
snapshot arithmetic, postconditions, verdicts -- with no Django and no database."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
