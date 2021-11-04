"""
Fetching data
*************

Used to read DNS records from CloudFlare.

Requests all managed DNS zones and then all records in each zone.
"""
import json
from typing import Generator

import requests
from netdox import utils
from netdox.objs import Domain, Network


def main(network: Network) -> None:
    """
    Reads all DNS records from CloudFlare and adds them to the network.

    :param network: The network.
    :type network: Network
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
        "Authorization": f"Bearer {utils.config('cloudflare')['token']}",
        "Content-Type": "application/json"
    }


def fetch_zones() -> Generator[str, None, None]:
    """
    Generator which yields one DNS zone ID

    :yield: The ID of one managed DNS zone in CloudFlare
    :rtype: Generator[str, None, None]
    """
    service = "zones"
    response = requests.get(base+service, headers=header).text
    zones = json.loads(response)['result']
    for zone in zones:
        yield zone['id']


@utils.handle
def add_A(network: Network, record: dict) -> None:
    """
    Integrates one A record into a Network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing information about an A record.
    :type record: dict
    """
    fqdn = record['name'].lower()
    ip = record['content']

    if fqdn not in network.exclusions:
        network.domains[fqdn].link(ip, 'Cloudflare')	

@utils.handle
def add_CNAME(network: Network, record: dict) -> None:
    """
    Integrates one CNAME record into a Network from a dictionary.

    :param network: The network.
    :type network: Network
    :param record: A dictionary containing information about an CNAME record.
    :type record: dict
    """
    fqdn = record['name'].lower()
    root = record['zone_name']
    dest = record['content']

    if fqdn not in network.exclusions:
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
