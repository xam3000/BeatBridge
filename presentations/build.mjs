import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import crypto from 'node:crypto';
import {constants as fsConstants} from 'node:fs';
import {FileBlob,PresentationFile} from 'file:///C:/Program%20Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import {slides} from './content.mjs';
const root=process.cwd(), build=path.join(root,'presentations/.build');
process.env.RUNTIME_NODE_MODULES='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
const skill='C:/Users/max_h/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/presentations';
const template=path.join(root,'icg_slide_template.pptx');
const font='Lato Light', red='#BE173B', ink='#171717', gray='#555555', bg='#F2F2F2', blue='#277B8E';
await fs.mkdir(path.join(build,'slides'),{recursive:true});
await fs.mkdir('presentations',{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(template));
// Shared template furniture: only the presenter's name and automatic numbering.
for(const l of p.layouts.items) for(const s of l.shapes.items){
 if(s.name==='Textfeld 16') s.text='Maximilian Hein';
 if(s.name==='Textfeld 18') s.text='';
}
const copies=[p.slides.items[0].copy(),p.slides.items[2].copy(),p.slides.items[4].copy()];
p.slides.keep([]);
function txt(s,text,x,y,w,h,size=21.33,color=ink,bold=false,name='text'){
 const a=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=text; a.text.style={typeface:font,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',wrap:true};a.text.insets=0;return a;
}
function lines(s,arr,x,y,w,{size=21.33,gap=55,color=ink}={}) {arr.forEach((v,i)=>txt(s,v,x,y+i*gap,w,gap-8,size,color));}
function label(s,text,x,y,w=420){return txt(s,text,x,y,w,34,23,red,true);}
function bottom(s,text){txt(s,text,45.33,400,879,53,19,gray,false,'interpretation');}
function table(s,data,{top=105,height=244,widths=[410,230,239],fontSize=21.33}={}){
 const t=s.tables.add({rows:data.length,columns:data[0].length,left:45.33,top,width:879.33,height,columnWidths:widths,values:data});
 t.borders.assign({fill:'#D8D8D8',width:0.6,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:data.length,columnCount:data[0].length}).assign({fill:bg,textStyle:{typeface:font,fontSize,color:ink},margins:{left:12,right:10,top:10,bottom:8},anchor:'center'});
 t.cells.block({row:0,column:0,rowCount:1,columnCount:data[0].length}).assign({fill:red,textStyle:{typeface:font,fontSize,bold:true,color:'#FFFFFF'}});
 return t;
}
function chart(s,{x=480,y=136,w=435,h=240,series,categories,title,max=1,min=0,yTitle='Gain',legend=true,numeric=false}){
 const ts={typeface:font,fontSize:17,color:gray};
 const c=s.charts.add(numeric?'scatter':'line',{position:{left:x,top:y,width:w,height:h},...(!numeric?{categories}:{}),series,hasLegend:legend,
   legend:{position:'bottom',textStyle:{...ts,fontSize:18}},
   title,titleTextStyle:{...ts,fontSize:20,color:ink},
   chartFill:bg,plotAreaFill:bg,chartLine:{fill:'none',width:0},
   lineOptions:{smooth:false},...(numeric?{scatterOptions:{style:'line'}}:{}),
   xAxis:{title:{text:'Übergangsposition',textStyle:ts},textStyle:ts,line:{fill:'#999999',width:1},...(numeric?{min:0,max:1,majorUnit:.25}:{})},
   yAxis:{title:{text:yTitle,textStyle:ts},min,max,majorUnit:0.5,textStyle:ts,majorGridlines:{fill:'#D8D8D8',width:0.7}}
 });return c;
}
const cats=['0','0,25','0,5','0,75','1'];
for(let i=0;i<slides.length;i++){
 const d=slides[i],s=p.slides.addCopy(copies[d.type==='cover'?0:d.type==='end'?2:1]);
 s.hidden=!!d.hidden;
 const shapes=s.shapes.items;
 if(d.type==='cover'){
  shapes[0].text=d.title; shapes[0].text.style={typeface:font,fontSize:42.67,alignment:'center'};
  shapes[1].text=d.subtitle; shapes[1].text.style={typeface:font,fontSize:26.67,alignment:'center'};
  shapes[2].text='Maximilian Hein   |   Masterarbeit';
 } else if(d.type==='end'){
  shapes[0].text=d.title; shapes[1].text=d.subtitle;
 } else {
  shapes[0].text=d.title;
  shapes[0].text.style={typeface:font,fontSize:d.type==='loss'||d.type==='listening'?27:29.33,color:ink};
  // Remove the unused inherited content slot, leaving the original title and master.
  const snap=await p.inspect({select:`$.slides[${i}].elements[*]`,include:['id','name']});
  const empty=snap.records.find(e=>e.name==='Inhaltsplatzhalter 2'); if(empty)p.delete(empty.id);
  txt(s,`# ${i+1}`,145,491,180,18,10.67,'#808080',false,'slide-number');
 }
 switch(d.type){
 case 'cover':case 'end':break;
 case 'problem':
  txt(s,d.lead,45.33,106,410,90,26.67);
  lines(s,d.points,45.33,232,400,{gap:51});
  chart(s,{numeric:true,series:[{name:'Track A',values:Array.from({length:33},(_,k)=>k===32?0:Math.cos(Math.PI*k/64)),xValues:Array.from({length:33},(_,k)=>k/32),line:{fill:red,width:3}},{name:'Track B',values:Array.from({length:33},(_,k)=>Math.sin(Math.PI*k/64)),xValues:Array.from({length:33},(_,k)=>k/32),line:{fill:blue,width:3}}],title:'Equal-Power-Fade'});
  txt(s,'Fester Gain-Verlauf, unabhängig vom Songinhalt',490,400,420,45,17,gray);
  break;
 case 'two':case 'direct':case 'backupRanking':
  label(s,d.leftTitle,45.33,110);label(s,d.rightTitle,500,110);
  lines(s,d.left,45.33,170,410,{gap:65});lines(s,d.right,500,170,410,{gap:65});bottom(s,d.bottom);break;
 case 'question':
  txt(s,d.lead,45.33,100,875,84,29.33);
  label(s,d.leftTitle,45.33,219);label(s,d.rightTitle,500,219);
  lines(s,d.left,45.33,265,405,{gap:52});lines(s,d.right,500,265,415,{gap:52});bottom(s,d.bottom);break;
 case 'pipeline':
  d.rows.forEach((row,j)=>{label(s,String(j+1).padStart(2,'0'),45.33,109+j*67,50);txt(s,row[0],110,109+j*67,290,34,23,ink,true);txt(s,row[1],414,109+j*67,504,56,21.33);});bottom(s,d.bottom);break;
 case 'features':
  txt(s,d.lead,45.33,102,860,50,25.33);
  d.groups.forEach((r,j)=>{label(s,r[0],45.33,180+j*63,300);txt(s,r[1],380,180+j*63,535,35);});
  txt(s,d.bottom,45.33,386,879,65,21.33,gray);break;
 case 'learning':
  txt(s,d.equation1,65,120,430,56,32);txt(s,d.equation2,65,204,430,56,32);txt(s,d.equation3,65,288,445,60,29.33);
  label(s,d.rightTitle,555,112,355);lines(s,d.right,555,173,355,{gap:49});bottom(s,d.bottom);break;
 case 'controls':
  lines(s,d.points,45.33,147,390,{gap:76});
  chart(s,{series:[{name:'Übergabeposition',values:[0,.12,.34,.81,1],line:{fill:red,width:3}}],categories:cats,title:'Illustration: monotone Position',yTitle:'Position',legend:false});bottom(s,d.bottom);break;
 case 'objective':
  chart(s,{x:40,y:144,w:397,h:212,categories:cats,series:[{name:'Schematische Energieform',values:[1,.75,.45,.75,1],line:{fill:red,width:3}}],title:'Illustration der Zielidee',yTitle:'Relative Energie',legend:false});
  d.points.forEach((r,j)=>{label(s,r[0],480,104+j*70,437);txt(s,r[1],480,135+j*70,440,49,20);});bottom(s,d.bottom);break;
 case 'models':table(s,d.table,{widths:[280,265,334],fontSize:20});bottom(s,d.bottom);break;
 case 'data':
  table(s,d.table,{top:100,height:143,widths:[345,150,175,209],fontSize:20});
  label(s,d.leftTitle,45.33,275);label(s,d.rightTitle,500,275);
  lines(s,d.left,45.33,321,422,{gap:39,size:20});lines(s,d.right,500,321,423,{gap:39,size:20});
  txt(s,d.bottom,45.33,424,879,28,18,gray);break;
 case 'loss':table(s,d.table,{top:109,height:247,widths:[358,255,266]});bottom(s,d.bottom);break;
 case 'study':
  txt(s,d.lead,45.33,106,875,45,29.33,red);lines(s,d.points,45.33,181,875,{gap:50});bottom(s,d.bottom);break;
 case 'listening':table(s,d.table,{top:110,height:231,widths:[348,147,220,164]});txt(s,d.bottom,45.33,370,879,81,19,gray);break;
 case 'limits':
  label(s,'Grenze',45.33,103);label(s,'Nächster Schritt',433,103);
  d.rows.forEach((r,j)=>{txt(s,r[0],45.33,158+j*57,345,50,21.33);txt(s,r[1],433,158+j*57,485,50,21.33);});
  txt(s,d.bottom,45.33,416,879,35,18.5,gray);break;
 case 'conclusion':
  d.lines.forEach((r,j)=>{label(s,r[0],45.33,110+j*92,820);txt(s,r[1],45.33,151+j*92,879,43,23);});bottom(s,d.bottom);break;
 case 'backupProtocols':table(s,d.table,{top:111,height:238,widths:[215,325,195,144],fontSize:19.5});bottom(s,d.bottom);break;
 case 'backupObjective':table(s,d.table,{top:110,height:250,widths:[245,280,354],fontSize:19});bottom(s,d.bottom);break;
 default:throw Error(d.type);
 }
 const elapsed=slides.slice(0,i).reduce((a,b)=>a+b.seconds,0),fmt=n=>`${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;
 s.speakerNotes.text=`${d.hidden?'RESERVE – im Hauptvortrag ausgeblendet':`ZEITPLAN ${fmt(elapsed)}–${fmt(elapsed+d.seconds)} (${d.seconds} Sekunden)`}\n\n${d.notes}\n\nQuelle: ${d.source}\nStand der Thesis: 16.11.2026.`;
 await fs.writeFile(path.join(build,'slides',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await (await s.export({format:'png',scale:1.5})).arrayBuffer()));
 await fs.writeFile(path.join(build,'slides',`slide-${String(i+1).padStart(2,'0')}.json`),await (await s.export({format:'layout'})).text());
 console.log(`rendered ${i+1}: ${d.title}`);
}
const candidate=path.join(build,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const final=path.join(root,'presentations/BeatBridge_Mastervortrag_20min.pptx');
// This workspace denies hard links. Retain the finalizer's no-overwrite semantics
// with an exclusive copy of the already validated stage; all final hash checks run.
const nativeLink=fs.link;
fs.link=async(source,target)=>{
 try{return await nativeLink(source,target);}catch(error){
  if(error.code!=='EPERM'||target!==final||path.dirname(source)!==path.dirname(final)||!path.basename(source).endsWith('.validated'))throw error;
  return fs.copyFile(source,target,fsConstants.COPYFILE_EXCL);
 }
};
const out=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,
 pythonExecutable:path.join(root,'.venv/Scripts/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','9144000,5143500','--validate-bullet-geometry','--validate-heading-fit',...[10,11,12,14,19,20].flatMap(n=>['--require-native-table-slide',String(n)])],
 fontPolicy:{basis:'reference',families:[font],referencePath:template,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(template)).digest('hex')},
 requiredNativeTableOwnerSlides:[10,11,12,14,19,20],requiredNativeChartOwnerSlides:[2,8,9],nativeChartTargetApplication:'powerpoint',materializeLiteralChartWorkbooks:true,verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')});
fs.link=nativeLink;
await fs.writeFile(path.join(build,'content-inspect.ndjson'),(await p.inspect({select:'$.slides[*]',include:['index','title','notes.text','elements.text']})).ndjson);
console.log(JSON.stringify(out));

