"""
Used to retrieve NAT information from pfSense.
"""
from networkobjs import IPv4Address, Network
import utils
from pyppeteer import launch
from plugins import BasePlugin
import asyncio

class Plugin(BasePlugin):
    name = 'pfsense'
    stages = ['nat']

    def runner(network: Network, stage: str) -> None:
        if stage == 'nat':
            nat = asyncio.run(pfsenseScrapeNat())
            for ip, alias in nat.items():
                if ip not in network.ips:
                    IPv4Address(network, ip, True)
                network.ips[ip].nat = alias

async def pfsenseScrapeNat() -> dict:
    nat = {}
    browser = await launch(args = ['--no-sandbox'])
    page = await browser.newPage()
    gateway = f"https://{utils.config()['plugins']['nat']['host']}/"
    await page.goto(gateway, waitUntil = 'networkidle0')

    await (await page.J('#usernamefld')).type(utils.config()['plugins']['nat']['username'])
    await (await page.J('#passwordfld')).type(utils.config()['plugins']['nat']['password'])
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