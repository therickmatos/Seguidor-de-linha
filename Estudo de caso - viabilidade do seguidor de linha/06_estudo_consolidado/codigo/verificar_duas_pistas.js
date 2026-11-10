const {chromium}=require('playwright-core');
const {pathToFileURL}=require('url');
const path=require('path');
const fs=require('fs');

(async()=>{
  const windowsChrome='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const executablePath=process.env.CHROME_PATH||(fs.existsSync(windowsChrome)?windowsChrome:undefined);
  const browser=await chromium.launch({headless:true,executablePath});
  try{
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
  if(await page.locator('#preset').inputValue()!=='chassi_baixo_2')throw Error('O teste de chassi baixo deve iniciar selecionado.');
  if(await page.locator('#scoreCommon').innerText()!=='33 / 33')throw Error('Região comum do novo chassi em 2025 incorreta.');
  if(await page.locator('#progress').inputValue()!=='0')throw Error('A simulação deve começar na posição inicial.');
  const payload=await page.evaluate(()=>({tracks:DATA.tracks.length,marks:events.length,left:events.filter(e=>e.side===1).length,right:events.filter(e=>e.side===-1).length,sensors:[tracesL.length,tracesR.length]}));
  if(JSON.stringify(payload)!==JSON.stringify({tracks:2,marks:33,left:31,right:2,sensors:[2,2]}))throw Error('Dados inesperados: '+JSON.stringify(payload));
  const geometry=await page.evaluate(()=>DATA.tracks.map(t=>({
    marks:t.marks.length,curveLeft:t.marks.filter(m=>m.kind==='curva'&&m.side===1).length,
    finishRight:t.marks.filter(m=>['partida','chegada'].includes(m.kind)&&m.side===-1).length,
    estimated:t.estimated.length,firstX:t.cycle[0][0],firstHeading:t.track[0][3],rotate:t.display_rotate
  })));
  if(geometry[0].marks!==33||geometry[0].curveLeft!==31||geometry[0].finishRight!==2||geometry[0].rotate||Math.sin(geometry[0].firstHeading)<.999)throw Error('Modelo 2025 inesperado: '+JSON.stringify(geometry[0]));
  if(geometry[1].marks!==35||geometry[1].curveLeft!==33||geometry[1].finishRight!==2||!geometry[1].estimated||geometry[1].rotate||Math.abs(geometry[1].firstX-3150)>.01||Math.cos(geometry[1].firstHeading)>-.999)throw Error('Espelhamento ou lados de 2024 incorretos: '+JSON.stringify(geometry[1]));
  const presets=await page.locator('#preset option').allTextContents();
  if(presets.some(s=>/dois QRE|três QRE|adicional/i.test(s)))throw Error('Há opções históricas de sensores adicionais fora do novo teste.');
  if(!presets.some(s=>s.includes('Chassi baixo')))throw Error('Falta a opção de chassi baixo.');
  async function check(preset,course,score){
    await page.selectOption('#preset',preset);await page.selectOption('#course',String(course));
    const actual=await page.locator('#scoreNom').innerText();if(actual!==score)throw Error(`${preset}/${course}: esperado ${score}, obtido ${actual}`);
  }
  const expected=JSON.parse(fs.readFileSync(path.join(__dirname,'..','dados','resultados_duas_pistas.json'),'utf8')).results;
  async function validateLow(course,preset='chassi_baixo_2'){
    await page.selectOption('#course',String(course));
    const year=course===0?'2025':'2024',row=expected.find(r=>r.track===year&&r.preset===preset);
    if(!row)throw Error('Falta validação Python: '+year+'/'+preset);
    await page.selectOption('#preset','chassi_baixo_2');
    if(preset!=='chassi_baixo_2'){
      await page.locator('#L').fill(String(row.L_mm));
      await page.waitForFunction(holes=>document.getElementById('mount').textContent.includes('Furos: '+holes.toFixed(1)+' mm'),row.hole_distance_mm);
    }
    const observed=await page.evaluate(()=>({mode:chassisMode,x:[X,...extras],y:Y,sensors:[tracesL.length,tracesR.length],
      cutouts:currentChassis().cutouts.length,width:DATA.lowChassis.width,length:DATA.lowChassis.length,
      allInside:[-X,...extras.map(x=>-x),X,...extras].every(x=>sensorInsideChassis(x,Y)),
      events:events.map(e=>({mark:e.label,hit:e.hit,common:e.common,side:e.side,sensors:e.sensorsHit})),
      nominal:document.getElementById('scoreNom').textContent,common:document.getElementById('scoreCommon').textContent,
      sides:document.getElementById('scoreSides').textContent}));
    if(observed.mode!=='low_two'||JSON.stringify(observed.x)!=='[52.25,77.75]'||observed.y!==20||JSON.stringify(observed.sensors)!=='[2,2]')throw Error('Configuração incorreta: '+JSON.stringify(observed));
    if(observed.cutouts!==15||!observed.allInside||Math.abs(observed.width-164.7)>.01||Math.abs(observed.length-58.6)>.01)throw Error('Contorno ou recortes incorretos.');
    if(observed.nominal!==`${row.nominal} / ${row.total}`||observed.common!==`${row.common} / ${row.total}`)throw Error('Total diverge da validação Python: '+JSON.stringify(observed));
    for(const e of observed.events){const ref=row.events.find(v=>v.mark===e.mark);if(!ref||e.hit!==ref.nominal||e.common!==ref.common)throw Error(`Marca divergente: ${year}/${preset}/${e.mark}`)}
    if(observed.events.length!==row.total||new Set(observed.events.map(e=>e.mark)).size!==row.total)throw Error('Há marcas duplicadas.');
    if(!observed.events.some(e=>e.sensors.length===2))throw Error('Falta exercitar marca detectada pelos dois sensores.');
    if(!observed.sides.includes(`Esquerda ${row.left_nominal}/${row.total-2}`)||!observed.sides.includes('Direita 2/2'))throw Error('Totais por lado incorretos.');
    if(await page.locator('#mount').evaluate(e=>e.classList.contains('danger')))throw Error('QRE válido marcado fora do contorno.');
  }
  for(const course of [0,1]){
    await validateLow(course);
    if(process.env.ROBOT_SCREENSHOT_DIR){
      await page.click('#zoom');await page.selectOption('#mark','1');
      await page.screenshot({path:path.join(process.env.ROBOT_SCREENSHOT_DIR,`chassi_dois_${course===0?'2025':'2024'}.png`),fullPage:true});
      await page.click('#zoom');
    }
    await validateLow(course,'chassi_baixo_2_65');await validateLow(course,'chassi_baixo_2_70');
  }
  await page.locator('#X').fill('110');
  await page.waitForFunction(()=>document.getElementById('mount').textContent.includes('fora do contorno'));
  if(await page.evaluate(()=>chassisMode)!=='low_two')throw Error('Personalizar X perdeu o contorno fixo.');
  await check('holes',1,'21 / 35');
  if(await page.evaluate(()=>chassisMode!=='v3'||tracesL.length!==1||tracesR.length!==1))throw Error('Retorno ao v3 não restaurou os sensores.');
  if(process.env.ROBOT_SCREENSHOT_PATH)await page.screenshot({path:process.env.ROBOT_SCREENSHOT_PATH,fullPage:true});
  await check('one_asym68',1,'20 / 35');await check('one_out1',1,'22 / 35');await check('one_60',1,'22 / 35');
  await check('holes',0,'24 / 33');if(!await page.locator('#photoWarning').isVisible())throw Error('Falta aviso fotográfico em 2025.');
  await check('one_asym68',0,'22 / 33');await check('one_out1',0,'24 / 33');await check('one_60',0,'24 / 33');
  await page.click('#crossing');if(!(await page.locator('#markDetail').innerText()).includes('caminho foi definido'))throw Error('Falta aviso do cruzamento de 2025.');
  await page.selectOption('#preset','holes');await page.selectOption('#barOffset','2');
  if(await page.locator('#scoreNom').innerText()!=='23 / 33')throw Error('Desvio fixo de 2025 divergente.');
  await page.selectOption('#barOffset','0');await check('holes',1,'21 / 35');
  await page.click('#crossing');if(!(await page.locator('#markDetail').innerText()).includes('caminho foi definido'))throw Error('Falta aviso do cruzamento.');
  await page.click('#play');const old=await page.locator('#progress').inputValue();await page.waitForTimeout(600);const now=await page.locator('#progress').inputValue();if(old===now)throw Error('Animação não avançou.');await page.click('#play');
  await page.click('#restart');if(await page.locator('#progress').inputValue()!=='0')throw Error('Falha ao voltar ao início.');
  await page.selectOption('#preset','chassi_baixo_2');
  await page.setViewportSize({width:390,height:844});const sizes=await page.evaluate(()=>({window:innerWidth,body:document.documentElement.scrollWidth}));if(sizes.body>sizes.window)throw Error('Rolagem horizontal no celular.');
  if(process.env.ROBOT_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.ROBOT_SCREENSHOT_DIR,'chassi_dois_mobile.png'),fullPage:true});
  const nojs=await browser.newPage({javaScriptEnabled:false});await nojs.goto(url,{waitUntil:'load'});
  if(!await nojs.locator('#fallback').isVisible()||await nojs.locator('#fallback svg').count()!==2)throw Error('Prévia estática sem duas pistas.');
  if(errors.length)throw Error(errors.join('\n'));
  console.log(JSON.stringify({resultado:'ok',pistas:options,payload,testes:'chassi de quatro QRE em 60/65/70 mm contra validação Python por marca, contorno e recortes, contagem única, retorno ao v3, desvios, cruzamento, animação, tela estreita e prévia estática'}));
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
