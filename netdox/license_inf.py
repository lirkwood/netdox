"""
Used to read existing PageSeeder licenses through a shared group and link those licenses to the domain they were issued to.
"""

from bs4 import BeautifulSoup
import ps_api, re


license_pattern = re.compile(r'(REPLACED )?(?P<domain>[\w.-]+)\s+-\s+')

def fetch() -> dict[str, str]:
    """
    Reads every file in the PageSeeder license group and attempts to extract the issued domain from the title using RegEx.

    :Returns:
        A dictionary mapping domains to their PageSeeder license ID.
    """
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


def org(license_id: str) -> str:
    """
    Given the ID of a PageSeeder license, returns the organisation the license was issued for.

    :Returns:
        URI of the organisation document in the PageSeeder license group.
    """
    license_psml = BeautifulSoup(ps_api.get_fragment(license_id, '2'), 'lxml')
    org_id = license_psml.find(title='Organization').xref["uriid"]
    return org_id
    
