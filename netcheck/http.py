import datetime
import logging
from enum import Enum
from typing import Dict, Optional

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("netcheck.http")


class NetcheckHttpHeaderType(str, Enum):
    bearer = "bearer"


class NetcheckHttpHeaders(BaseModel):
    name: str
    value: str
    type: Optional[NetcheckHttpHeaderType] = None


class NetcheckHttpMethod(str, Enum):
    get = 'get'
    post = 'post'
    patch = 'patch'
    put = 'put'
    delete = 'delete'


def http_request_check(
        url,
        method: NetcheckHttpMethod = 'get',
        headers: Dict[str, str] = None,
        timeout=5,
        verify: bool = True,
        should_fail: bool = False
):
    if headers is None:
        headers = {}
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'netcheck'

    # This structure gets stored along with the test results
    test_spec = {
        'type': 'http',
        'shouldFail': should_fail,
        'timeout': timeout,
        'verify-tls-cert': verify,
        'method': method,
        'headers': headers,
        'url': url,
    }

    result_data = {
        'startTimestamp': datetime.datetime.utcnow().isoformat(),
    }

    output = {
        'status': 'error',
        'spec': test_spec,
        'data': result_data
    }

    # Prepare the arguments for requests
    requests_kwargs = {
        'timeout': test_spec['timeout'],
        'verify': test_spec['verify-tls-cert'],
        'headers': test_spec['headers'],
    }

    try:
        response = getattr(requests, method)(url, **requests_kwargs)
        result_data['status-code'] = response.status_code
        result_data['headers'] = dict(response.headers)
        result_data['body'] = response.text
        response.raise_for_status()
        output['status'] = 'pass' if not should_fail else 'fail'
    except Exception as e:
        output['status'] = 'pass' if should_fail else 'fail'
        logger.debug(f"Caught exception:\n\n{e}")
        result_data['exception-type'] = e.__class__.__name__
        result_data['exception'] = str(e)

    result_data['endTimestamp'] = datetime.datetime.utcnow().isoformat()

    return output

