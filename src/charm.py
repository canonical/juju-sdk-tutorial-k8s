#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus
from ops.pebble import Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class FastAPIDemoCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.pebble_service_name = "fastapi-service"
        self.framework.observe(self.on.demo_server_pebble_ready, self._on_demo_server_pebble_ready)

    def _on_demo_server_pebble_ready(self, event):
        """Define and start a workload using the Pebble API.

        Change this example to suit your needs. You'll need to specify the right entrypoint and
        environment configuration for your specific workload.

        Learn more about interacting with Pebble at at https://juju.is/docs/sdk/pebble.
        """
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload
        # Add initial Pebble config layer using the Pebble API
        container.add_layer("fastapi_demo", self._pebble_layer, combine=True)
        # Make Pebble reevaluate its plan, ensuring any services are started if enabled.
        container.replan()
        # Learn more about statuses in the SDK docs:
        # https://juju.is/docs/sdk/constructs#heading--statuses
        self.unit.status = ActiveStatus()

    @property
    def _pebble_layer(self):
        """Return a dictionary representing a Pebble layer."""
        command = " ".join(
            [
                "uvicorn",
                "api_demo_server.app:app",
                "--host=0.0.0.0",
                "--port=8000",
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
