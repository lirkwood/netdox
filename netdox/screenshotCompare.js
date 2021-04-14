const puppeteer = require('puppeteer');
var { imgDiff } = require("img-diff-js");
const fs = require('fs');
const dns = require('./src/dns.json');
var domains = Object.keys(dns)
var review = {}     // domains that failed the imagediff process in some way


function docid(string) {
  return string.replace(/\./g,'_')
}


async function diffScreens(array) {
  for (let index = 0; index < array.length; index++) {
    const domain = array[index]
    console.log(`[DEBUG][screenshotCompare.js] Diffing ${domain}`)
    const filename = docid(domain).concat('.png')
    // if has a base image
    if (fs.existsSync("/etc/ext/base/".concat(filename))) {
      // diff images
      var result = await imgDiff({
        actualFilename: "/opt/app/out/screenshots/".concat(filename),
        expectedFilename: "/etc/ext/base/".concat(filename),
        diffFilename: "/opt/app/out/review/".concat(filename),
        generateOnlyDiffFile: true
      });

      if (result['imagesAreSame'] == false) {
        // if diff pixel count > 10% (where aspect ratio is 1920x1080)
        if (result['diffCount'] > 207360) {
          console.log(`[DEBUG][screenshotCompare.js] Found imgdiff on ${filename}`)
          review[filename] = 'imgdiff'
        } else {
          console.log(`[DEBUG][screenshotCompare.js] ${review['diffCount']} diff pixels for ${domain}`)
        }
      }
    } else {
      review[filename] = 'no_base'
    }
  }
  return true
}

async function try_ss(dmn, protocol, browser) {
  var filename = docid(dmn).concat('.png')
  var url = protocol.concat(dmn)

  const page = await browser.newPage();
  try{
    await page.goto(url, {timeout: 3000});
    await page.screenshot({path: '/opt/app/out/screenshots/'.concat(filename)});
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
  var success = []
  const browser = await puppeteer.launch({defaultViewport: {width: 1920, height: 1080}, args: ['--no-sandbox']});
  for (let index = 0; index < array.length; index++) {
    const domain = array[index]
    let code = await try_ss(domain, 'https://', browser)
    if (code == false) {
      let retry = await newBrowser(array.slice(index))
      success = success.concat(retry)
    } else {
      success.push(domain)
    }
  }
  await browser.close();
  return success
}

(async () => {
  console.log('[INFO][screenshotCompare.js] Taking screenshots...')

  let thirdLength = domains.length / 3
  let first = domains.slice(0, thirdLength)
  let second = domains.slice(thirdLength, 2*thirdLength)
  let third = domains.slice(2*thirdLength)

  let firstDiff = newBrowser(first).then(success => {diffScreens(success)})
  let secondDiff = newBrowser(second).then(success => {diffScreens(success)})
  let thirdDiff = newBrowser(third).then(success => {diffScreens(success)})

  await firstDiff
  await secondDiff
  await thirdDiff

  fs.writeFileSync('/opt/app/src/review.json', JSON.stringify(review, null, 2), (err) => {if (err) throw err;})
})();
