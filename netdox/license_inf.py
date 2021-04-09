from bs4 import BeautifulSoup
import subprocess, re
import ps_api, utils


license_pattern = re.compile(r'(REPLACED )?(?P<domain>[\w.-]+)\s+-\s+')

@utils.handle
def read(uri, dns):
    id = uri['id']

    title_match = re.match(license_pattern, uri['title'])
    if title_match:
        domains = [title_match['domain']]
    else:
        domains = [uri['title'].split()[0]]

    try:
        subprocess.check_output(f'ping -c 1 -w 2 {domains[0]}', shell=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        domains[0] = "[old] "+ domains[0]
    else:
        try:
            for alias in (dns[domains[0]]['dest']['domains'] + dns[domains[0]]['dest']['nat']):
                domains.append(alias)
                # print(f'[INFO][license_inf.py] {domains[0]} matched on {alias}')
        except KeyError:
            domains[0] = "[ext] "+ domains[0]
    finally:
        return (id, domains)
    
@utils.handle
def fetch(dns):
    license_dict = {}
    # 187062 is the uri of the license folder in operations-license shared to operations-network
    license_xml = BeautifulSoup(ps_api.get_uris('187062'), 'lxml')
    for uri in license_xml("uri"):
        uri_inf = read(uri, dns)
        license_dict[uri_inf[0]] = uri_inf[1]
    
    return license_dict