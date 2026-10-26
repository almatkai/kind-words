// Frozen REAL renderer components/callbacks, evaluated before/after prerequisite patch.
import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const root=path.resolve(import.meta.dirname,'..');const esbuild=createRequire(path.join(root,'.qa/v1/package.json'))('esbuild');
function component(base,file,exportName,stubs={}){
 let cursor=0,slots=[],effects=[],pending=[],changed=false;
 const node=(type,props,key)=>({type,props:props??{},key});
 const hook={useState(init){const i=cursor++;if(!(i in slots))slots[i]=typeof init==='function'?init():init;return [slots[i],v=>{const next=typeof v==='function'?v(slots[i]):v;if(!Object.is(next,slots[i]))changed=true;slots[i]=next;}];},useRef(init){const i=cursor++;return slots[i]??(slots[i]={current:init});},useMemo(fn,deps){const i=cursor++;if(!slots[i]||deps.some((d,n)=>d!==slots[i].deps[n]))slots[i]={deps,value:fn()};return slots[i].value;},useCallback(fn,deps){return hook.useMemo(()=>fn,deps);},useEffect(fn,deps){const i=cursor++;if(!slots[i]||!deps||deps.some((d,n)=>d!==slots[i][n])){slots[i]=deps;pending.push(fn);}}};
 const unknown=new Proxy({}, {get:(_,key)=>String(key)});hook.default=hook;hook.createElement=(type,props,...children)=>node(type,{...props,children});
 const calls=[];const window={tezbar:new Proxy({}, {get:(_,name)=>stubs[name]??(async p=>{calls.push([name,p]);return {ok:true,mode:'no-view',message:'Copied: synthetic'};})}),setTimeout:()=>1,clearTimeout(){}};
 const context=vm.createContext({window,console:{log(){},error(){}},setTimeout:()=>1,clearTimeout(){},fetch(){throw Error('Network forbidden');},process:undefined});
 const code=esbuild.transformSync(fs.readFileSync(path.join(base,file),'utf8'),{loader:'tsx',format:'cjs',jsx:'automatic',target:'es2022'}).code;
 const module={exports:{}};
 const req=name=>{if(name==='react')return hook;if(name==='react/jsx-runtime')return {jsx:node,jsxs:node,Fragment:'Fragment'};if(name.includes('extensionSessionRefresh'))return {startSessionRefresh:()=>()=>{}};if(name.includes('colorConverter'))return {buildColorConversionResults:()=>[]};if(name.endsWith('/primitives'))return {...unknown,cx:(...x)=>x.filter(Boolean).join(' ')};return unknown;};
 vm.runInContext('(function(require,module,exports){'+code+'\n})',context,{timeout:1000})(req,module,module.exports);
 return {calls,render(props){let tree;for(let i=0;i<8;i++){cursor=0;pending=[];changed=false;tree=module.exports[exportName](props);for(const fn of pending)fn();if(!changed)return tree;}throw Error('Hook render failed to settle');}};
}
function nodes(tree){if(!tree||typeof tree!=='object')return [];return [tree,...[tree.props?.children??[]].flat(Infinity).flatMap(nodes)];}
function label(n){return [n.props.children??[]].flat(Infinity).filter(v=>typeof v==='string').join('');}
function test(base,patched){
 const list=component(base,'src/renderer/src/raycast-api/list-runtime.tsx','ListRuntime');
 let calls=[];const props={root:{type:'List',props:{selectedItemId:'b',searchText:'',__hasServerSearch:true,onSelectionActionId:'select',searchBarAccessory:{type:'List.Dropdown',props:{actionId:'tone',value:'warm'},children:[{type:'List.Dropdown.Item',props:{title:'All',value:''}},{type:'List.Dropdown.Item',props:{title:'Warm',value:'warm'}}]}},children:['a','b'].map(id=>({type:'List.Item',props:{id,title:id,actionIds:['copy-'+id]}}))},title:'Synthetic',commandName:'synthetic',onBack(){},onRunPrimaryAction:(...args)=>calls.push(args),actions:[{id:'copy-a',title:'Copy'},{id:'copy-b',title:'Copy'}],onOpenActions(){},onSearchTextChanged(){},onLoadMore(){}};
 let tree=list.render(props);let all=nodes(tree);const rows=all.filter(n=>n.props['data-idx']!==undefined);
 assert.equal(rows[1].props.className.includes('bg-white/[0.16]'),patched,'selectedItemId must focus random row');
 const tabs=all.filter(n=>n.type==='button'&&['All','Warm'].includes(label(n)));
 assert.equal(tabs.find(n=>label(n)==='Warm').props.className.includes('bg-white/[0.14]'),patched,'controlled restored tone');
 // Real click callback must pass empty string All, not fallback to first truthy value.
 tabs.find(n=>label(n)==='All').props.onClick();assert.equal(calls.at(-1)[1].value,'');
 if(patched){props.root={...props.root,props:{...props.root.props,searchBarAccessory:{...props.root.props.searchBarAccessory,props:{actionId:'tone',value:''}}}};tree=list.render(props);all=nodes(tree);assert(all.find(n=>n.type==='button'&&label(n)==='All').props.className.includes('bg-white/[0.14]'));}
 calls=[];nodes(tree).find(n=>n.props['data-idx']===0).props.onMouseEnter();assert.equal(calls.length,patched?1:0);if(patched)assert.equal(calls[0][1].value,'a');
 calls=[];nodes(tree).find(n=>n.props['data-idx']===0).props.onClick();assert.equal(calls[0][0],'copy-a');assert.equal(calls.length,1);
 const detail=component(base,'src/renderer/src/raycast-api/detail-runtime.tsx','DetailRuntime');let args;
 const d=detail.render({root:{type:'Detail',props:{markdown:'synthetic'}},title:'Retry',onBack(){},onRunPrimaryAction:(...a)=>args=a,onOpenActions(){}});
 nodes(d).find(n=>n.type==='button'&&label(n)==='Enter').props.onClick({type:'click',synthetic:true});assert.equal(args.length,patched?0:1,'MouseEvent must not be actionId');
 const lifecycle=component(base,'src/renderer/ExtensionRuntimeView.tsx','default');let back=0;
 const initial={ok:true,mode:'view',sessionId:'synthetic',extensionId:'synthetic',commandName:'quick-compliment',title:'Retry',refreshMs:null,root:{type:'Detail',props:{markdown:'Retry'}},actions:[{id:'retry',kind:'action',title:'Retry'}]};
 const t=lifecycle.render({initial,onBack(){back++;}});const surface=nodes(t).find(n=>n.props.onInvokeAction);
 return surface.props.onInvokeAction('retry').then(()=>{assert.equal(lifecycle.calls.filter(c=>c[0]==='extensionDisposeSession').length,patched?1:0);assert.equal(back,patched?1:0);});
}
await test(path.join(root,'fixtures/host'),false);await test(path.join(root,'.qa/patched-host'),true);
console.log('PASS actual pinned renderer callbacks before/after: controlled dropdown including empty All, selected row, selection and primary click, Detail MouseEvent, recovery no-view dispose/onBack. DOM/GUI not run.');

