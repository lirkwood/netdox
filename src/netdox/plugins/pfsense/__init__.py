"""
Used to retrieve NAT information from pfSense.
"""
import asyncio
import logging
from getpass import getuser

from netdox import Network, utils
from netdox.app import LifecycleStage
from pyppeteer import executablePath, launch

logger = logging.getLogger(__name__)
logging.getLogger('pyppeteer').setLevel(logging.WARNING)

def runner(network: Network) -> None:
    for ip, alias in asyncio.run(pfsenseScrapeNat()).items():
        network.ips[ip].translate(alias, 'pfsense')

async def pfsenseScrapeNat() -> dict:
    nat = {}
    config = utils.config('pfsense')

    logger.debug('Starting browser...')
    browser_args = ['--disable-gpu']
    if getuser() == 'root':
        browser_args.append('--no-sandbox')
    browser = await launch(
        executablePath = config['browser'],
        autoClose = False,
        args = browser_args
    )

    logger.debug('Opening page...')
    page = await browser.newPage()
    gateway = f"https://{config['host']}/"
    logger.debug(f'Navigating to url {gateway} ...')
    await page.goto(gateway, waitUntil = 'networkidle0')

    logger.debug('Logging in to pfsense...')
    await (await page.J('#usernamefld')).type(config['username'])
    await (await page.J('#passwordfld')).type(config['password'])
    await asyncio.gather(
        page.waitForNavigation(),
        page.click('.btn-sm'),
    )
    logger.debug('Logged in to pfsense.')

    rows = await page.JJ('tr.ui-sortable-handle')
    for row in rows:
        columns = await row.JJeval('td', 'columns => columns.map(column => column.textContent.trim())')
        nat[columns[3]] = columns[4]
    logger.debug('Finished reading rows.')
    
    await page.close()
    await browser.close()
    return nat

__stages__ = {LifecycleStage.NAT: runner}
__config__ = {
    'username': '',
    'password': '',
    'host': '',
    'browser': ''
}
