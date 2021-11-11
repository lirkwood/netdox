import asyncio
import json
import logging
import os
import re
import shutil
from datetime import date
from typing import Iterable, Tuple

import diffimg
from bs4 import BeautifulSoup
from netdox import pageseeder, utils
from netdox import Domain, Network
from pyppeteer import launch
from pyppeteer.browser import Page
from pyppeteer.errors import TimeoutError

logger = logging.getLogger(__name__)
logging.getLogger('pyppeteer').setLevel(logging.WARNING)

SCREENSHOT_ATTR = 'screenshot'
__attrs__ = {SCREENSHOT_ATTR}


class ScreenshotManager:
    workdir: str
    """Directory to save temporary files to."""
    basedir: str
    """Directory of base images to diff against."""
    outdir: str
    """Directory to save output images to."""
    placeholder: str
    """Path to a placeholder image."""
    urimap: dict
    """URI map of the screenshots on PageSeeder"""
    existingScreens: list[str]
    """List of filenames of screenshots on PageSeeder."""

    def __init__(self, domains: Iterable[Domain], workdir: str, basedir: str, outdir: str, placeholder: str) -> None:
        self.stats: dict[str, list[str]] = {
            'fail': [],
            'diff': [],
            'base': []
        }

        self.workdir = workdir
        self.basedir = basedir
        self.outdir = outdir
        self.placeholder = placeholder

        try:
            self.urimap = pageseeder.urimap('website/screenshots')
            self.existingScreens = list(self.urimap.keys())
        except FileNotFoundError:
            self.urimap = {}
            self.existingScreens = []
        
        if os.path.basename(self.placeholder) not in self.existingScreens:
            shutil.copyfile(
                self.placeholder, 
                self.outdir +'/screenshots/'+ os.path.basename(self.placeholder)
            )

        self.domains = []
        for domain in domains:
            screenshot = domain.getAttr(SCREENSHOT_ATTR)
            if screenshot and screenshot.strip().lower() in ('true','yes'):
                self.domains.append(domain)

    def start(self) -> None:
        """
        Screenshots all domains with the ``screenshot`` attribute set, 
        and then diffs them to against a base image (previous screenshot).

        If screenshot fails, and there is not a screenshot on PageSeeder already, a placeholder is generated.
        If the screenshot is different to the base image (by >5%), 
        the base is copied to a dated archive directory and uploaded as well for human inspection.
        """
        for domain, success in self.takeScreens():
            filename = domain.name.replace('.','_') + '.jpg'
            if not success:
                self.stats['fail'].append(domain.docid)
                self.addPSMLFooter(domain)
            else:
                self.addPSMLFooter(domain, filename)
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

    async def screenshot(self, page: Page, domain: Domain) -> tuple[Domain, bool]:
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
            await page.screenshot(path = f'{self.workdir}/{domain.name.replace(".","_")}.jpg')
            return (domain, True)
        except TimeoutError:
            logger.warning(f'Navigation to {domain.name} timed out.')
        except Exception as e:
            logger.warning(f'Screenshot for {domain.name} failed: \'{e}\'')

        return (domain, False)

    def addPSMLFooter(self, domain: Domain, filename: str = None) -> None:
        """
        Appends a fragment containing an image named *filename* to the footer of *domain*.

        :param domain: The domain to modify the footer of.
        :type domain: Domain
        :param filename: The filename of the image, relative to the ``screenshots`` directory on PageSeeder. defaults to the ``placeholder`` filename.
        :type filename: str
        """
        filename = filename or os.path.basename(self.placeholder)
        domain.psmlFooter.append(BeautifulSoup(f'''
            <fragment id="screenshot">
                <para><image src="/ps/{utils.config()["pageseeder"]["group"].replace("-","/")}/website/screenshots/{filename}"
            </fragment>
        ''', features = 'xml'))

    def sentenceStale(self) -> None:
        """
        Sentence any stale screenshots on PageSeeder.
        Also clears the sentence of any screenshots wrongfully marked as stale.
        """
        for file in self.existingScreens:
            if file.replace('_','.')[:-4] not in self.domains:
                info = json.loads(pageseeder.get_uri(self.urimap[file]))
                labels = info['labels'] if 'labels' in info else []
                if 'stale' in labels:
                    for label in labels:
                        match = re.fullmatch(utils.expiry_date_pattern, label)
                        if match and ( date.fromisoformat(match['date']) <= date.today() ):
                            pageseeder.archive(self.urimap[file])
                else:
                    pageseeder.sentence_uri(self.urimap[file])
            else:
                pageseeder.clear_sentence(self.urimap[file])

        if 'diffimg' in pageseeder.urimap():
            pageseeder.archive(pageseeder.urimap()['diffimg'])

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
        placeholder = utils.APPDIR+ 'plugins/screenshots/placeholder.jpg'
    )
    mngr.start()
    mngr.sentenceStale()


__stages__ = {'footers': runner}

if __name__ == '__main__':
    init()
    runner(Network.fromDump())
