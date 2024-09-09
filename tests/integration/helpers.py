import socket
from pytest_operator.plugin import OpsTest


async def get_address(ops_test: OpsTest, app_name: str, unit_num: int = 0) -> str:
    """Get the address for a the k8s service for an app."""
    status = await ops_test.model.get_status()
    k8s_service_address = status["applications"][app_name].public_address
    return k8s_service_address

def is_port_open(host: str, port: int) -> bool:
    """check if a port is opened in a particular host"""
    try:
        with socket.create_connection((host, port), timeout=5):
            return True  # If connection succeeds, the port is open
    except (ConnectionRefusedError, TimeoutError):
        return False  # If connection fails, the port is closed
