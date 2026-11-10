const {chromium}=require('playwright-core');
const {pathToFileURL}=require('url');
const path=require('path');
const fs=require('fs');

(async()=>{
  const windowsChrome='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const executablePath=process.env.CHROME_PATH||(fs.existsSync(windowsChrome)?windowsChrome:undefined);
  const browser=await chromium.launch({headless:true,executablePath});
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const packaged=path.join(__dirname,'..','simulador.html');
  const html=process.argv[2]||(fs.existsSync(packaged)?packaged:path.join(__dirname,'simulador_pista_foto.html'));
  const url=pathToFileURL(path.resolve(html)).href;
  await page.goto(url,{waitUntil:'load'});
  const options=await page.locator('#course option').allTextContents();
  if(options.length!==2||!options[0].includes('2025')||!options[1].includes('2024'))throw Error('Menu incorreto: '+JSON.stringify(options));
  if(await page.locator('#course').inputValue()!=='0')throw Error('2025 deve iniciar selecionada.');
  if(!await page.locator('#photoWarning').isVisible())throw Error('Falta aviso de pista hipotética.');
  if(await page.locator('#scoreCommon').innerText()!=='22 / 31')throw Error('Região comum de 2025 incorreta.');
  if(await page.locator('#progress').inputValue()!=='0')throw Error('A simulação deve começar na posição inicial.');
  const payload=await page.evaluate(()=>({tracks:DATA.tracks.length,marks:events.length,left:events.filter(e=>e.side===1).length,right:events.filter(e=>e.side===-1).length,sensors:[tracesL.length,tracesR.length]}));
  if(JSON.stringify(payload)!==JSON.stringify({tracks:2,marks:31,left:29,right:2,sensors:[1,1]}))throw Error('Dados inesperados: '+JSON.stringify(payload));
  const geometry=await page.evaluate(()=>DATA.tracks.map(t=>({
    marks:t.marks.length,curveLeft:t.marks.filter(m=>m.kind==='curva'&&m.side===1).length,
    finishRight:t.marks.filter(m=>['partida','chegada'].includes(m.kind)&&m.side===-1).length,
    estimated:t.estimated.length,firstX:t.cycle[0][0],firstHeading:t.track[0][3],rotate:t.display_rotate
  })));
  if(geometry[0].marks!==31||geometry[0].curveLeft!==29||geometry[0].finishRight!==2||geometry[0].rotate||Math.sin(geometry[0].firstHeading)<.999)throw Error('Modelo 2025 inesperado: '+JSON.stringify(geometry[0]));
  if(geometry[1].marks!==35||geometry[1].curveLeft!==33||geometry[1].finishRight!==2||!geometry[1].estimated||geometry[1].rotate||Math.abs(geometry[1].firstX-3150)>.01||Math.cos(geometry[1].firstHeading)>-.999)throw Error('Espelhamento ou lados de 2024 incorretos: '+JSON.stringify(geometry[1]));
  const presets=await page.locator('#preset option').allTextContents();
  if(presets.some(s=>/dois QRE|três QRE|adicional/i.test(s)))throw Error('Há opções com sensores adicionais.');
  async function check(preset,course,score){
    await page.selectOption('#preset',preset);await page.selectOption('#course',String(course));
    const actual=await page.locator('#scoreNom').innerText();if(actual!==score)throw Error(`${preset}/${course}: esperado ${score}, obtido ${actual}`);
  }
  await check('holes',1,'21 / 35');if(process.env.ROBOT_SCREENSHOT_PATH)await page.screenshot({path:process.env.ROBOT_SCREENSHOT_PATH,fullPage:true});
  await check('one_asym68',1,'20 / 35');await check('one_out1',1,'22 / 35');await check('one_60',1,'22 / 35');
  await check('holes',0,'26 / 31');if(!await page.locator('#photoWarning').isVisible())throw Error('Falta aviso fotográfico em 2025.');
  await check('one_asym68',0,'29 / 31');await check('one_out1',0,'26 / 31');await check('one_60',0,'30 / 31');
  await page.click('#crossing');if(!(await page.locator('#markDetail').innerText()).includes('caminho foi definido'))throw Error('Falta aviso do cruzamento de 2025.');
  await page.selectOption('#preset','holes');await page.selectOption('#barOffset','2');
  if(await page.locator('#scoreNom').innerText()!=='26 / 31')throw Error('Desvio fixo de 2025 divergente.');
  await page.selectOption('#barOffset','0');await check('holes',1,'21 / 35');
  await page.click('#crossing');if(!(await page.locator('#markDetail').innerText()).includes('caminho foi definido'))throw Error('Falta aviso do cruzamento.');
  await page.click('#play');const old=await page.locator('#progress').inputValue();await page.waitForTimeout(600);const now=await page.locator('#progress').inputValue();if(old===now)throw Error('Animação não avançou.');await page.click('#play');
  await page.click('#restart');if(await page.locator('#progress').inputValue()!=='0')throw Error('Falha ao voltar ao início.');
  await page.setViewportSize({width:390,height:844});const sizes=await page.evaluate(()=>({window:innerWidth,body:document.documentElement.scrollWidth}));if(sizes.body>sizes.window)throw Error('Rolagem horizontal no celular.');
  const nojs=await browser.newPage({javaScriptEnabled:false});await nojs.goto(url,{waitUntil:'load'});
  if(!await nojs.locator('#fallback').isVisible()||await nojs.locator('#fallback svg').count()!==2)throw Error('Prévia estática sem duas pistas.');
  if(errors.length)throw Error(errors.join('\n'));
  console.log(JSON.stringify({resultado:'ok',pistas:options,payload,testes:'configurações, desvios, cruzamento, animação, tela estreita e prévia estática'}));
  await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
