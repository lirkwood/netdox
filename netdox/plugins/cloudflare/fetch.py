"""
Fetching data
*************

Used to read DNS records from CloudFlare.

Requests all managed DNS zones and then all records in each zone.
"""
import json, requests
import utils

def main(forward: utils.DNSSet, reverse: utils.DNSSet):
    """
    Reads all DNS records from CloudFlare and adds them to forward/reverse

	:Args:
		forward: DNSSet
			A forward DNS set
		reverse: DNSSet
			A reverse DNS set
    """
    init()
    for id in fetch_zones():
        service = f'zones/{id}/dns_records'
        response = requests.get(base+service, headers=header).text
        records = json.loads(response)['result']
        for record in records:
            if record['type'] == 'A':
                add_A(forward, record)
            elif record['type'] == 'CNAME':
                add_CNAME(forward, record)
            elif record['type'] == 'PTR':
                add_PTR(reverse, record)


def init():
    """
    Defines some global variables for usage in the plugin
    """
    global base
    base = "https://api.cloudflare.com/client/v4/"

    global header
    header = {
        "Authorization": f"Bearer {utils.auth()['plugins']['cloudflare']['token']}",
        "Content-Type": "application/json"
    }


def fetch_zones():
    """
    Generator which returns one zone ID

    :Yields:
        The ID of a DNS zone in CloudFlare
    """
    service = "zones"
    response = requests.get(base+service, headers=header).text
    zones = json.loads(response)['result']
    for zone in zones:
        yield zone['id']


@utils.handle
def add_A(dns_set: utils.DNSSet, record: dict):
    """
    Integrates one A record into a dns set from json returned by DNSME api

    :Args:
        dns_set: DNSSet
            A forward DNS set
        record: dict
            Some JSON describing a DNS record
        root: str
            The root domain the record comes from
    """
    fqdn = record['name'].lower()
    root = record['zone_name']
    ip = record['content']

    if fqdn not in dns_set:
        dns_set.add(utils.DNSRecord(fqdn, root))
    dns_set[fqdn].link(ip, 'ipv4', 'Cloudflare')

@utils.handle
def add_CNAME(dns_set: utils.DNSSet, record: dict):
    """
    Integrates one CNAME record into a dns set from json returned by CloudFlare api

    :Args:
        dns_set: DNSSet
            A forward DNS set
        record: dict
            Some JSON describing a DNS record
        root: str
            The root domain the record comes from
    """
    fqdn = record['name'].lower()
    root = record['zone_name']
    dest = record['content']

    if fqdn not in dns_set:
        dns_set.add(utils.DNSRecord(fqdn, root))
    dns_set[fqdn].link(dest, 'domain', 'Cloudflare')

@utils.handle
def add_PTR(dns_set: utils.DNSSet, record: dict):
    """
    Not Implemented
    """
    # Not implemented - Cloudflare recommends against using PTR outside of PTR zones

if __name__ == '__main__':
    forward, reverse = main()