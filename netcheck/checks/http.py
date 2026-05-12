import datetime
import logging
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel
import urllib3
from urllib3.poolmanager import PoolManager

# We disable urllib warning because we expect to be carrying out tests against hosts using self-signed
# certs etc.
urllib3.disable_warnings()


import requests  # noqa: E402
from requests.adapters import HTTPAdapter  # noqa: E402


class _SourceAddressAdapter(HTTPAdapter):
    """HTTPAdapter that binds outgoing connections to a specific source IP."""

    def __init__(self, source_address: str, **kwargs):
        self._source_address = (source_address, 0)
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["source_address"] = self._source_address
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs
        )


logger = logging.getLogger("netcheck.http")
DEFAULT_HTTP_VALIDATION_RULE = """
data['status-code'] in [200, 201]
"""


class NetcheckHttpHeaderType(str, Enum):
    bearer = "bearer"


class NetcheckHttpHeaders(BaseModel):
    name: str
    value: str
    type: Optional[NetcheckHttpHeaderType] = None


class NetcheckHttpMethod(str, Enum):
    get = "get"
    post = "post"
    patch = "patch"
    put = "put"
    delete = "delete"


def http_request_check(
    url,
    method: NetcheckHttpMethod = "get",
    headers: Dict[str, str] = None,
    timeout=5,
    verify: bool = True,
    source_ip: Optional[str] = None,
):
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "netcheck"

    # This structure gets stored along with the test results
    test_spec = {
        "type": "http",
        "timeout": timeout,
        "verify-tls-cert": verify,
        "method": method,
        "headers": headers,
        "url": url,
    }
    if source_ip is not None:
        test_spec["source-ip"] = source_ip

    result_data = {
        "startTimestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    output = {"spec": test_spec, "data": result_data}

    # Prepare the arguments for requests
    requests_kwargs = {
        "timeout": test_spec["timeout"],
        "verify": test_spec["verify-tls-cert"],
        "headers": test_spec["headers"],
    }

    session = requests.Session()
    if source_ip is not None:
        adapter = _SourceAddressAdapter(source_ip)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

    try:
        response = session.request(method, url, **requests_kwargs)
        result_data["status-code"] = response.status_code
        result_data["headers"] = dict(response.headers)
        result_data["body"] = response.text
        response.raise_for_status()
    except Exception as e:
        logger.debug(f"Caught exception:\n\n{e}")
        result_data["exception-type"] = e.__class__.__name__
        result_data["exception"] = str(e)

    result_data["endTimestamp"] = datetime.datetime.now(datetime.UTC).isoformat()

    return output
