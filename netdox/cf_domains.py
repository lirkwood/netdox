import json, requests
import utils

@utils.handle
def main():
    """
    Returns tuple containing forward and reverse DNS records from Cloudflare
    """
    init()
    forward = {}
    reverse = {}
    for id in fetch_zones():
        service = f'zones/{id}/dns_records'
        response = requests.get(base+service, headers=header).text
        records = json.loads(response)['result']
        for record in records:
            if record['type'] == 'A':
                forward = add_A(forward, record)
            elif record['type'] == 'CNAME':
                forward = add_CNAME(forward, record)
            elif record['type'] == 'PTR':
                reverse = add_PTR(reverse, record)
    
    return (forward, reverse)


def init():
    global base
    base = "https://api.cloudflare.com/client/v4/"

    with open('src/authentication.json') as authstream:
        creds = json.load(authstream)['cloudflare']

    global header
    header = {
        "Authorization": f"Bearer {creds['token']}",
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


@utils.mod_set
def add_A(dns_set, record):
    """
    Integrates one A record into a dns set from json returned by Cloudflare api
    """
    fqdn = record['name']
    root = record['zone_name']
    ip = record['content']

    if fqdn not in dns_set:
        dns_set[fqdn] = utils.dns(fqdn, root, 'Cloudflare')
    dns_set[fqdn].link(ip, 'ipv4')

    return dns_set

@utils.mod_set
def add_CNAME(dns_set, record):
    """
    Integrates one CNAME record into a dns set from json returned by Cloudflare api
    """
    fqdn = record['name']
    root = record['zone_name']
    dest = record['content']

    if fqdn not in dns_set:
        dns_set[fqdn] = utils.dns(fqdn, root, 'Cloudflare')
    dns_set[fqdn].link(dest, 'domain')

    return dns_set

@utils.mod_set
def add_PTR(dns_set, record):
    """
    Integrates one PTR record into a dns set from json returned by Cloudflare api
    """
    # Not implemented - Cloudflare recommends against using PTR
    return dns_set

if __name__ == '__main__':
    forward, reverse = main()