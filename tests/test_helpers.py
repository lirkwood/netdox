import pytest
from conftest import LOCATIONS, hide_file
from netdox import utils
from netdox import helpers
from fixtures import *
from os import remove
from lxml import etree

class TestLocator:

    def test_locate(self):
        locator = helpers.Locator(LOCATIONS)
        assert locator.locate('192.168.0.0') == 'Subnet0'
        assert locator.locate(['192.168.0.0']) == 'Subnet0'
        assert locator.locate(['192.168.0.0', '192.168.0.255']) == 'Subnet0'

        assert locator.locate(['192.168.1.0']) == 'Subnet1or2'
        assert locator.locate(['192.168.1.0', '192.168.2.255']) == 'Subnet1or2'

        assert locator.locate(['192.168.0.0', '192.168.1.0']) == None   

class TestReport:
    SECTION_ID = 'section_id'
    OUTPATH = 'test_report.psml'

    @pytest.fixture
    def valid_section(self) -> str:
        return f'<section id="{self.SECTION_ID}" />'

    @pytest.fixture
    def invalid_section(self) -> str:
        return '<section><random_tag!></section>'

    def test_add_section_success(self, valid_section):
        report = helpers.Report()
        report.addSection(valid_section)
        assert report.sections == [valid_section]

    def test_add_section_failure(self, invalid_section):
        report = helpers.Report()
        report.addSection(invalid_section)
        assert report.sections == []

    def test_write_report(self, valid_section):
        report = helpers.Report()
        report.addSection(valid_section)
        report.writeReport(self.OUTPATH)

        try:
            etree.XMLSchema(file = utils.APPDIR + 'src/psml.xsd').assertValid(
                etree.parse(self.OUTPATH))
        except Exception:
            assert False, 'Invalid report content.'
        finally:
            remove(self.OUTPATH)

class TestOrganization:
    NAME = 'organization Name'
    URIID = '999'
    CONTACT_NAME = 'Admin Fullname'
    CONTACT_EMAIL = 'admin@organization.org'
    CONTACT_PHONE = '123456789'

    @pytest.fixture
    def organization(self) -> helpers.Organization:
        return helpers.Organization(
            self.NAME, self.URIID, self.CONTACT_NAME, 
            self.CONTACT_EMAIL, self.CONTACT_PHONE
        )

    def test_from_psml_success(self, organization):
        assert organization == helpers.Organization.from_psml(
            f'''<document id="{self.URIID}">
                <section id="title">
                    <fragment xmlns:psof="http://www.pageseeder.org/function" id="1">
                        <heading level="1">{self.NAME}</heading>
                    </fragment>
                </section>
                <section id="details">
                    <properties-fragment xmlns:psof="http://www.pageseeder.org/function" id="2">
                        <property name="admin-name" title="Admin contact name" value="{self.CONTACT_NAME}"/>
                        <property name="admin-email" title="Admin contact email" value="{self.CONTACT_EMAIL}"/>
                        <property name="admin-phone" title="Admin contact phone" value="{self.CONTACT_PHONE}"/>
                    </properties-fragment>
                </section>
            </document>''')

    def test_from_psml_failure(self):
        with pytest.raises(ValueError):
            helpers.Organization.from_psml(f'''<document id="{self.URIID}">
                <section id="title">
                    <fragment xmlns:psof="http://www.pageseeder.org/function" id="1">
                        <heading level="1">{self.NAME}</heading>
                    </fragment>
                </section>
                <section id="details">
                    <properties-fragment xmlns:psof="http://www.pageseeder.org/function" id="2">
                        <!-- <property name="admin-name" title="Admin contact name" value="{self.CONTACT_NAME}"/>
                        <property name="admin-email" title="Admin contact email" value="{self.CONTACT_EMAIL}"/>
                        <property name="admin-phone" title="Admin contact phone" value="{self.CONTACT_PHONE}"/> -->
                    </properties-fragment>
                </section>
            </document>''')


class TestCounter:

    @fixture
    def mock_counter(self) -> helpers.Counter:
        return helpers.Counter()

    def test_inc_facet(self, mock_counter: helpers.Counter):
        assert mock_counter.counts == helpers.Counter.DEFAULT_COUNTS

        mock_counter.inc_facet(helpers.CountedFacets.DNSLink)
        assert mock_counter.counts[helpers.CountedFacets.DNSLink] == 1

        mock_counter.dec_facet(helpers.CountedFacets.DNSLink)
        assert mock_counter.counts[helpers.CountedFacets.DNSLink] == 0

        mock_counter.dec_facet(helpers.CountedFacets.DNSLink)
        assert mock_counter.counts[helpers.CountedFacets.DNSLink] == 0

