#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the application."""

import logging

import ops

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class FastAPIDemoCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        self.pebble_service_name = "fastapi-service"
        self.container = self.unit.get_container(
            "demo-server"
        )  # see 'containers' in charmcraft.yaml
        framework.observe(self.on.demo_server_pebble_ready, self._on_demo_server_pebble_ready)
        framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_config_changed(self, event: ops.ConfigChangedEvent) -> None:
        port = self.config["server-port"]  # see charmcraft.yaml
        logger.debug("New application port is requested: %s", port)

        if port == 22:
            self.unit.status = ops.BlockedStatus("Invalid port number, 22 is reserved for SSH")
            return

        self._update_layer_and_restart()

    def _on_demo_server_pebble_ready(self, event: ops.PebbleReadyEvent) -> None:
        self._update_layer_and_restart()

    def _update_layer_and_restart(self) -> None:
        """Define and start a workload using the Pebble API.

        You'll need to specify the right entrypoint and environment
        configuration for your specific workload. Tip: you can see the
        standard entrypoint of an existing container using docker inspect

        Learn more about interacting with Pebble at https://juju.is/docs/sdk/pebble
        Learn more about Pebble layers at
            https://canonical-pebble.readthedocs-hosted.com/en/latest/reference/layers
        """
        # Learn more about statuses in the SDK docs:
        # https://juju.is/docs/sdk/constructs#heading--statuses
        self.unit.status = ops.MaintenanceStatus("Assembling Pebble layers")
        try:
            # Get the current pebble layer config
            services = self.container.get_plan().to_dict().get("services", {})
            if services != self._pebble_layer.to_dict().get("services", {}):
                # Changes were made, add the new layer
                self.container.add_layer("fastapi_demo", self._pebble_layer, combine=True)
                logger.info("Added updated layer 'fastapi_demo' to Pebble plan")

                self.container.restart(self.pebble_service_name)
                logger.info(f"Restarted '{self.pebble_service_name}' service")

            self.unit.status = ops.ActiveStatus()
        except ops.pebble.APIError:
            self.unit.status = ops.MaintenanceStatus("Waiting for Pebble in workload container")

    @property
    def _pebble_layer(self) -> ops.pebble.Layer:
        """A Pebble layer for the FastAPI demo services."""
        command = " ".join(
            [
                "uvicorn",
                "api_demo_server.app:app",
                "--host=0.0.0.0",
                f"--port={self.config['server-port']}",
            ]
        )
        pebble_layer: ops.pebble.LayerDict = {
            "summary": "FastAPI demo service",
            "description": "pebble config layer for FastAPI demo server",
            "services": {
                self.pebble_service_name: {
                    "override": "replace",
                    "summary": "fastapi demo",
                    "command": command,
                    "startup": "enabled",
                }
            },
        }
        return ops.pebble.Layer(pebble_layer)


if __name__ == "__main__":  # pragma: nocover
    ops.main(FastAPIDemoCharm)
