import datetime
import logging
import socket

logger = logging.getLogger("netcheck.tcp")
DEFAULT_TCP_VALIDATION_RULE = """
data.connected == true
"""


def tcp_check(host: str, port: int, timeout: float = 5) -> dict:
    test_spec = {
        "type": "tcp",
        "host": host,
        "port": port,
        "timeout": timeout,
    }

    result_data = {
        "startTimestamp": datetime.datetime.utcnow().isoformat(),
    }

    output = {"spec": test_spec, "data": result_data}

    try:
        with socket.create_connection((host, port), timeout=timeout):
            result_data["connected"] = True
            result_data["error"] = None
    except socket.timeout:
        logger.debug(f"TCP connection to {host}:{port} timed out")
        result_data["connected"] = False
        result_data["error"] = f"Connection timed out after {timeout}s"
    except ConnectionRefusedError:
        logger.debug(f"TCP connection to {host}:{port} refused")
        result_data["connected"] = False
        result_data["error"] = f"Connection refused to {host}:{port}"
    except OSError as e:
        logger.debug(f"TCP connection to {host}:{port} failed: {e}")
        result_data["connected"] = False
        result_data["error"] = str(e)

    result_data["endTimestamp"] = datetime.datetime.utcnow().isoformat()

    return output
