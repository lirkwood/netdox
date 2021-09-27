from netdox.plugins.activedirectory import dns

## DNS

def test_parseDN():
    assert dns.parseDN(
        'DC=hostname,DC=zone.tld,cn=MicrosoftDNS,DC=DomainDnsZones,DC=domain,DC=component'
    ) == ('hostname.zone.tld', 'zone.tld')

    assert dns.parseDN(
        'DC=*,DC=zone.tld,cn=MicrosoftDNS,DC=DomainDnsZones,DC=domain,DC=component'
    ) == ('_wildcard_.zone.tld', 'zone.tld')

    assert dns.parseDN(
        'DC=@,DC=zone.tld,cn=MicrosoftDNS,DC=DomainDnsZones,DC=domain,DC=component'
    ) == ('zone.tld', 'zone.tld')

    assert dns.parseDN(
        'DC=hostname,DC=zone.tld,cn=MicrosoftDNS,DC=DomainDnsZones,DC=domain,DC=component'
    ) == ('hostname.zone.tld', 'zone.tld')

    assert dns.parseDN('invalid.distinguished_name') == (None, None)