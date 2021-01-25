const puppeteer = require('puppeteer');
const urlList = require('./live.json');

(async () => {
  const browser = await puppeteer.launch();
  for (let index = 0; index < urlList.length; index++) {
    const page = await browser.newPage();
    const url = urlList[index];
    if (url.includes('https')) {
      var path = url.replace('https://','').replace(/\./g,'_').concat('.png')
    } else {
      var path = url.replace('http://','').replace(/\./g,'_').concat('.png')
    }
    console.log(url.concat(' screenshot saved.'))
    try{
      await page.goto(url);
      await page.screenshot({path: 'new/_nd_img_'.concat(path)});
    } catch (error) {
      console.log(`Error thrown when taking screenshot of url: ${url}. Error thrown: ${error}`)
    }
  }
  await browser.close();
})();