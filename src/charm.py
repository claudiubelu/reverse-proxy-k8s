#!/usr/bin/env python3
# Copyright 2023 Claudiu Belu
# See LICENSE file for licensing details.

"""Charm the reverse proxy service.

Charm that creates an ingress route for an ExternalName Kubernetes Service
through the ingress relation.
"""

import logging

import ops
from charms.nginx_ingress_integrator.v0 import ingress

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

_NGINX_CONFD_DEFAULT = "/etc/nginx/conf.d/default.conf"

_NGINX_CONFIG_TEMPLATE = """
server {
    listen       80;
    listen  [::]:80;

    location / {
        proxy_pass %(proxy_url)s;
        proxy_set_header Host %(header_host)s;
        proxy_set_header x-Real-IP $remote_addr;
    }
}
"""


class ReverseProxyK8SCharm(ops.CharmBase):
    """Charm the reverse proxy service."""

    def __init__(self, *args):
        super().__init__(*args)
        # General hooks:
        self.framework.observe(self.on.nginx_pebble_ready, self._on_nginx_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

        # Setup Ingress.
        self.ingress = ingress.IngressRequires(self, self._get_ingress_config())

    def _on_nginx_pebble_ready(self, event):
        """Define and start the nginx Pebble Layer."""
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload

        # Create the current Pebble layer configuration
        pebble_layer = {
            "summary": "nginx layer",
            "description": "Pebble config layer for nginx.",
            "services": {
                "nginx": {
                    "override": "replace",
                    "summary": "nginx",
                    "command": "/docker-entrypoint.sh nginx -g 'daemon off;'",
                    "startup": "enabled",
                },
            },
        }

        # Add initial Pebble config layer using the Pebble API
        container.add_layer("nginx", pebble_layer, combine=True)

        self._update_charm_status(container)

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle changed configuration.

        The ingress relation data or the Kubernetes Service may need to be updated.
        """
        self._update_charm_status()

    def _update_charm_status(self, container=None):
        self.ingress.update_config(self._get_ingress_config())

        # If not provided with a container, get one.
        container = container or self.unit.get_container("nginx")
        if not container.can_connect() or not container.pebble.get_services():
            self.unit.status = ops.WaitingStatus("Waiting for Pebble to be ready")
            return

        if not self.config["proxy-url"]:
            self.unit.status = ops.BlockedStatus("proxy-url config option needs to be set.")
            container.stop("nginx")
            return

        self._override_nginx_config(container)

        self.unit.status = ops.ActiveStatus()

    def _get_ingress_config(self):
        return {
            "service-hostname": self.config["service-hostname"] or self.app.name,
            "service-name": self.app.name,
            "service-port": self.config["service-port"],
            # NOTE(claudiub): Comma-sepparated list of routes we want routed to this app.
            "path-routes": self.config["path-routes"],
            # NOTE(claudiub): If this option is enabled, the requests that match the paths
            # above would be rewritten to "rewrite-target" (/ by default), which we do not
            # need.
            "rewrite-enabled": self.config["rewrite-enabled"],
        }

    def _override_nginx_config(self, container):
        new_config = _NGINX_CONFIG_TEMPLATE % {
            "proxy_url": self.config["proxy-url"],
            "header_host": self.config["header-host"],
        }
        config = container.pull(_NGINX_CONFD_DEFAULT).read()

        if new_config == config:
            # The configuration is already the same, no need to update it.
            return

        container.push(_NGINX_CONFD_DEFAULT, new_config)
        container.restart("nginx")


if __name__ == "__main__":  # pragma: nocover
    ops.main(ReverseProxyK8SCharm)  # type: ignore
