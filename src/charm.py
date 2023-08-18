#!/usr/bin/env python3
# Copyright 2023 Claudiu Belu
# See LICENSE file for licensing details.

"""Charm the reverse proxy service."""

import logging

import ops

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class ReverseProxyK8SCharm(ops.CharmBase):
    """Charm the reverse proxy service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle changed configuration."""
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(ReverseProxyK8SCharm)  # type: ignore
