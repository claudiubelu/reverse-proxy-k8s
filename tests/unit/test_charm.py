# Copyright 2023 Claudiu Belu
# See LICENSE file for licensing details.

import unittest
from unittest import mock

import charm
from ops import model, testing


class TestCharm(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.harness = testing.Harness(charm.ReverseProxyK8SCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader()
        self.harness.begin_with_initial_hooks()

    def _patch(self, obj, method, *args, **kwargs):
        """Patches the given method and returns its Mock."""
        patcher = mock.patch.object(obj, method, *args, **kwargs)
        mock_patched = patcher.start()
        self.addCleanup(patcher.stop)

        return mock_patched

    def _add_relation(self, relation_name, relation_data):
        relator_name = "%s-relator" % relation_name
        rel_id = self.harness.add_relation(relation_name, relator_name)
        relator_unit = "%s/0" % relator_name
        self.harness.add_relation_unit(rel_id, relator_unit)
        self.harness.update_relation_data(rel_id, relator_name, relation_data)
        return rel_id

    def test_nginx_pebble_ready(self):
        # Get the nginx container from the model and emit the PebbleReadyEvent carrying it.
        # but we can't connect to the container yet.
        container = self.harness.model.unit.get_container("nginx")

        self.harness.charm.on.nginx_pebble_ready.emit(container)

        # No proxy-url config was set, so the status should be Blocked.
        self.assertIsInstance(self.harness.model.unit.status, model.BlockedStatus)
        updated_plan = self.harness.get_container_pebble_plan("nginx").to_dict()
        expected_plan = {
            "services": {
                "nginx": {
                    "override": "replace",
                    "summary": "nginx",
                    "command": "/docker-entrypoint.sh nginx -g 'daemon off;'",
                    "startup": "enabled",
                },
            },
        }
        self.assertDictEqual(expected_plan, updated_plan)

        # Set the proxy-url config option and reemit the  PebbleReadyEvent. The charm
        # should become Active.
        mock_override_nginx_config = self._patch(
            charm.ReverseProxyK8SCharm, "_override_nginx_config"
        )
        self.harness.update_config({"proxy-url": "foo.lish"})

        self.harness.charm.on.nginx_pebble_ready.emit(container)

        self.assertEqual(self.harness.model.unit.status, model.ActiveStatus())
        mock_override_nginx_config.assert_called_with(container)

    def test_config_changed(self):
        container = self.harness.model.unit.get_container("nginx")
        mock_can_connect = self._patch(container, "can_connect")
        mock_can_connect.return_value = False
        mock_get_services = self._patch(container.pebble, "get_services")
        mock_get_services.return_value = []

        self.harness.update_config()

        # It should be waiting for Pebble to be ready.
        self.assertIsInstance(self.harness.charm.unit.status, model.WaitingStatus)

        mock_can_connect.return_value = True
        self.harness.update_config()

        # It should still be in a Waiting status, the service list is empty, typically
        # happens because update hook can be executed before the pebble ready hook.
        self.assertIsInstance(self.harness.charm.unit.status, model.WaitingStatus)

        mock_get_services.return_value = [mock.sentinel.service]
        self.harness.update_config()

        # Assert that the unit is currently blocked, because the 'proxy-url'
        # config option is not set.
        self.assertIsInstance(self.harness.charm.unit.status, model.BlockedStatus)

        # The needed config option is set, the charam should now be Active.
        self._patch(charm.ReverseProxyK8SCharm, "_override_nginx_config")
        self.harness.update_config({"proxy-url": "foo.lish"})
        self.assertIsInstance(self.harness.charm.unit.status, model.ActiveStatus)

        relation_id = self._add_relation("ingress", {})
        relation_data = self.harness.get_relation_data(relation_id, self.harness.charm.app)
        self.harness.update_config()

        # Default values set in the relation, based on the default config option values.
        expected_data = {
            "host": self.harness.charm.app.name,
            "name": self.harness.charm.app.name,
            "port": "80",
            "service-hostname": self.harness.charm.app.name,
            "service-name": self.harness.charm.app.name,
            "service-port": "80",
            "path-routes": "/",
            "rewrite-enabled": "True",
        }
        self.assertDictEqual(expected_data, relation_data)

        updated_configs = {
            "service-hostname": "foo.lish",
            "service-port": 8080,
            "path-routes": "/foo",
            "rewrite-enabled": False,
        }
        self.harness.update_config(updated_configs)

        relation_data = self.harness.get_relation_data(relation_id, self.harness.charm.app)
        expected_data = {
            "host": "foo.lish",
            "name": self.harness.charm.app.name,
            "port": "8080",
            "service-hostname": "foo.lish",
            "service-name": self.harness.charm.app.name,
            "service-port": "8080",
            "path-routes": "/foo",
            "rewrite-enabled": "False",
        }
        self.assertDictEqual(expected_data, relation_data)
        self.assertDictEqual(expected_data, relation_data)

        self.assertIsInstance(self.harness.charm.unit.status, model.ActiveStatus)

    def test_override_nginx_config(self):
        mock_container = mock.Mock()

        self.harness.charm._override_nginx_config(mock_container)

        mock_container.pull.assert_called_once_with(charm._NGINX_CONFD_DEFAULT)
        expected_config = charm._NGINX_CONFIG_TEMPLATE % {
            "proxy_url": self.harness.charm.config["proxy-url"],
            "header_host": self.harness.charm.config["header-host"],
        }
        mock_container.push.assert_called_once_with(charm._NGINX_CONFD_DEFAULT, expected_config)
        mock_container.restart.assert_called_once_with("nginx")

        # Check that a new configuration is not pushed if it's already the same.
        mock_container.reset_mock()
        mock_container.pull.return_value.read.return_value = expected_config

        self.harness.charm._override_nginx_config(mock_container)

        mock_container.push.assert_not_called()
