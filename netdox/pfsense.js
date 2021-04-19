const fs = require('fs');
const puppeteer = require('puppeteer');
const auth = require('./src/authentication.json')['pfsense'];
const nat = {};

(async () => {
    const browser = await puppeteer.launch({args: ['--no-sandbox']})
    const page = await browser.newPage()
    const gateway = 'https://'.concat(auth['host'])
    await page.goto(gateway, {waitUntil: 'networkidle0'})

    await page.$eval('#usernamefld', (username, auth) => {username.value = auth['username']}, auth)
    await page.$eval('#passwordfld', (password, auth) => {password.value = auth['password']}, auth)
    await page.click('.btn-sm')

    await page.waitForNavigation({ waitUntil: 'networkidle0' })
    await page.goto(gateway.concat('/firewall_nat_1to1.php'))

    let title = await page.$eval('.panel-title', title => title.textContent)
    if (title == 'NAT 1:1 Mappings') {
        let rows = await page.$$('tr.ui-sortable-handle')
        for (let index = 0; index < rows.length; index++) {
            const row = rows[index];
            let columns = await row.$$eval('td', columns => columns.map(column => column.textContent.trim()))
            nat[columns[3]] = columns[4]
            nat[columns[4]] = columns[3]
        }
        console.log(nat)
    } else {
        console.log('[ERROR][pfsense.js] Failed to login to pfSense. Unable to retrieve NAT.')
    }
    await browser.close();
})();
