const puppeteer = require('puppeteer');
const { compare } = require("odiff-bin");
const fs = require('fs');
const dns = require('./src/dns.json');
var domains = Object.keys(dns)
var review = {}     //Keys are image filenames, vals are results
var success = []    


async function imgdiff() {
  console.log('[INFO][screenshotCompare.js] Comparing screenshots to base images...')
  for (let index = 0; index < success.length; index++) {
    const filename = success[index]
    try {
      const { match, reason } = await compare(
        "/etc/ext/base/".concat(filename),
        "/opt/app/out/screenshots/".concat(filename),
        "/opt/app/out/review/".concat(filename)
      );
      if (match == false) {
        review[filename] = 'imgdiff'
      }
    } catch (error) {
      if (error instanceof TypeError) {
        fs.copyFile('/opt/app/out/screenshots/'.concat(filename), '/etc/ext/base/'.concat(filename), (err) => {if (err) throw (err);});
        console.log(`[WARNING][screenshotCompare.js] No base image for ${filename}. Screenshot saved as base.`)
        review[filename] = 'no_base'
      }
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
    // if successful save img path and print
    success.push(filename)
    console.log(`[INFO][screenshotCompare.js] screenshot saved for ${url}`)
    await page.close()
    return true
  } catch (error) {
    // if failed due to cert error try with http
    if (error.toString().includes('net::ERR_CERT') && (protocol == 'https://')) {
      await try_ss(dmn, 'http://', browser)
    } else if (error.toString().includes('Target closed')) {
      return false
    } else {
      review[filename] = `no_ss:${error}`
      console.log(`[WARNING][screenshotCompare.js] ${url} failed. ${error}`);
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
      console.log('[***DEBUG***][screenshotCompare.js] Descended')
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
  await imgdiff()
})();