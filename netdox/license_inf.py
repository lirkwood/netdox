from bs4 import BeautifulSoup
import subprocess, re
import ps_api, utils


license_pattern = re.compile(r'(REPLACED )?(?P<domain>[\w.-]+)\s+-\s+')

def read(uri_summary, dns):
    id = uri_summary['id']

    title_match = re.match(license_pattern, uri_summary['title'])
    if title_match:
        domains = [title_match['domain']]
    else:
        domains = [uri_summary['title'].split()[0]]

    try:
        for alias in (dns[domains[0]].domains):
            domains.append(alias)
            # print(f'[INFO][license_inf.py] {domains[0]} matched on {alias}')
    except KeyError:
        domains[0] = "[ext] "+ domains[0]
        
    return (id, domains)
    

def fetch(dns):
    license_dict = {}
    # 187062 is the uri of the license folder in operations-license shared to operations-network
    license_xml = BeautifulSoup(ps_api.get_uris('187062'), 'lxml')
    for uri in license_xml("uri"):
        id, domains = read(uri, dns)
        license_dict[id] = domains
    
    return license_dict


def org(license_id):
    license_psml = BeautifulSoup(ps_api.get_fragment(license_id, '2'), 'lxml')
    org_id = license_psml.find(title='Organization').xref["uriid"]
    return org_id
    
