#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
import json
import logging
from typing import Any

import ops
import requests
from charms.data_platform_libs.v0.data_interfaces import DatabaseCreatedEvent
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

PEER_NAME = "fastapi-peer"


class FastAPIDemoCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework):
        super().__init__(framework)
        self.pebble_service_name = "fastapi-service"
        self.container = self.unit.get_container(
            "demo-server"
        )  # see 'containers' in charmcraft.yaml

        # Charm events defined in the database requires charm library.
        self.database = DatabaseRequires(self, relation_name="database", database_name="names_db")
        framework.observe(self.database.on.database_created, self._on_database_created)
        framework.observe(self.database.on.endpoints_changed, self._on_database_created)

        framework.observe(self.on.demo_server_pebble_ready, self._update_layer_and_restart)
        framework.observe(self.on.config_changed, self._on_config_changed)
        framework.observe(self.on.collect_unit_status, self._on_collect_status)
        framework.observe(self.on.start, self._count)

    def _on_collect_status(self, event):
        port = self.config["server-port"]
        if port == 22:
            event.add_status(ops.BlockedStatus("Invalid port number, 22 is reserved for SSH"))
        if not self.model.get_relation("database"):
            # We need the user to do 'juju integrate'.
            event.add_status(ops.BlockedStatus("Waiting for database relation"))
        elif not self.database.fetch_relation_data():
            # We need the charms to finish integrating.
            event.add_status(ops.WaitingStatus("Waiting for database relation"))
        try:
            status = self.container.get_service(self.pebble_service_name)
        except (ops.pebble.APIError, ops.ModelError):
            event.add_status(ops.MaintenanceStatus("Waiting for Pebble in workload container"))
        else:
            if not status.is_running():
                event.add_status(ops.MaintenanceStatus("Waiting for the service to start up"))
        # If nothing is wrong, then the status is active.
        event.add_status(ops.ActiveStatus())

    def _on_config_changed(self, event):
        port = self.config["server-port"]  # see charmcraft.yaml
        logger.debug("New application port is requested: %s", port)

        if port == 22:
            logger.info("Invalid port number, 22 is reserved for SSH")
            return

        self._update_layer_and_restart(None)

    def _count(self, event) -> None:
        """This function updates a counter for the number of times a K8s pod has been started.

        It retrieves the current count of pod starts from the 'unit_stats' peer relation data,
        increments the count, and then updates the 'unit_stats' data with the new count.
        """
        unit_stats = self.get_peer_data("unit_stats")
        counter = unit_stats.get("started_counter", 0)
        self.set_peer_data("unit_stats", {"started_counter": int(counter) + 1})

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        """Event is fired when postgres database is created."""
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
        self.unit.status = ops.MaintenanceStatus("Assembling Pebble layers")
        new_layer = self._pebble_layer.to_dict()
        try:
            # Get the current pebble layer config
            services = self.container.get_plan().to_dict().get("services", {})
            if services != new_layer["services"]:
                # Changes were made, add the new layer
                self.container.add_layer("fastapi_demo", self._pebble_layer, combine=True)
                logger.info("Added updated layer 'fastapi_demo' to Pebble plan")

                self.container.restart(self.pebble_service_name)
                logger.info(f"Restarted '{self.pebble_service_name}' service")
        except ops.pebble.APIError as e:
            logger.info("Unable to connect to Pebble: %s", e)
            return
        # Add workload version in Juju status.
        self.unit.set_workload_version(self.version)

    @property
    def app_environment(self):
        """This property method creates a dictionary containing environment variables
        for the application. It retrieves the database authentication data by calling
        the `fetch_postgres_relation_data` method and uses it to populate the dictionary.
        If any of the values are not present, it will be set to None.
        The method returns this dictionary as output.
        """
        db_data = self.fetch_postgres_relation_data()
        if not db_data:
            return {}
        env = {
            "DEMO_SERVER_DB_HOST": db_data.get("db_host", None),
            "DEMO_SERVER_DB_PORT": db_data.get("db_port", None),
            "DEMO_SERVER_DB_USER": db_data.get("db_username", None),
            "DEMO_SERVER_DB_PASSWORD": db_data.get("db_password", None),
        }
        return env

    def fetch_postgres_relation_data(self) -> dict:
        """Fetch postgres relation data.

        This function retrieves relation data from a postgres database using
        the `fetch_relation_data` method of the `database` object. The retrieved data is
        then logged for debugging purposes, and any non-empty data is processed to extract
        endpoint information, username, and password. This processed data is then returned as
        a dictionary. If no data is retrieved, the unit is set to waiting status and
        the program exits with a zero status code."""
        relations = self.database.fetch_relation_data()
        logger.debug("Got following database data: %s", relations)
        for data in relations.values():
            if not data:
                continue
            logger.info("New PSQL database endpoint is %s", data["endpoints"])
            host, port = data["endpoints"].split(":")
            db_data = {
                "db_host": host,
                "db_port": port,
                "db_username": data["username"],
                "db_password": data["password"],
            }
            return db_data
        return {}

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
                    "environment": self.app_environment,
                }
            },
        }
        return ops.pebble.Layer(pebble_layer)

    @property
    def version(self) -> str:
        """Reports the current workload (FastAPI app) version."""
        try:
            if self.container.get_services(self.pebble_service_name):
                return self._request_version()
        # Catching Exception is not ideal, but we don't care much for the error here, and just
        # default to setting a blank version since there isn't much the admin can do!
        except Exception as e:
            logger.warning("unable to get version from API: %s", str(e), exc_info=True)
        return ""

    def _request_version(self) -> str:
        """Helper for fetching the version from the running workload using the API."""
        resp = requests.get(f"http://localhost:{self.config['server-port']}/version", timeout=10)
        return resp.json()["version"]

    @property
    def peers(self):
        """Fetch the peer relation."""
        return self.model.get_relation(PEER_NAME)

    def set_peer_data(self, key: str, data: Any) -> None:
        """Put information into the peer data bucket instead of `StoredState`."""
        self.peers.data[self.app][key] = json.dumps(data)

    def get_peer_data(self, key: str) -> dict[Any, Any]:
        """Retrieve information from the peer data bucket instead of `StoredState`."""
        if not self.peers:
            return {}
        data = self.peers.data[self.app].get(key, "")
        return json.loads(data) if data else {}


if __name__ == "__main__":  # pragma: nocover
    ops.main(FastAPIDemoCharm)
