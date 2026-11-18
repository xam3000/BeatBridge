import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {constants as fsConstants} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from 'file:///C:/Program%20Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1116-1220-0_26.1116.1220.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import {styledSlides as slides} from './style-content.mjs';

const root=process.cwd(),build=path.join(root,'presentations/.build/style-20261117');
const skill='C:/Users/max_h/.codex/plugins/cache/openai-primary-runtime/presentations/26.1116.12020/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1116-1220-0_26.1116.1220.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
const {makeNativeBulletParagraphs,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const source=path.join(root,'presentations/output/BeatBridge_Mastervortrag_20min.pptx');
const reference=path.join(root,'presentations/older_presentations/seminar_master.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const font='Lato Light',ink='#000000',bg='#F2F2F2';
await fs.mkdir(path.join(build,'draft-slides'),{recursive:true});
const agendaLayout=p.layouts.items.find(l=>l.name==='Gliederung');
if(!agendaLayout)throw Error('Source agenda layout missing');
const {slide:agenda}=p.slides.insert({after:p.slides.items[0],layoutId:agendaLayout.id});
agenda.placeholders.addFromLayout();
function text(slide,value,x,y,w,h,size=21.33,color=ink,name='text'){
 const a=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=value;a.text.style={typeface:font,fontSize:size,color,autoFit:'none',wrap:true};a.text.insets=0;return a;
}
function bullets(slide,items,{x=55.33,y=98,w=859,h=345,size=21.33,gap=4,name='bullet-list'}={}){
 // The reference decks use the same 16 pt body type for primary and secondary lists.
 size=21.33;
 const a=text(slide,'',x,y,w,h,size,ink,name);
 a.text=items.flatMap(item=>{
  const {text:value,level=0}=typeof item==='string'?{text:item}:item;
  const paras=makeNativeBulletParagraphs([value],{marginLeftPoints:level?37.5:22.5,hangingPoints:22.5,spaceAfterPoints:gap});
  for(const para of paras)para.runs=[{run:value,style:{typeface:font,fontSize:`${size}px`,color:ink}}];
  return paras;
 });
 a.text.insets=0;
 return a;
}
function table(slide,values,{y=101,h=242,widths=[410,230,239],size=21.33}={}){
 const t=slide.tables.add({rows:values.length,columns:values[0].length,left:45.33,top:y,width:879.33,height:h,columnWidths:widths,values});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:bg,textStyle:{typeface:font,fontSize:size,color:ink,bold:false},margins:{left:12,right:8,top:8,bottom:8},anchor:'center'});
 t.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:'#DEDEDE',textStyle:{typeface:font,fontSize:size,color:ink,bold:false}});
 t.borders.assign({fill:'#BEBEBE',style:'solid',width:.6});return t;
}
function restyleChart(c,{x,y,w,h,title,legend=false}){
 c.position={left:x,top:y,width:w,height:h};c.title=title;
 c.titleTextStyle.typeface=font;c.titleTextStyle.fontSize=20;c.titleTextStyle.fill=ink;
 c.chartFill='#FFFFFF';c.plotAreaFill='#FFFFFF';c.hasLegend=legend;
 c.legend={position:'bottom',textStyle:{typeface:font,fontSize:17.33,fill:ink}};
 c.xAxis={textStyle:{typeface:font,fontSize:17,fill:ink},title:{text:'Übergangsposition',textStyle:{typeface:font,fontSize:17,fill:ink}}};
 c.yAxis={textStyle:{typeface:font,fontSize:17,fill:ink}};
}
let elapsed=0;
const format=s=>`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
for(let i=0;i<slides.length;i++){
 const d=slides[i],s=p.slides.items[i];s.hidden=!!d.hidden;
 if(d.type==='cover'){
  s.shapes.items[1].text.style={typeface:font,fontSize:21.33,color:ink,alignment:'center'};
 } else if(d.type==='end'){
  s.shapes.items[0].text=d.title;s.shapes.items[1].text=d.subtitle;
 } else {
  const titleShape=s.shapes.items.find(a=>a.name==='Titel 1')??s.shapes.items.find(a=>a.placeholder?.type==='title');
  if(!titleShape)throw Error(`No title on ${i+1}`);
  titleShape.text=d.title;
  titleShape.text.style={typeface:font,fontSize:29.33,color:d.type==='agenda'?'#FFFFFF':ink,bold:false};
  const selected=await p.inspect({select:`$.slides[${i}].elements[*]`,include:['id','kind','name']});
  // Keep the inherited ICG design and imported charts. Rewrite owned copy and
  // deliberately rebuild native tables from their complete unchanged values.
  const titleRecord=selected.records.find(a=>a.name===titleShape.name);
  p.delete(selected.records.filter(a=>a.id!==titleRecord.id&&['shape','textbox','table'].includes(a.kind)).map(a=>a.id));
  text(s,`# ${i+1}`,145,491,180,18,10.67,'#808080','slide-number');
  switch(d.type){
  case 'agenda':bullets(s,d.bullets,{y:111,gap:5});break;
  case 'problem':
   bullets(s,d.bullets,{y:96,h:112});
   restyleChart(s.charts.items[0],{x:187,y:222,w:587,h:231,title:'Equal-Power-Fade',legend:true});break;
  case 'two':case 'question':case 'pipeline':case 'features':case 'study':case 'direct':case 'limits':case 'conclusion':case 'backupRanking':
   bullets(s,d.bullets,{gap:d.type==='limits'?4:5});break;
  case 'learning':
   bullets(s,d.bullets,{x:55.33,y:124,w:440,h:309,gap:9});
   text(s,d.equation1,530,142,390,62,29.33);
   text(s,d.equation2,530,235,390,62,29.33);
   text(s,d.equation3,530,328,390,62,26.67);break;
  case 'controls':
   bullets(s,d.bullets,{y:96,h:115});
   restyleChart(s.charts.items[0],{x:187,y:222,w:587,h:231,title:'Schematische Übergabeposition'});break;
  case 'objective':
   bullets(s,d.bullets,{y:105,w:421,h:285,gap:4});
   restyleChart(s.charts.items[0],{x:500,y:122,w:412,h:253,title:'Energieform (schematisch)'});
   bullets(s,d.caveats,{y:409,h:43,gap:0,size:20});break;
  case 'models':
   table(s,d.table,{h:235,widths:[280,265,334],size:20});
   bullets(s,d.caveats,{y:373,h:80,gap:4,size:20});break;
  case 'data':
   bullets(s,d.bullets,{y:98,h:85,gap:5});
   table(s,d.table,{y:211,h:143,widths:[345,150,175,209],size:20});
   bullets(s,d.caveats,{y:386,h:70,gap:3,size:20});break;
  case 'loss':
   table(s,d.table,{h:231,widths:[358,255,266]});
   bullets(s,d.caveats,{y:355,h:100,gap:3,size:20});break;
  case 'listening':
   table(s,d.table,{h:231,widths:[348,147,220,164]});
   bullets(s,d.caveats,{y:355,h:100,gap:3,size:20});break;
  case 'backupProtocols':
   table(s,d.table,{h:238,widths:[215,325,195,144],size:19.5});
   bullets(s,d.caveats,{y:380,h:74,gap:4,size:19});break;
  case 'backupObjective':
   table(s,d.table,{h:250,widths:[245,280,354],size:19});
   bullets(s,d.caveats,{y:380,h:75,gap:4,size:20});break;
  default:throw Error(`Unknown slide type ${d.type}`);
  }
 }
 s.speakerNotes.text=`${d.hidden?'RESERVE – im Hauptvortrag ausgeblendet':`ZEITPLAN ${format(elapsed)}–${format(elapsed+d.seconds)} (${d.seconds} Sekunden)`}\n\n${d.notes}\n\nQuelle: ${d.source}\nThesis- und Vortragsstand: 17.11.2026.`;
 elapsed+=d.seconds;
 const stem=`slide-${String(i+1).padStart(2,'0')}`;
 await fs.writeFile(path.join(build,'draft-slides',`${stem}.png`),new Uint8Array(await (await s.export({format:'png',scale:1.5})).arrayBuffer()));
 await fs.writeFile(path.join(build,'draft-slides',`${stem}.json`),await (await s.export({format:'layout'})).text());
 console.log(`rendered ${i+1}: ${d.title}`);
}
await fs.writeFile(path.join(build,'content-inspect.ndjson'),(await p.inspect({select:'$.slides[*]',include:['index','title','layout','elements.text','notes.text']})).ndjson);
if(process.argv.includes('--draft')){console.log('Draft render complete');process.exit(0);}
const candidate=path.join(build,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
const final=path.join(root,'presentations/output/BeatBridge_Mastervortrag_20min_20261117.pptx');
// Exclusive-copy fallback for the verified workspace hard-link EPERM only.
const nativeLink=fs.link;
fs.link=async(a,b)=>{try{return await nativeLink(a,b);}catch(e){if(e.code!=='EPERM'||b!==final||path.dirname(a)!==path.dirname(final)||!a.endsWith('.validated'))throw e;return fs.copyFile(a,b,fsConstants.COPYFILE_EXCL);}};
const owners=[11,12,13,15,20,21];
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,
 pythonExecutable:path.join(root,'.venv/Scripts/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','9144000,5143500','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],
 fontPolicy:{basis:'reference',families:[font],referencePath:reference,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(reference)).digest('hex')},
 requiredNativeTableOwnerSlides:owners,requiredNativeChartOwnerSlides:[3,9,10],nativeChartTargetApplication:'powerpoint',verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation-final.json')});
fs.link=nativeLink;
console.log(JSON.stringify({finalPath:result.finalPath,sha256:result.finalSha256,seconds:elapsed,slides:slides.length,layout:result.presentationLayout,package:result.packageIntegrity}));
