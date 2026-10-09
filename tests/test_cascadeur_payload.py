"""The Cascadeur package and everything it imports ships in the zip."""

import os
import unittest

import install

PLUGIN = os.path.dirname(os.path.abspath(install.__file__))


class Payload(unittest.TestCase):

    def test_cascadeur_package_ships(self):
        self.assertIn("skeldar_cascadeur", install.payload())

    def test_shared_modules_ship(self):
        names = install.payload()
        self.assertIn("maya_sharenet.py", names)
        self.assertIn("maya_sharerecords.py", names)

    def test_uebridge_package_ships(self):
        self.assertIn("maya_uebridge", install.payload())

    def test_the_cascadeur_package_has_its_modules_on_disk(self):
        package = os.path.join(PLUGIN, "skeldar_cascadeur")
        for name in ("__init__.py", "rules.py", "prefs.py", "shared.py",
                     "unreal.py", "cascade_io.py", "actions.py", "window.py",
                     "bridge.py"):
            self.assertTrue(os.path.isfile(os.path.join(package, name)), name)


if __name__ == "__main__":
    unittest.main()
