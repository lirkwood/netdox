from bs4 import BeautifulSoup
import ps_api, re


license_pattern = re.compile(r'(REPLACED )?(?P<domain>[\w.-]+)\s+-\s+')

def fetch():
    license_dict = {}
    # 187062 is the uri of the license folder in operations-license shared to operations-network
    license_xml = BeautifulSoup(ps_api.get_uris('187062'), 'lxml')
    for uri in license_xml("uri"):
        id = uri['id']

        title_match = re.match(license_pattern, uri['title'])
        if title_match:
            domain = title_match['domain']
        else:
            domain = uri['title'].split()[0]

        license_dict[domain] = id
    
    return license_dict


def org(license_id):
    license_psml = BeautifulSoup(ps_api.get_fragment(license_id, '2'), 'lxml')
    org_id = license_psml.find(title='Organization').xref["uriid"]
    return org_id
    
