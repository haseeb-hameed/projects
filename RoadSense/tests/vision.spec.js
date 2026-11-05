import{test,expect}from'@playwright/test';
test('real recorded-video frame analysis without GPS/account, pause/reset and no road-report writes',async({page})=>{
 test.setTimeout(120000);const errors=[],writes=[],frames=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST'&&/\/api\/(hazards|detect|alerts|routes)(\/|$)/.test(r.url()))writes.push(r.url())});page.on('response',async r=>{if(r.url().endsWith('/api/vision/frame')&&r.status()===200)frames.push(await r.json())});
 await page.goto('http://localhost:5173');await expect(page.getByText('Actual model inference. Not a prepared animation.')).toBeVisible();
 await page.getByLabel('Choose road video',{exact:true}).setInputFiles('tests/fixtures/synthetic-decode.webm');
 await expect(page.getByRole('button',{name:'Analyse video',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Analyse video',exact:true}).click();
 await expect(page.locator('.vision-metrics>div').first().locator('strong')).not.toHaveText('0',{timeout:60000});
 if(await page.getByRole('button',{name:'Pause analysis'}).count())await page.getByRole('button',{name:'Pause analysis'}).click();
 await expect(page.getByRole('button',{name:'Analyse video',exact:true})).toBeEnabled({timeout:20000});
 expect(frames.length).toBeGreaterThan(0);expect(frames[0].source).toBe('video');expect(frames[0].saved).toBe(false);expect(frames[0].reports).toEqual([]);expect(frames[0].inference_ms).toBeGreaterThan(0);
 await expect(page.locator('.vision-stage canvas')).toBeVisible();
 await page.screenshot({path:'docs/video-detector-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Analyse video',exact:true}).click();await expect(page.getByText('Video analysis complete',{exact:true})).toBeVisible({timeout:60000});expect(frames.length).toBeGreaterThan(2);
 await page.getByRole('button',{name:'Restart',exact:true}).click();await expect(page.locator('.vision-metrics>div').first().locator('strong')).toHaveText('0');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'docs/video-detector-phone.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();expect(writes).toEqual([]);expect(errors).toEqual([]);
});
test('actual image inference draws the backend result on the displayed frame',async({page})=>{
 test.setTimeout(90000);await page.goto('http://localhost:5173');await page.getByRole('button',{name:'Still image',exact:true}).click();await page.getByLabel('Choose road image',{exact:true}).setInputFiles('models/upstream-validation-preview.jpg');await page.getByRole('button',{name:'Analyse image',exact:true}).click();await expect(page.locator('.vision-stage canvas')).toBeVisible({timeout:60000});await expect(page.locator('.vision-results')).toContainText('Backend inference');await page.screenshot({path:'docs/actual-inference-smoke.png',fullPage:true});
});
