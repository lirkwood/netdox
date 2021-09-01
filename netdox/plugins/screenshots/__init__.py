import asyncio
import json
import logging
import os
import shutil
from datetime import date
from typing import Iterable, Tuple

import diffimg
from bs4 import BeautifulSoup
from pyppeteer import launch
from pyppeteer.browser import Page
from pyppeteer.errors import TimeoutError

from netdox import pageseeder, utils
from netdox.objs import Domain, Network

logger = logging.getLogger(__name__)
logging.getLogger('pyppeteer').setLevel(logging.WARNING)


class ScreenshotManager:
    workdir: str
    """Directory to save temporary files to."""
    basedir: str
    """Directory of base images to diff against."""
    outdir: str
    """Directory to save output images to."""
    placeholder: str
    """Path to a placeholder image."""
    existingScreens: list[str]
    """List of filenames of screenshots on PageSeeder."""
    roles: list[str]
    """List of roles that have the ``screenshot`` property set."""
    _failed: list[str]
    """List of domain docids that failed to be screenshot"""
    _diff: list[str]
    """List of domain docids that had a screenshot >5% different to the base img"""
    _noBase: list[str]
    """List of domain docids that had no base img to diff against"""

    def __init__(self, domains: Iterable[Domain], workdir: str, basedir: str, outdir: str, placeholder: str) -> None:
        self.stats = {
            'fail': [],
            'diff': [],
            'base': []
        }

        self.workdir = workdir
        self.basedir = basedir
        self.outdir = outdir
        self.placeholder = placeholder

        self.existingScreens = pageseeder.get_files(pageseeder.urimap()['screenshots'])

        self.roles = [role \
            for role, config in utils.roles().items() if (
                'screenshot' in config and config['screenshot']
        )]

        self.domains = [domain \
            for domain in domains if domain.role in self.roles
        ]

    def start(self) -> None:
        """
        Screenshots all domains with the ``screenshot`` property set in the domain's role, 
        and then diffs them to against a base image (previous screenshot).

        If screenshot fails, and there is not a screenshot on PageSeeder already, a placeholder is generated.
        If the screenshot is different to the base image (by >5%), 
        the base is copied to a dated archive directory and uploaded as well for human inspection.
        """
        for domain, success in self.takeScreens():
            filename = domain.docid + '.jpg'
            if not success:
                self.stats['fail'].append(domain.docid)
                self.copyPlaceholder(filename)
            else:
                domain.psmlFooter.append(BeautifulSoup(f'''
                    <fragment id="screenshot">
                        <para><image src="{utils.config()["pageseeder"]["group"].replace("-","/")}/website/screenshots/{domain.docid}.jpg"
                    </fragment>
                ''', features = 'xml'))

                if os.path.exists(f'{self.basedir}/{filename}'):

                    if diffimg.diff(
                        im1_file = f'{self.basedir}/{filename}', 
                        im2_file = f'{self.workdir}/{filename}',
                        diff_img_file = f'{self.outdir}/diffimg/{filename}',
                        ignore_alpha = True
                    ) > 0.05:
                        # if diff > 5%
                        self.stats['diff'].append(domain.docid)
                        self.newBase(filename, archive = True)

                    else:
                        os.remove(f'{self.outdir}/diffimg/{filename}')

                else:
                    self.stats['base'].append(domain.docid)
                    self.newBase(filename)

        with open(f'{self.workdir}/stats.json', 'w') as stream:
            stream.write(json.dumps(self.stats))
    
    ## Manipulating screenshot files

    def newBase(self, filename: str, archive = False) -> None:
        """
        Copies the new screenshot to the output and base dirs.
        If *archive* is True, copies the old base image to screenshot_history.

        :param filename: Filename of the screenshot in question.
        :type filename: str
        :param archive: Whether or not to archive the old base image, defaults to False.
        :type archive: bool, optional
        """
        if archive:
            shutil.copyfile(
                f'{self.basedir}/{filename}', 
                f'{self.outdir}/screenshot_history/{date.today().isoformat()}/{filename}'
            )
        shutil.copyfile(
            f'{self.workdir}/{filename}',
            f'{self.outdir}/screenshots/{filename}'
        )
        shutil.copyfile(
            f'{self.workdir}/{filename}',
            f'{self.basedir}/{filename}'
        )

    def copyPlaceholder(self, filename: str) -> None:
        """
        Copies placeholder if no image on PS already.

        :param filename: Filename of the screenshot in question.
        :type filename: str
        """
        if filename not in self.existingScreens:
            shutil.copyfile(
                self.placeholder, 
                f'{self.outdir}/screenshots/{filename}'
            )

    ## Taking screenshots

    def takeScreens(self) -> list[Tuple[Domain, bool]]:
        """
        Take screenshots of every domain

        :return: A list of tuples containing a Domain object and boolean. True if successfully screenshotted.
        :rtype: list[Tuple[Domain, bool]]
        """
        return asyncio.run(self._takeScreens())

    async def _takeScreens(self) -> list[Tuple[Domain, bool]]:
        """
        Splits ``self.domains`` into three groups and calls ``self.ssDomainList`` on each asynchronously.

        :return: The superset of the three values returned by the ``self.ssDomainList`` calls.
        :rtype: list[Tuple[Domain, bool]]
        """
        total = len(self.domains)
        third = int(total / 3)
        
        group1 = self.domains[:third]
        group2 = self.domains[third:2*third]
        group3 = self.domains[2*third:]

        return [result for results in await asyncio.gather(
            *map(self.ssDomainlist, (group1, group2, group3))
        ) for result in results]

    async def ssDomainlist(self, domains: list[Domain]) -> list[Tuple[Domain, bool]]:
        """
        Creates a new browser and page, and asynchronously screenshots each domain in *domains*.

        :param domains: A list of Domains
        :type domains: list[Domain]
        :return: A list of tuples containing a Domain object and boolean. True if successfully screenshotted.
        :rtype: list[Tuple[Domain, bool]]
        """
        browser = await launch(ignoreHTTPSErrors = True)
        page = await browser.newPage()
        await page.setViewport({'width':1680,'height':1050})
        values = [ await self.screenshot(page, domain) for domain in domains ]
        await page.close()
        await browser.close()
        return values

    async def screenshot(self, page: Page, domain: Domain) -> bool:
        """
        Takes a screenshot of a domain

        :param page: The page object to use
        :type page: Page
        :param domain: The domain to screenshot
        :type domain: Domain
        :return: True if a screenshot is successfully saved. False otherwise.
        :rtype: bool
        """
        try:
            await page.goto(f'https://{domain.name}/', timeout = 5000, waitUntil = 'networkidle0')  #@IgnoreException
            await page.screenshot(path = f'{self.workdir}/{domain.docid}.jpg')
            return (domain, True)
        except TimeoutError:
            logger.warning(f'Navigation to {domain.name} timed out.')
        except Exception as e:
            logger.warning(f'Screenshot for {domain.name} failed: \'{e}\'')

        return (domain, False)


def init() -> None:
    if not os.path.exists(utils.APPDIR+ 'plugins/screenshots/base'):
        os.mkdir(utils.APPDIR+ 'plugins/screenshots/base')
    if not os.path.exists(utils.APPDIR+ 'out/screenshot_history'):
        os.mkdir(utils.APPDIR+ 'out/screenshot_history')

    for path in (
        'plugins/screenshots/src',
        'out/screenshots',
        'out/diffimg',
        'out/screenshot_history/'+ date.today().isoformat()
    ):
        if os.path.exists(utils.APPDIR + path):
            shutil.rmtree(utils.APPDIR + path)
        os.mkdir(utils.APPDIR + path)

def runner(network: Network) -> None:
    mngr = ScreenshotManager(
        domains = network.domains, 
        workdir = utils.APPDIR+ 'plugins/screenshots/src',
        basedir = utils.APPDIR+ 'plugins/screenshots/base',
        outdir = utils.APPDIR+ 'out',
        placeholder = utils.APPDIR+ 'src/placeholder.jpg'
    )
    mngr.start()


__stages__ = {'footers': runner}

if __name__ == '__main__':
    init()
    runner(Network.fromDump())
