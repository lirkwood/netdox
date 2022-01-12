"""
This module contains functions / classes for fetching, reading, and updating the config on PageSeeder.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup
from lxml import etree
from requests import Response

from netdox import pageseeder, psml, utils, nwman

logger = logging.getLogger(__name__)

# PageSeeder config

@dataclass
class NetworkConfig:
    """
    Holds the configuration values found in the main config document on PageSeeder.
    """
    DOCID = '_nd_config'
    """Docid for the config file."""
    EXCLUSION_FRAG_ID = 'exclude'
    """ID of the exclusions fragment in PSML."""
    LABEL_SECTION_ID = 'labels'
    """ID of the labels section in PSML."""
    ORG_SECTION_ID = 'organizations'
    """ID of the organization section in PSML."""
    exclusions: set[str]
    """Set of FQDNs to exclude from the network."""
    labels: dict[str, dict]
    """A dictionary mapping document label names to a map of attributes."""
    organizations: dict[str, set[str]]
    """A dictionary mapping organization document URIIDs to their assigned labels."""

    def __init__(self, 
            exclusions: Iterable[str] = [],
            labels: dict[str, dict] = None,
            organizations: dict[str, set[str]] = None
        ) -> None:
        self.exclusions = set(exclusions)
        self.labels = labels or {}
        self.organizations = organizations or {}

    @property
    def is_empty(self) -> bool:
        """
        Returns True if this object has no labels or exclusions.
        False otherwise.
        """
        return not (self.labels or self.exclusions)

    @property
    def attrs(self) -> set[str]:
        """
        Returns all attributes that may be set on a label.
        """
        return {attr for attrs in self.labels.values() for attr in attrs}

    @property
    def normal_attrs(self) -> bool:
        """
        Returns True if all of the labels in config have the correct attributes set.
        False otherwise.
        """
        return all([
            bool(attr in attrs) 
            for attrs in self.labels.values() 
            for attr in self.attrs
        ])

    def update_attrs(self, attrs: Iterable[str]) -> None:
        """
        Updates the keys in each label map to *attrs*.

        :param attrs: The attributes that may be configured on a label.
        :type attrs: Iterable[str]
        """
        for label, old in self.labels.items():
            self.labels[label] = dict.fromkeys(attrs) | {
                key: value for key, value in old.items() if key in attrs}

    @classmethod
    def from_psml(cls, document: str) -> NetworkConfig:
        """
        Instantiates this class from a PSML document.

        :param document: The document to build the config from.
        :type document: str
        :return: An instance of this class.
        :rtype: NetworkConfig
        """
        etree.XMLSchema(file = utils.APPDIR + 'src/psml.xsd').assertValid(
            etree.fromstring(bytes(document, 'utf-8')))
        soup = BeautifulSoup(document, 'xml')

        exclusions = set()
        exclusionFrag = soup.find('fragment', id = cls.EXCLUSION_FRAG_ID)
        for para in exclusionFrag('para'):
            exclusions.add(str(para.string))

        labels = {}
        labelSection = soup.find('section', id = cls.LABEL_SECTION_ID)
        for label in labelSection('properties-fragment'):
            attrs = psml.PropertiesFragment.from_tag(label).to_dict()
            labelName = attrs.pop('label')
            labels[labelName] = attrs

        orgs = defaultdict(set)
        orgSection = soup.find('section', id = cls.ORG_SECTION_ID)
        for frag in orgSection('properties-fragment'):
            org_prop = frag.find(attrs = {'name':'organization'})
            label_prop = frag.find(attrs = {'name':'label'})
            if (
                org_prop.find('xref') and 
                org_prop.xref.has_attr('uriid') and
                label_prop['value']
            ):
                orgs[org_prop.xref['uriid']].add(label_prop['value'])

        return cls(exclusions, labels, orgs)

    def to_psml(self) -> str:
        """
        Serialises this object to PSML.

        :return: This object as a PSML document.
        :rtype: str
        """
        with open(utils.APPDIR+ 'src/templates/config.psml', 'r') as stream:
            soup = BeautifulSoup(stream.read(), 'xml')
        for tag in soup.find_all('t:fragment'):
            tag.decompose()

        docinfo = soup.find('documentinfo')
        assert docinfo is not None, 'Failed to find element documentinfo in config template.'
        uri = docinfo.uri
        assert uri is not None, 'Failed to find element uri in config documentinfo.'
        uri['docid'] = self.DOCID

        exclusionFrag = soup.find('fragment', id = self.EXCLUSION_FRAG_ID)
        for domain in self.exclusions:
            para = soup.new_tag('para')
            para.string = domain
            exclusionFrag.append(para)

        labelSection = soup.find('section', id = self.LABEL_SECTION_ID)
        for label, properties in self.labels.items():
            labelSection.append(psml.PropertiesFragment.from_dict(
                id = f'label_{label}', 
                constructor = {'label': label} | properties
            ))

        orgSection = soup.find('section', id = self.ORG_SECTION_ID)
        for uriid, labels in self.organizations.items():
            for count, label in enumerate(labels):
                orgSection.append(psml.PropertiesFragment(f'org_{uriid}_{count}', [
                    psml.Property('label', label, 'Label Name'),
                    psml.Property('organization', psml.XRef(uriid), 'Organization')
                ]))

        return str(soup)

    @classmethod
    def from_pageseeder(cls) -> NetworkConfig:
        """
        Fetches the NetworkConfig from PageSeeder.
        """
        try:
            return cls.from_psml(
                pageseeder.get_default_docid(cls.DOCID).text)
        except Exception:
            logger.error('Failed to retrieve config from PageSeeder')
            return cls()
    

def generate_template(attrs: set[str]) -> str:
    """
    Generates a new template from a provided set of attributes.

    :param attrs: A set of attributes that can be configured for each label.
    :type attrs: Iterable[str]
    """
    with open(utils.APPDIR+ 'src/templates/config.psml') as stream:
        soup = BeautifulSoup(stream.read(), 'xml')

    tFragment = soup.find('t:fragment')
    tFragment.findChild('properties-fragment').decompose()
    tFragment.append(psml.PropertiesFragment('', 
        [psml.Property('label', '', 'Label Name')] + [
        psml.Property(attr, '') for attr in attrs
    ]))

    return str(soup)

def update_template(attrs: set[str]) -> Response:
    """
    Updates the config template on PageSeeder.

    :param attrs: A set of configurable attributes for each label.
    :type attrs: Iterable[str]
    """
    project = "-".join(
        utils.config()['pageseeder']['group'].split("-")[:-1])

    return pageseeder.put_group_resource(
        f'/WEB-INF/config/template/{project}/psml/netdox/document-template.psml',
        generate_template(attrs), overwrite = True)


# Local config

def gen_config_template(nwman: nwman.NetworkManager):
    """
    Generates a template config file from the plugins discovered by *nwman*.

    :param nwman: The NetworkManager to read the plugin data from.
    :type nwman: nwman.NetworkManager
    """
    with open(utils.APPDIR+ 'src/defaults/config.json', 'r') as stream:
        app_config = json.load(stream)
    app_config['plugins'] = defaultdict(dict)

    # deactivate logging while initialising a networkmanager
    nwman_logger = logging.getLogger('netdox.nwman')
    nwman_level = nwman_logger.level
    nwman_logger.setLevel(logging.ERROR)

    # generate config template from plugins
    for plugin in nwman.plugins:
        if plugin.config is not None:
            try:
                json.dumps(plugin.config)
            except Exception:
                logger.error(
                    f"Plugin {plugin.__name__.split('.')[-1]} "
                    'registered an invalid JSON object under __config__.')
            else:
                app_config['plugins'][plugin.name] = plugin.config

    nwman_logger.setLevel(nwman_level)
    
    with open(utils.APPDIR+ 'cfg/config.json', 'w') as stream:
        stream.write(json.dumps(app_config, indent = 2))
