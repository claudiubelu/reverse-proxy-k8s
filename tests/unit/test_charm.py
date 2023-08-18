# Copyright 2023 Claudiu Belu
# See LICENSE file for licensing details.

import unittest

import charm
from ops import model, testing


class TestCharm(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.harness = testing.Harness(charm.ReverseProxyK8SCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader()
        self.harness.begin_with_initial_hooks()

    def test_config_changed(self):
        # Assert that the unit is currently active.
        self.assertIsInstance(self.harness.charm.unit.status, model.ActiveStatus)
