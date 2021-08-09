"""
Fetching data
*************
"""
import asyncio
import json
import re

import utils
from iptools import regex_ip
from networkobjs import IPv4Address, Network
from pyppeteer import launch

patt_nat = re.compile(rf'(?P<alias>{regex_ip.pattern}).+?(?P<dest>{regex_ip.pattern}).*')

def runner(network: Network):
    """
    Reads the NAT dump from FortiGate and calls the pfSense node script.

    :param network: The network
    :type network: Network
    """
    # Gather FortiGate NAT
    with open('src/nat.txt','r') as stream:
        natDict = {}
        for line in stream.read().splitlines():
            match = re.match(patt_nat, line)
            if match:
                natDict[match['alias']] = match['dest']
                natDict[match['dest']] = match['alias']

    # Gather pfSense NAT
    natDict |= asyncio.run(pfsenseScrapeNat())

    for ip in natDict:
        if ip not in network.ips:
            IPv4Address(network, ip, True)
        network.ips[ip].nat = natDict[ip]


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
        print('[DEBUG][nat] Failed to navigate to pfSense NAT page')
    
    await page.close()
    await browser.close()
    return nat