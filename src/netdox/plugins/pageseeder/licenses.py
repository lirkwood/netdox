import logging
from re import fullmatch
import json

from bs4 import BeautifulSoup
from netdox import Network, pageseeder, psml
from netdox.base import NetworkObject
from netdox.dns import DNSObject
from netdox.utils import dns_name_pattern

logger = logging.getLogger(__name__)

def runner(network: Network):
    # TODO change from ps to ps-licenses
    urimap = pageseeder.urimap('website/ps', 'document')
    cache: set[str] = set()
    for uri in urimap.values():
        license_soup = BeautifulSoup(pageseeder.get_default_uriid(uri).text, 'xml')
        details = psml.PropertiesFragment.from_tag(
            license_soup.find('section', id = 'details').find('properties-fragment')
        ).to_dict()

        domain = details['domain']
        try:
            if isinstance(domain, str):
                assert fullmatch(dns_name_pattern, domain)
            elif isinstance(domain, psml.XRef):
                domain = _domain_from_xref(domain)
            else:
                raise TypeError()
        
        except AssertionError:
            logger.warning(f'License with uri {uri} has invalid domain: {domain}')
        except AttributeError:
            logger.warning(f'Domain is unresolved xref in license with uri {uri}.')
        except TypeError:
            logger.warning(
                f'Unable to parse domain from PSML for license with uri {uri}.')
        else:
            license_type = details['license-type']
            org = None
            if isinstance(details['organization'], psml.XRef):
                xref = details['organization']
                if 'uriid' in xref.attrs:
                    org = xref['uriid']

            cache |= apply_licenses(network.find_dns(domain), 
                uri, license_type, org, cache)

def _domain_from_xref(input: psml.XRef) -> str:
    """
    Extracts the domain name from an XRef resolving to a domain document.

    :param input: An XRef object.
    :type input: Union[str, psml.XRef]
    :raises AttributeError: If the xref is unresolved.
    :raises ValueError: If a valid domain name cannot be extracted.
    :return: The domain name, as a string.
    :rtype: str
    """
    if 'unresolved' in input.attrs and bool(input['unresolved']):
        raise AttributeError('Cannot extract domain name from unresolved xref.')

    if 'urititle' in input.attrs and fullmatch(dns_name_pattern, input['urititle']):
        return input['urititle']
    
    dest = json.loads(pageseeder.get_uri(input['uriid']))
    if fullmatch(dns_name_pattern, dest['title']):
        return dest['title']
    elif fullmatch(dns_name_pattern, dest['displaytitle']):
        return dest['displaytitle']
    else:
        raise ValueError('Unable to extract a valid domain name from xref.')


def apply_licenses(
        dnsobj: DNSObject, 
        license_uri: int,
        license_type: str,
        org_uri: str = None, 
        cache: set[str] = None
    ) -> set[str]:
    """
    Walks the DNS and recursively adds a footer fragment / sets the organization
    on dns objects and their nodes.

    Won't overwrite an existing organization attribute.

    :param dnsobj: The DNSObject to start with.
    :type dnsobj: DNSObject
    :param org_uri: URI of the organization.
    :type org_uri: int
    :param cache: A cache of DNSObject names, defaults to None
    :type cache: set[str], optional
    :return: The cache of DNSObject names.
    :rtype: set[str]
    """
    if not cache:
        cache = set()
    elif dnsobj.name in cache: 
        return cache
    cache.add(dnsobj.name)
    
    add_footer(dnsobj, license_uri, license_type)

    if org_uri and dnsobj.organization != org_uri:
        dnsobj.organization = org_uri

        if dnsobj.node and dnsobj.node.identity not in cache:
            cache.add(dnsobj.node.identity)
            
            if not dnsobj.node.organization:
                dnsobj.node.organization = org_uri
            add_footer(dnsobj.node, license_uri, license_type)

            for addr in (dnsobj.node.domains | dnsobj.node.ips):
                cache |= apply_licenses(dnsobj.network.find_dns(addr),
                    license_uri, license_type, org_uri, cache)

    for backref in dnsobj.backrefs.destinations:
        cache |= apply_licenses(backref, license_uri, license_type, org_uri, cache)

    for dest in dnsobj.records.destinations:
        cache |= apply_licenses(dest, license_uri, license_type, org_uri, cache)

    return cache

def add_footer(nwobj: NetworkObject, license_uri: int, license_type: str) -> None:
    """
    Adds a properties-fragment to the footer of the network object that describes 
    the PageSeeder license.

    :param nwobj: The network object.
    :type nwobj: NetworkObject
    :param license_uri: URI of the associated license document.
    :type license_uri: int
    :param license_type: Type of the associated license.
    :type license_type: str
    """
    nwobj.psmlFooter.append(psml.PropertiesFragment('ps-license', [
        psml.Property('license', psml.XRef(str(license_uri)), 'PageSeeder License'),
        psml.Property('license-type', license_type, 'License Type')
    ]))
