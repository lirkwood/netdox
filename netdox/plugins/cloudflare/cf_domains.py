import json, requests
import utils

def main(forward: dict[str, utils.DNSRecord], reverse: dict[str, utils.DNSRecord]):
    """
    Returns tuple containing forward and reverse DNS records from Cloudflare
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
    global base
    base = "https://api.cloudflare.com/client/v4/"

    global header
    header = {
        "Authorization": f"Bearer {utils.auth['plugins']['cloudflare']['token']}",
        "Content-Type": "application/json"
    }


def fetch_zones():
    """
    Generator which returns one zone ID
    """
    service = "zones"
    response = requests.get(base+service, headers=header).text
    zones = json.loads(response)['result']
    for zone in zones:
        yield zone['id']


@utils.handle
def add_A(dns_set: dict[str, utils.DNSRecord], record: dict):
    """
    Integrates one A record into a dns set from json returned by Cloudflare api
    """
    fqdn = record['name'].lower()
    root = record['zone_name']
    ip = record['content']

    if fqdn not in dns_set:
        dns_set[fqdn] = utils.DNSRecord(fqdn, root)
    dns_set[fqdn].link(ip, 'ipv4', 'Cloudflare')

@utils.handle
def add_CNAME(dns_set: dict[str, utils.DNSRecord], record: dict):
    """
    Integrates one CNAME record into a dns set from json returned by Cloudflare api
    """
    fqdn = record['name'].lower()
    root = record['zone_name']
    dest = record['content']

    if fqdn not in dns_set:
        dns_set[fqdn] = utils.DNSRecord(fqdn, root)
    dns_set[fqdn].link(dest, 'domain', 'Cloudflare')

@utils.handle
def add_PTR(dns_set: dict[str, utils.DNSRecord], record: dict):
    """
    Integrates one PTR record into a dns set from json returned by Cloudflare api
    """
    # Not implemented - Cloudflare recommends against using PTR outside of PTR zones

if __name__ == '__main__':
    forward, reverse = main()