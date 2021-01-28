const puppeteer = require('puppeteer');
const { compare } = require("odiff-bin");
const fs = require('fs');
const urlList = require('./live.json');
var failed = []


async function imgdiff(array) {
  for (let index = 0; index < array.length; index++) {
    const image = array[index]
    try {
      const { match, reason } = await compare(
        "base/".concat(image),
        "screenshots/".concat(image),
        "review/".concat(image)
      );
      if (match == false) {
        failed.push(image)
      }
    } catch (error) {
      if (error instanceof TypeError) {
        failed.push(image)
      }
    }
  }
  fs.writeFile('review.json', failed, function (err) {if (err) throw err;});
}

(async (callback) => {
  var array = []
  const browser = await puppeteer.launch({defaultViewport: {width: 1920, height: 1080}});
  for (let index = 0; index < urlList.length; index++) {
    const page = await browser.newPage();
    const url = urlList[index]
    if (url.includes('https')) {
      var path = '_nd_img_'.concat(url.replace('https://','').replace(/\./g,'_').concat('.png'))
    } else {
      var path = '_nd_img_'.concat(url.replace('http://','').replace(/\./g,'_').concat('.png'))
    }
    console.log(url.concat(' screenshot saved.'))
    try{
      await page.goto(url);
      await page.screenshot({path: 'screenshots/'.concat(path)});
      array.push(path)
    } catch (error) {
      failed.push(path)
      console.log(`Error thrown when taking screenshot of url: ${url}. Error thrown: ${error}`);
    }
  }
  await browser.close();
  callback(array)
})(imgdiff);

