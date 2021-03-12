const puppeteer = require('puppeteer');
const { compare } = require("odiff-bin");
const fs = require('fs');
const dns = require('./src/dns.json');
var domains = Object.keys(dns)
var review = {}     //Keys are image filenames, vals are results
var success = []    


async function imgdiff() {
  for (let index = 0; index < success.length; index++) {
    const image = success[index]
    try {
      const { match, reason } = await compare(
        "src/base/".concat(image),
        "out/screenshots/".concat(image),
        "out/review/".concat(image)
      );
      if (match == false) {
        review[image] = 'imgdiff'
      }
    } catch (error) {
      if (error instanceof TypeError) {
        fs.copyFile('out/screenshots/'.concat(image), 'src/base/'.concat(image), (err) => {if (err) throw (err);});
        console.log(`[WARNING][screenshotCompare.js] No base image for ${image}. Screenshot saved as base.`)
        review[image] = 'no_base'
      }
    }
  }
  fs.writeFileSync('src/review.json', JSON.stringify(review, null, 2), (err) => {if (err) throw err;})
}

async function try_ss(dmn, protocol, browser) {
  var path = dmn.replace(/\./g,'_').concat('.png')
  var url = protocol.concat(dmn)

  const page = await browser.newPage();
  try{
    await page.goto(url, {timeout: 3000});
    await page.screenshot({path: 'out/screenshots/'.concat(path)});
    // if successful save img path and print
    success.push(path)
    console.log(`[INFO][screenshotCompare.js] screenshot saved for ${url}`)
    await page.close()
  } catch (error) {
    // if failed due to cert error try with http
    if (error.toString().includes('net::ERR_CERT') && (protocol == 'https://')) {
      try_ss(dmn, 'http://', browser)
    } else {
      review[path] = `no_ss:${error}`
      console.log(`[WARNING][screenshotCompare.js] ${url} failed. ${error}`);
    }
    await page.close()
  }
}

(async () => {
  const browser = await puppeteer.launch({defaultViewport: {width: 1920, height: 1080}, args: ['--no-sandbox']});
  for (let index = 0; index < domains.length; index++) {
    const dmn = domains[index]
    await try_ss(dmn, 'https://', browser)
  }
  await browser.close();
  await imgdiff()
})();