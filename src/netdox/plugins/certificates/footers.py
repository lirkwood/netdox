"""
Module containing functions to append certificate information to the footer of NWObjs.
"""
from ssl import get_server_certificate

from cryptography import x509
from netdox.dns import Domain
from netdox.psml import PropertiesFragment, Property


def analyze(domain: Domain) -> None:
    """
    Appends a fragment to the domain's psml footer,
    containing some information from the returned SSL certificate.

    :param domain: Domain to pull the cert from.
    :type domain: Domain
    """
    cert = x509.load_pem_x509_certificate(
        bytes(get_server_certificate((domain.name, 443)), 'utf-8'))

    domain.psmlFooter.append(
        PropertiesFragment('certificate', [
            Property('valid_from', 
                cert.not_valid_before.isoformat(), 'Valid from (UTC)'),
            Property('valid_to',
                cert.not_valid_after.isoformat(), 'Valid until (UTC)'),
            Property('distinguishedname',
                cert.subject.rfc4514_string(), 'Distinguished Name')
        ])
    )