"""
Used to retrieve NAT information from pfSense.
"""
import asyncio

from pyppeteer import launch

from netdox import utils
from netdox.networkobjs import IPv4Address, Network

def runner(network: Network) -> None:
    for ip, alias in asyncio.run(pfsenseScrapeNat()).items():
        if ip not in network.ips:
            IPv4Address(network, ip, True)
        network.ips[ip].nat = alias

async def pfsenseScrapeNat() -> dict:
    nat = {}
    config = utils.config()['plugins']['pfsense']
    browser = await launch(args = ['--no-sandbox'])
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
            nat[columns[4]] = columns[3]
    else:
        print('[DEBUG][pfsense] Failed to navigate to pfSense NAT page')
    
    await page.close()
    await browser.close()
    return nat

__stages__ = {'nat': runner}