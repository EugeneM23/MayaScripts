"""Put the plugin folder on sys.path for the whole test run.

The shipped toolset lives in `SkeldarAnim/` (2026-09-01) -- the repo root
is the workshop and holds the standalone tools, the plugin folder holds
everything a colleague receives. Discovery runs with `-t .`, which gives
the repo root, so `import maya_overrig` needs one line and this is the
only place unittest is guaranteed to import before any test module.

Inserted at the FRONT, and after the repo root in effect: a stale
installed copy in the animator's prefs must never win over the tree the
tests are meant to be proving (CLAUDE.md note 9, from the other side).
"""

import os
import sys

_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")

if _PLUGIN not in sys.path:
    sys.path.insert(0, _PLUGIN)
