const puppeteer = require('puppeteer');
var { imgDiff } = require("img-diff-js");
const fs = require('fs');
const domains = require('./src/config.json')['website']
var review = {
	"no_ss": {},
	"no_base": [],
	"imgdiff": [],
	"nodiff": []
}

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
				actualFilename: "out/screenshots/".concat(filename),
				expectedFilename: "/etc/ext/base/".concat(filename),
				diffFilename: "out/review/".concat(filename),
				generateOnlyDiffFile: true
			});

			// if diff pixel count > 10% (where aspect ratio is 1920x1080)
			if (diffCount > 207360) {
				review['imgdiff'].push(domain)
			} else {
				review['nodiff'].push(domain)
			}

		} else {
			review['no_base'].push(domain)
		}
	}
	return true
}

async function try_ss(domain, protocol, browser) {
	var filename = pngName(domain)
	var url = protocol.concat(domain)

	const page = await browser.newPage();
	try {
		await page.goto(url, { timeout: 5000 });
		await page.waitForTimeout(1000)
		await page.screenshot({ path: 'out/screenshots/'.concat(filename) });
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
			review['no_ss'][domain] = error.toString()
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

	fs.writeFileSync('src/review.json', JSON.stringify(review, null, 2), (err) => { if (err) throw err; })
})();