// Original commands delegate filtering to the launcher. Exercise the unmodified
// pinned renderer's actual clientSideFilter path, not a regex or reimplementation.
const searchCases=[];
const sourceData=JSON.parse(fs.readFileSync(path.join(root,'.qa/source-oracle.json')));
for(const [command,records] of [['random-compliment',sourceData.compliments],['gratitude-note',sourceData.prompts]]){
 const client=component(path.join(root,'fixtures/host'),'src/renderer/src/raycast-api/list-runtime.tsx','ListRuntime');
 for(const query of ['', 'you','  YOU  ','who','today','playlist','—','?',"'",'specific-skill','İ','Σ','nothing synthetic matches']){
  const props={root:{type:'List',props:{searchText:query},children:records.map(r=>({type:'List.Item',props:{id:r.id,title:r.text}}))},title:'Synthetic',commandName:command,onBack(){},onRunPrimaryAction(){},actions:[],onOpenActions(){},onSearchTextChanged(){},onLoadMore(){}};
  const tree=client.render(props);const ids=nodes(tree).filter(n=>n.type==='li').map(n=>n.key);
  searchCases.push({command,query,ids});
 }
}
fs.writeFileSync(path.join(root,'.qa/search-oracle.json'),JSON.stringify(searchCases));
console.log('PASS 26 search cases executed through actual pinned original default renderer filter; oracle emitted for real Rust-pipe comparison.');
