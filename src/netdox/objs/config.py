from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup
from netdox import pageseeder, psml, utils
from requests import Response

logger = logging.getLogger(__name__)


@dataclass
class NetworkConfig:
    """
    Holds the config values.
    """
    DOCID = '_nd_config'
    """Docid for the config file."""
    EXCLUSION_FRAG_ID = 'exclude'
    """ID of the exclusions fragment in PSML."""
    LABEL_SECTION_ID = 'labels'
    """ID of the labels section in PSML."""
    exclusions: set[str]
    """Set of FQDNs to exclude from the network."""
    labels: dict[str, dict]
    """A dictionary mapping document label names to a map of attributes."""

    def __init__(self, exclusions: Iterable[str] = [], labels: dict[str, dict] = None) -> None:
        self.exclusions = set(exclusions)
        self.labels = labels or {}

    @property
    def attrs(self) -> set[str]:
        """
        Returns all attributes that may be set on a label.

        :return: A set of attribute names.
        :rtype: set[str]
        """
        return {attr for attrs in self.labels.values() for attr in attrs}

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

        return cls(exclusions, labels)

    def to_psml(self) -> str:
        """
        Serialises this object to PSML.

        :return: This object as a PSML document.
        :rtype: str
        """
        with open(utils.APPDIR+ 'src/templates/config.psml', 'r') as stream:
            soup = BeautifulSoup(stream.read(), 'xml')
        soup.find('t:fragment').decompose()

        exclusionFrag = soup.find('fragment', id = self.__class__.EXCLUSION_FRAG_ID)
        for domain in self.exclusions:
            para = soup.new_tag('para')
            para.string = domain
            exclusionFrag.append(para)

        labelSection = soup.find('section', id = self.__class__.LABEL_SECTION_ID)
        for label, properties in self.labels.items():
            labelSection.append(psml.PropertiesFragment.from_dict(
                id = f'label_{label}', 
                constructor = properties | {'label': label}
            ))

        return str(soup)

    @classmethod
    def from_pageseeder(cls) -> NetworkConfig:
        """
        Fetches the NetworkConfig from PageSeeder.
        """
        return cls.from_psml(
            pageseeder.get_default_docid('_nd_config').text)
    

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
