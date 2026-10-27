// Execute the frozen original TSX, schemas and data, with a closed VM and hooks.
// Compiler/React packages are exactly those installed from the frozen V1 lock.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const root = path.resolve(import.meta.dirname, '..');
const locked = createRequire(path.join(root, '.qa/v1/package.json'));
const esbuild = locked('esbuild');
const source = path.join(root, 'fixtures/source');
function session(command, samples) {
  let cursor=0, hook=0, states=[], memos=[], effects=[], calls=[];
  const node=(type,props,key)=>({type,props:props??{},key});
  const api = {Action:Object.assign('Action',{}), ActionPanel:'ActionPanel', List:Object.assign(function(){},{Item:Object.assign('List.Item',{}),Dropdown:Object.assign(function(){},{Item:'List.Dropdown.Item'})}),
    Clipboard:{copy:async text=>{effects.push(['copy',text]);}},showHUD:async text=>{effects.push(['hud',text]);},closeMainWindow:async()=>{effects.push(['close']);}};
  api.List.Item={Detail:'List.Item.Detail',toString:()=> 'List.Item'};
  const hooks={useState(initial){const i=hook++;if(!(i in states)) states[i]=typeof initial==='function'?initial():initial;return [states[i],v=>{states[i]=typeof v==='function'?v(states[i]):v;}];},useMemo(fn,deps){const i=hook++;if(!memos[i]||deps.some((d,n)=>d!==memos[i].deps[n])) memos[i]={value:fn(),deps};return memos[i].value;}};
  const cache=new Map();
  const math=Object.create(Math);math.random=()=>{const n=samples[cursor++]??0.5;calls.push(n);return n;};
  const context=vm.createContext({Math:math,console:{log(){throw Error('Unexpected log');}},fetch(){throw Error('Network forbidden');},process:undefined,Buffer:undefined,setTimeout:undefined});
  function load(file) {
    if(cache.has(file))return cache.get(file).exports;
    const module={exports:{}};cache.set(file,module);
    if(file.endsWith('.json')) {module.exports=JSON.parse(fs.readFileSync(file,'utf8'));return module.exports;}
    const code=esbuild.transformSync(fs.readFileSync(file,'utf8'),{loader:file.endsWith('tsx')?'tsx':'ts',format:'cjs',jsx:'automatic',target:'es2022'}).code;
    const req=name=>{
      if(name==='@raycast/api')return api;
      if(name==='react')return hooks;
      if(name==='react/jsx-runtime')return {jsx:node,jsxs:node,Fragment:'Fragment'};
      if(!name.startsWith('.'))throw Error('Forbidden require: '+name);
      const base=path.resolve(path.dirname(file),name);
      if(!base.startsWith(source+path.sep))throw Error('Outside source');
      const found=[base,base+'.ts',base+'.tsx',base+'.json'].find(p=>fs.existsSync(p)&&fs.statSync(p).isFile());
      assert.ok(found,name);return load(found);
    };
    const fn=vm.runInContext('(function(require,module,exports){'+code+'\n})',context,{timeout:1000});
    fn(req,module,module.exports);return module.exports;
  }
  const main=load(path.join(source,'src',command+(command==='quick-compliment'?'.ts':'.tsx'))).default;
  const data=load(path.join(source,'src/data',command==='gratitude-note'?'prompts.schema.ts':'compliments.schema.ts'));
  let tree;
  const children=n=>[n.props.children??[]].flat(Infinity).filter(Boolean);
  function snapshot(){return {selected:tree.props.selectedItemId,rows:children(tree).map(r=>({id:r.props.id,text:r.props.title,markdown:r.props.detail.props.markdown,actions:children(r.props.actions).map(a=>({title:a.props.title,shortcut:a.props.shortcut}))})),dropdown:tree.props.searchBarAccessory?{storeValue:tree.props.searchBarAccessory.props.storeValue,options:children(tree.props.searchBarAccessory).map(o=>({title:o.props.title,value:o.props.value}))}:null};}
  function render(){hook=0;tree=main();return snapshot();}
  return {render,snapshot,data,calls,effects, async event(e){
    if(e.type==='tone')tree.props.searchBarAccessory.props.onChange(e.value);
    else if(e.type==='select')tree.props.onSelectionChange(e.value);
    else {const row=children(tree).find(r=>r.props.id===e.row)??children(tree)[0];const a=children(row.props.actions).find(a=>a.props.title===(e.type==='shuffle'?'Shuffle':command==='gratitude-note'?'Copy Prompt':'Copy Compliment'));await a.props.onAction();}
    return render();
  },quick:()=>main()};
}
const cases=[];
for (const command of ['random-compliment','gratitude-note']) {
  const s=session(command,[0]);const initial=s.render();const rows=initial.rows;
  // Every original copy callback, exact prompt markdown and record ordering.
  for(let i=0;i<rows.length;i++){
    const samples=[(i+0.25)/rows.length,0.9999999999999999];const x=session(command,samples);
    const before=x.render();const events=[{type:'copy',row:rows[i].id}];
    const after=await x.event(events[0]);assert.deepEqual(x.effects,[['copy',rows[i].text],['hud','Copied: '+rows[i].text],['close']]);
    cases.push({command,samples,events,expected:[before,after],effects:x.effects});
  }
  const samples=[0,0.5,0.9999999999999999,0.25,0.75,0];const x=session(command,samples);const expected=[x.render()];const events=[];
  if(command==='random-compliment')for(const value of ['warm','playful','sincere','specific-skill','all']){
    events.push({type:'tone',value});expected.push(await x.event(events.at(-1)));
    events.push({type:'select',value:expected.at(-1).selected});expected.push(await x.event(events.at(-1)));
    events.push({type:'shuffle',row:expected.at(-1).rows[0].id});expected.push(await x.event(events.at(-1)));
  }
  else for(const row of rows){events.push({type:'select',value:row.id},{type:'shuffle',row:row.id});expected.push(await x.event(events.at(-2)),await x.event(events.at(-1)));}
  cases.push({command,samples,events,expected,effects:[]});
}
const compliments=JSON.parse(fs.readFileSync(path.join(source,'src/data/compliments.json')));
for(let i=0;i<compliments.length;i++){
  const samples=[(i+0.25)/compliments.length];const s=session('quick-compliment',samples);await s.quick();
  assert.deepEqual(s.effects,[['copy',compliments[i].text],['hud','Copied: '+compliments[i].text]]);
  cases.push({command:'quick-compliment',samples,events:[],expected:[],effects:s.effects});
}
// Schema functions are also executed, not inferred through text matches.
for(const command of ['random-compliment','gratitude-note']){
  const s=session(command,[0]);const values=command==='gratitude-note'?s.data.prompts:s.data.compliments;
  for(const bad of [null,{},[null],[{...values[0],id:''}],[values[0],values[0]]])assert.throws(()=>s.data.validate(bad));
  assert.equal(s.data.validate(values).length,values.length);
}
const result={sourceSha:'a1bf2ff51f80251e24eaeb6d8602b5a8145d1892',raycastVersion:locked('@raycast/api/package.json').version,compliments,prompts:JSON.parse(fs.readFileSync(path.join(source,'src/data/prompts.json'))),cases};
const output=path.join(root,'.qa/source-oracle.json');fs.writeFileSync(output,JSON.stringify(result));
console.log(`Original functions executed: ${cases.length} cases; ${compliments.length} compliments; ${result.prompts.length} prompts; VM external effects blocked.`);
