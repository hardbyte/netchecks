import datetime
import logging
import socket
from typing import Optional

logger = logging.getLogger("netcheck.tcp")
DEFAULT_TCP_VALIDATION_RULE = """
data.connected == true
"""


def tcp_check(
    host: str, port: int, timeout: float = 5, source_ip: Optional[str] = None
) -> dict:
    test_spec = {
        "type": "tcp",
        "host": host,
        "port": port,
        "timeout": timeout,
    }
    if source_ip is not None:
        test_spec["source-ip"] = source_ip

    result_data = {
        "startTimestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    output = {"spec": test_spec, "data": result_data}

    source_address = (source_ip, 0) if source_ip is not None else None

    try:
        with socket.create_connection(
            (host, port), timeout=timeout, source_address=source_address
        ):
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

    result_data["endTimestamp"] = datetime.datetime.now(datetime.UTC).isoformat()

    return output
