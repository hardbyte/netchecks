import datetime
import logging

import dns.resolver

logger = logging.getLogger("netcheck.dns")


def get_A_records_by_dns_lookup(target, nameserver=None, timeout=60):
    # We always reset the default dns resolver
    dns.resolver.reset_default_resolver()
    resolver = dns.resolver.get_default_resolver()

    A_records = []

    if nameserver is not None:
        resolver.nameservers = [nameserver]

    # this resolver can also be used with the default nameserver
    # search=True is required to use the OS search path!
    # E.g. `kubernetes` -> `kubernetes.default.svc.cluster.local`
    result = resolver.resolve(target, 'A', lifetime=timeout, search=True)

    for IPval in result:
        A_records.append(IPval.to_text())

    return A_records


def dns_lookup_check(host, server, timeout=10, should_fail=False):

    test_spec = {
        'type': 'dns',
        'shouldFail': should_fail,
        'nameserver': server,
        'host': host,
        'timeout': timeout,
    }
    result_data = {
        'startTimestamp': datetime.datetime.utcnow().isoformat(),
    }

    output = {
        'status': 'error',
        'spec': test_spec,
        'data': result_data
    }

    try:
        ip_addresses = get_A_records_by_dns_lookup(host, nameserver=server, timeout=timeout)
        result_data['A'] = ip_addresses
        output['status'] = 'pass' if not should_fail else 'fail'
    except Exception as e:
        logger.info(f"Caught exception:\n\n{e}")
        output['status'] = 'pass' if should_fail else 'fail'
        result_data['exception-type'] = e.__class__.__name__
        result_data['exception'] = str(e)

    result_data['endTimestamp'] = datetime.datetime.utcnow().isoformat()

    return output
