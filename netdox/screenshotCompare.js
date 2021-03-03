const puppeteer = require('puppeteer');
const { compare } = require("odiff-bin");
const fs = require('fs');
const urlList = require('./src/live.json');
var review = {}


async function imgdiff(array) {
  for (let index = 0; index < array.length; index++) {
    const image = array[index]
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
        fs.copyFile('out/screenshots/'.concat(image), 'out/review/'.concat(image), (err) => {if (err) throw (err);});
        console.log(`[WARNING][screenshotCompare.js] No base image for ${image}. Screenshot copied for review.`)
        review[image] = 'no_base'
      }
    }
  }
  fs.writeFileSync('src/review.json', JSON.stringify(review, null, 2), (err) => {if (err) throw err;})
}

(async (callback) => {
  var array = []
  const browser = await puppeteer.launch({defaultViewport: {width: 1920, height: 1080}, args: ['--no-sandbox']});
  for (let index = 0; index < urlList.length; index++) {
    const page = await browser.newPage();
    const url = urlList[index]
    if (url.includes('https')) {
      var path = url.replace('https://','').replace(/\./g,'_').concat('.png')
    } else {
      var path = url.replace('http://','').replace(/\./g,'_').concat('.png')
    }
    try{
      await page.goto(url);
      await page.screenshot({path: 'out/screenshots/'.concat(path)});
      array.push(path)
      console.log(`[INFO][screenshotCompare.js] screenshot saved for ${url}`)
    } catch (error) {
      review[path] = `no_ss:${error}`
      console.log(`[WARNING][screenshotCompare.js] Error thrown when taking screenshot of url: ${url}. Error thrown: ${error}`);
    }
  }
  await browser.close();
  callback(array)
})(imgdiff);

