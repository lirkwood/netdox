import asyncio
import json
import os
import shutil
from typing import Iterable, Tuple
from bs4 import BeautifulSoup

import diffimg
import utils
from networkobjs import Domain, Network
from plugins import BasePlugin as BasePlugin
from pyppeteer import launch
from pyppeteer.page import Page
from datetime import date
import pageseeder


class ScreenshotManager:
    domains: list[str]
    workdir: str
    basedir: str
    outdir: str
    placeholder: str
    roles: list[str]
    failed: list[str]
    diff: list[str]
    nobase: list[str]

    def __init__(self, domains: Iterable[Domain], workdir: str, basedir: str, outdir: str, placeholder: str) -> None:
        self.failed = []
        self.diff = []
        self.nobase = []

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
        Screenshots all domains with the correct role config, and then compares them to an existing screenshot.

        If the domain cannot be screenshotted, and there is not a screenshot on PageSeeder already, a placeholder is generated.
        If the screenshot is different to the existing screenshot, 
        the existing file is copied to a dated archive directory and the new one will be uploaded.
        """
        if os.path.exists(self.workdir+'/ss'):
            shutil.rmtree(self.workdir+'/ss')
        os.mkdir(self.workdir+'/ss')

        for domain, success in self.takeScreens():
            # if no screen
            if not success:
                self.failed.append(domain.docid)
                # copy placeholder
                if f'{domain.docid}.jpg' not in self.existingScreens:
                    shutil.copyfile(
                        self.placeholder, 
                        f'{self.outdir}/screenshots/{domain.docid}.jpg'
                    )

            else:
                domain.psmlFooter.append(BeautifulSoup(f'''
                    <fragment id="screenshot">
                        <para><img src="{utils.config()["pageseeder"]["group"].replace("-","/")}/website/screenshots/{domain.docid}.jpg"
                    </fragment>
                ''', features = 'xml'))
                
                try:
                    diffratio = diffimg.diff(
                        im1_file = f'{self.basedir}/{domain.docid}.jpg', 
                        im2_file = f'{self.workdir}/ss/{domain.docid}.jpg',
                        diff_img_file = f'{self.outdir}/diffimg/{domain.docid}.jpg'
                    )
                except FileNotFoundError:
                    # if no base img
                    self.nobase.append(domain.docid)
                    shutil.copyfile(
                        f'{self.workdir}/ss/{domain.docid}.jpg',
                        f'{self.outdir}/screenshots/{domain.docid}.jpg'
                    )
                else:
                    # if diff > 5%
                    if diffratio > 0.05:
                        self.diff.append(domain.docid)
                        # save old base img
                        shutil.copyfile(
                            f'{self.basedir}/{domain.docid}.jpg', 
                            f'{self.outdir}/screenshot_history/{date.today().isoformat()}/{domain.docid}.jpg'
                        )
                        # copy new screen
                        shutil.copyfile(
                            f'{self.workdir}/ss/{domain.docid}.jpg',
                            f'{self.outdir}/screenshots/{domain.docid}.jpg'
                        )
                        shutil.copyfile(
                            f'{self.workdir}/screenshots/{domain.docid}.jpg',
                            f'{self.basedir}/{domain.docid}.jpg'
                        )
                    else:
                        # delete empty diff file
                        os.remove(f'{self.outdir}/diffimg/{domain.docid}.jpg')
        
        with open(f'{self.workdir}/stats.json', 'w') as stream:
            stream.write(json.dumps(self.stats))

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
        browser = await launch(args = ['--no-sandbox'])
        page = await browser.newPage()
        await page.setViewport({'width':1680,'height':1050})

        values = await asyncio.gather(
            *[self.screenshot(page, domain) for domain in domains]
        )
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
            await page.goto(f'https://{domain.name}/', timeout = 3000)
            await page.screenshot(path = f'{self.workdir}/ss/{domain.docid}.jpg')
            return (domain, True)
        except Exception:
            return (domain, False)

    @property
    def stats(self) -> dict[str, list[str]]:
        return {
            'failed': self.failed,
            'nobase': self.nobase,
            'diff': self.diff
        }


class Plugin(BasePlugin):
    name = "screenshots"
    stages = ['post-write']

    def init(self) -> None:
        if os.path.exists('plugins/screenshots/src'):
            shutil.rmtree('plugins/screenshots/src')
        if os.path.exists('out/screenshots'):
            shutil.rmtree('out/screenshots')
        if os.path.exists(f'out/screenshot_history/{date.today().isoformat()}'):
            shutil.rmtree(f'out/screenshot_history/{date.today().isoformat()}')

        if not os.path.exists('src/base'):
            os.mkdir('src/base')
        if not os.path.exists('out/screenshot_history'):
            os.mkdir('out/screenshot_history')
            
        os.mkdir('plugins/screenshots/src')
        os.mkdir('out/screenshots')
        os.mkdir(f'out/screenshot_history/{date.today().isoformat()}')

    def runner(self, network: Network, stage: str) -> None:
        mngr = ScreenshotManager(
            domains = network.domains, 
            workdir = 'plugins/screenshots/src',
            basedir = 'plugins/screenshots/base',
            outdir = 'out',
            placeholder = 'src/placeholder.jpg'
        )
        mngr.start()