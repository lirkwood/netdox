const puppeteer = require('puppeteer');
var { imgDiff } = require("img-diff-js");
const fs = require('fs');
const dns = require('./src/dns.json');
var domains = Object.keys(dns)
var success = []    // domains to be tested using imgdiff
var review = {}     // domains that failed the imagdiff process in some way


async function diffScreens() {
  console.log('[INFO][screenshotCompare.js] Comparing screenshots to base images...')
  for (let index = 0; index < success.length; index++) {
    const filename = success[index]
    if (fs.existsSync("/etc/ext/base/".concat(filename))) {
      let result = await imgDiff({
        actualFilename: "/opt/app/out/screenshots/".concat(filename),
        expectedFilename: "/etc/ext/base/".concat(filename),
        diffFilename: "/opt/app/out/review/".concat(filename)
      });
      if (result['imagesAreSame'] == false) {
        // 2do: add pixel threshold using result['diffCount']
        console.log(`[DEBUG][screenshotCompare.js] Found imgdiff on ${filename}`)
        review[filename] = 'imgdiff'
      }
    } else {
      review[filename] = 'no_base'
    }
  }
  fs.writeFileSync('/opt/app/src/review.json', JSON.stringify(review, null, 2), (err) => {if (err) throw err;})
}

async function try_ss(dmn, protocol, browser) {
  var filename = dmn.replace(/\./g,'_').concat('.png')
  var url = protocol.concat(dmn)

  const page = await browser.newPage();
  try{
    await page.goto(url, {timeout: 3000});
    await page.screenshot({path: '/opt/app/out/screenshots/'.concat(filename)});
    success.push(filename)
    // console.log(`[INFO][screenshotCompare.js] screenshot saved for ${url}`)
    await page.close()
    return true
  } catch (error) {
    // if failed due to cert error on https try with http
    if (error.toString().includes('net::ERR_CERT') && (protocol == 'https://')) {
      await try_ss(dmn, 'http://', browser)
    } else if (error.toString().includes('Target closed')) {
      return false
    } else {
      review[filename] = `no_ss:${error}`
      // console.log(`[WARNING][screenshotCompare.js] ${url} failed. ${error}`);
    }
    await page.close()
    return true
  }
}

async function newBrowser(array) {
  const browser = await puppeteer.launch({defaultViewport: {width: 1920, height: 1080}, args: ['--no-sandbox']});
  for (let index = 0; index < array.length; index++) {
    const domain = array[index]
    let code = await try_ss(domain, 'https://', browser)
    if (code == false) {
      let retry = await newBrowser(array.slice(index))
      return retry
    }
  }
  await browser.close();
  return true
}

(async () => {
  console.log('[INFO][screenshotCompare.js] Taking screenshots...')

  let thirdLength = domains.length / 3
  let first = domains.slice(0, thirdLength)
  let second = domains.slice(thirdLength, 2*thirdLength)
  let third = domains.slice(2*thirdLength)

  let firstReturned = newBrowser(first)
  let secondReturned = newBrowser(second)
  let thirdReturned = newBrowser(third)

  await firstReturned
  await secondReturned
  await thirdReturned
  await diffScreens()
})();