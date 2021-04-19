const puppeteer = require('puppeteer');
var { imgDiff } = require("img-diff-js");
const fs = require('fs');
const dns = require('./src/dns.json');
const exclusions = require('./src/screenshot_exclude.json')
var domains = Object.keys(dns)
var review = {}     // domains that failed the imagediff process in some way


function pngName(string) {
	return string.replace(/\./g, '_').concat('.png')
}


async function diffScreens(array) {
	for (let index = 0; index < array.length; index++) {
		const domain = array[index]
		const filename = pngName(domain)
		// if has a base image
		if (fs.existsSync("/etc/ext/base/".concat(filename))) {
			// diff images
			let { diffCount } = await imgDiff({
				actualFilename: "/opt/app/out/screenshots/".concat(filename),
				expectedFilename: "/etc/ext/base/".concat(filename),
				diffFilename: "/opt/app/out/review/".concat(filename),
				generateOnlyDiffFile: true
			});

			// if diff pixel count > 10% (where aspect ratio is 1920x1080)
			if (diffCount > 207360) {
				review[domain] = 'imgdiff'
			} else {
				review[domain] = 'nodiff'
			}

		} else {
			review[domain] = 'no_base'
		}
	}
	return true
}

async function try_ss(domain, protocol, browser) {
	var filename = pngName(domain)
	var url = protocol.concat(domain)

	const page = await browser.newPage();
	try {
		await page.goto(url, { timeout: 3000 });
		await page.waitForTimeout('500')
		await page.screenshot({ path: '/opt/app/out/screenshots/'.concat(filename) });
	} catch (error) {
		try { await page.close() } catch (err) {};
		// if failed due to cert error on https try with http
		if (error.toString().includes('net::ERR_CERT') && (protocol == 'https://')) {
			let http = await try_ss(domain, 'http://', browser)
			return http

			// if puppeteer crashed
		} else if (error.toString().includes('Target closed')) {
			return 'crashed'

		} else {
			review[domain] = `no_ss:${error}`
			return false
		}

	}
	await page.close()
	return true
}

async function newBrowser(array) {
	var success = []
	var browser = await puppeteer.launch({ defaultViewport: { width: 1920, height: 1080 }, args: ['--no-sandbox'] });
	for (let index = 0; index < array.length; index++) {
		var domain = array[index]
		if (!exclusions.includes(domain)) {
			let screenshot = await try_ss(domain, 'https://', browser)
	
			if (screenshot == true) {
				success.push(domain)
			} else if (screenshot == 'crashed') {
				// If puppeteer crashes, start new browser and retry
				try { await browser.close() } catch (err) { };
				var browser = await puppeteer.launch({ defaultViewport: { width: 1920, height: 1080 }, args: ['--no-sandbox'] });
				index--;
			}
		}
	}
	await browser.close();
	return success
}


(async () => {
	console.log('[INFO][screenshotCompare.js] Taking screenshots...')

	let thirdLength = domains.length / 3
	let first = domains.slice(0, thirdLength)
	let second = domains.slice(thirdLength, 2 * thirdLength)
	let third = domains.slice(2 * thirdLength)

	let firstDiff = newBrowser(first).then(success => { diffScreens(success) })
	let secondDiff = newBrowser(second).then(success => { diffScreens(success) })
	let thirdDiff = newBrowser(third).then(success => { diffScreens(success) })

	await firstDiff
	await secondDiff
	await thirdDiff

	fs.writeFileSync('/opt/app/src/review.json', JSON.stringify(review, null, 2), (err) => { if (err) throw err; })
})();