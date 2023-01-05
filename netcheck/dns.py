import dns.resolver


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

