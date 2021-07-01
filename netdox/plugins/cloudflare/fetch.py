"""
Fetching data
*************

Used to read DNS records from CloudFlare.

Requests all managed DNS zones and then all records in each zone.
"""
import json

import requests
import utils
from networkobjs import Domain, Network


def main(network: Network) -> None:
    """
    Reads all DNS records from CloudFlare and adds them to forward/reverse

	:Args:
		network:
			A Network object
    """
    init()
    for id in fetch_zones():
        service = f'zones/{id}/dns_records'
        response = requests.get(base+service, headers=header).text
        records = json.loads(response)['result']
        for record in records:
            if record['type'] == 'A':
                add_A(network, record)
            elif record['type'] == 'CNAME':
                add_CNAME(network, record)
            elif record['type'] == 'PTR':
                add_PTR(network, record)


def init() -> None:
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


def fetch_zones() -> str:
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
def add_A(network: Network, record: dict) -> None:
    """
    Integrates one A record into a Network from json returned by DNSME api

    :Args:
		network:
			A Network object
        record: dict
            Some JSON describing a DNS record
        root: str
            The root domain the record comes from
    """
    fqdn = record['name'].lower()
    root = record['zone_name']
    ip = record['content']

    if fqdn not in network.domains:
        network.add(Domain(fqdn, root))
    network.domains[fqdn].link(ip, 'Cloudflare')	

@utils.handle
def add_CNAME(network: Network, record: dict) -> None:
    """
    Integrates one CNAME record into a Network from json returned by CloudFlare api

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

    if fqdn not in network.domains:
        network.add(Domain(fqdn, root))
    network.domains[fqdn].link(dest, 'Cloudflare')

@utils.handle
def add_PTR(network: Network, record: dict) -> None:
    """
    Not Implemented
    """
    # Not implemented - Cloudflare recommends against using PTR outside of PTR zones
    raise NotImplementedError

if __name__ == '__main__':
    forward, reverse = main()
