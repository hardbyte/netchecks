import dns.resolver



def get_A_records_by_dns_lookup(target, nameserver=None, timeout=60):

    # We always reset the default dns resolver
    dns.resolver.reset_default_resolver()
    resolver = dns.resolver.get_default_resolver()

    if nameserver is not None:
        resolver.nameservers = [nameserver]
    result = resolver.resolve(target, 'A', lifetime=timeout)
    A_records = []

    for IPval in result:
        A_records.append(IPval.to_text())
    return A_records

