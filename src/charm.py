#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus
from ops.model import BlockedStatus
from ops.model import MaintenanceStatus
from ops.model import WaitingStatus
from ops.pebble import Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class FastAPIDemoCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.pebble_service_name = "fastapi-service"
        self.container = self.unit.get_container("demo-server")  # see 'containers' in metadata.yaml
        self.framework.observe(self.on.demo_server_pebble_ready, self._update_layer_and_restart)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_config_changed(self, event):
        port = self.config["server-port"]  # see config.yaml
        logger.debug("New application port is requested: %s", port)

        if int(port) == 22:
            self.unit.status = BlockedStatus("Invalid port number, 22 is reserved for SSH")
            return

        self._update_layer_and_restart(None)

    def _update_layer_and_restart(self, event) -> None:
        """Define and start a workload using the Pebble API.

        You'll need to specify the right entrypoint and environment
        configuration for your specific workload. Tip: you can see the
        standard entrypoint of an existing container using docker inspect

        Learn more about Pebble layers at https://github.com/canonical/pebble
        """

        # Learn more about statuses in the SDK docs:
        # https://juju.is/docs/sdk/constructs#heading--statuses
        self.unit.status = MaintenanceStatus("Assembling pod spec")
        if self.container.can_connect():
            new_layer = self._pebble_layer.to_dict()
            # Get the current pebble layer config
            services = self.container.get_plan().to_dict().get("services", {})
            if services != new_layer["services"]:
                # Changes were made, add the new layer
                self.container.add_layer("fastapi_demo", self._pebble_layer, combine=True)
                logger.info("Added updated layer 'fastapi_demo' to Pebble plan")

                self.container.restart(self.pebble_service_name)
                logger.info(f"Restarted '{self.pebble_service_name}' service")

            self.unit.status = ActiveStatus()
        else:
            self.unit.status = WaitingStatus("Waiting for Pebble in workload container")

    @property
    def _pebble_layer(self):
        """Return a dictionary representing a Pebble layer."""
        command = " ".join(
            [
                "uvicorn",
                "api_demo_server.app:app",
                "--host=0.0.0.0",
                f"--port={self.config['server-port']}",
            ]
        )
        pebble_layer = {
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
        return Layer(pebble_layer)


if __name__ == "__main__":  # pragma: nocover
    main(FastAPIDemoCharm)
