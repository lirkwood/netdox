"""
Used to retrieve NAT information from pfSense.
"""
import asyncio
import logging
from getpass import getuser

from netdox import Network, utils
from pyppeteer import launch

logger = logging.getLogger(__name__)
logging.getLogger('pyppeteer').setLevel(logging.WARNING)

def runner(network: Network) -> None:
    for ip, alias in asyncio.run(pfsenseScrapeNat()).items():
        network.ips[ip].translate(alias, 'pfsense')

async def pfsenseScrapeNat() -> dict:
    nat = {}
    config = utils.config('pfsense')
    browser = await launch(autoClose = False,
        args = ['--no-sandbox'] if getuser() == 'root' else []
    )
    page = await browser.newPage()
    gateway = f"https://{config['host']}/"
    await page.goto(gateway, waitUntil = 'networkidle0')

    await (await page.J('#usernamefld')).type(config['username'])
    await (await page.J('#passwordfld')).type(config['password'])
    await page.click('.btn-sm')

    await page.goto(gateway + 'firewall_nat_1to1.php', waitUntil = 'networkidle0')
    if await page.Jeval('.panel-title', 'title => title.textContent') == 'NAT 1:1 Mappings':
        rows = await page.JJ('tr.ui-sortable-handle')
        for row in rows:
            columns = await row.JJeval('td', 'columns => columns.map(column => column.textContent.trim())')
            nat[columns[3]] = columns[4]
    else:
        logger.error('Failed to navigate to pfSense NAT page')
    
    await page.close()
    await browser.close()
    return nat

__stages__ = {'nat': runner}
__config__ = {
    'username': '',
    'password': '',
    'host': ''
}