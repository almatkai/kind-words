#!/usr/bin/env python3
"""Real SDK JSONL pipes. Every reverse effect is synthetic; never touches OS APIs."""
import json, os, pathlib, queue, subprocess, threading, time, tempfile, uuid
from functools import lru_cache
ROOT=pathlib.Path(__file__).resolve().parents[1]
QA=ROOT/'.qa';QA.mkdir(exist_ok=True)
FIXTURE=ROOT/'target/debug/kind-words-qa-fixture'
DEFAULT = object()
@lru_cache(maxsize=1)
def visibility_default():
 # Execute extracted real router/platform code, and reject a stale fixture binary.
 contract=json.loads(subprocess.check_output([str(FIXTURE),'--host-contract'],text=True))
 base=ROOT/'fixtures/host/src-tauri/src/native_core'
 assert contract['platformSource']==(base/'platform.rs').read_text()
 assert contract['routerSource']==(base/'extensions/process_host.rs').read_text()
 assert contract['visibility'] is None,contract['visibility']
 return contract['visibility']
def default_response(method):
 if method=='host.window.visibility':return visibility_default()
 if method=='host.clipboard.write':return {'ok':True} # mock clipboard producer, strict contract
 raise AssertionError('unmocked reverse method: '+method)
class Host:
 def __init__(self, samples=(), binary=FIXTURE, data=None):
  self.dir=tempfile.TemporaryDirectory(dir=QA);self.base=pathlib.Path(self.dir.name)
  env=dict(os.environ);env.update(HOME=str(self.base),TMPDIR=str(self.base),XDG_CACHE_HOME=str(self.base))
  self.p=subprocess.Popen([str(binary),*map(str,samples)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,env=env)
  self.q=queue.Queue();self.n=0;self.effects=[];self.replies={};self.held=[]
  def read():
   for line in self.p.stdout:self.q.put(json.loads(line))
   self.q.put(None)
  self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
  hello=self.next();assert hello['type']=='hello' and hello['protocol']==1 and hello['id']=='com.tezbar.native.kind-words' and hello['sdkVersion']=='0.1.1',hello
  for p in ['package','data','temp']:(self.base/p).mkdir()
  self.data=pathlib.Path(data) if data else self.base/'data'
  assert self.call('initialize',dict(protocol=1,extensionId=hello['id'],platform='macOS',packageDir=str(self.base/'package'),dataDir=str(self.data),tempDir=str(self.base/'temp'),grantedCapabilities=['clipboard.write','window.visibility'],migrationPaths={},reason='command'))['result']['ready']
 def next(self):
  x=self.q.get(timeout=6);assert x is not None,'unexpected EOF';return x
 def send(self,x):
  self.p.stdin.write(json.dumps(x,separators=(',',':'))+'\n');self.p.stdin.flush()
 def request(self,method,params):
  self.n+=1;rid='h:'+str(uuid.UUID(int=self.n));self.send(dict(type='request',id=rid,method=method,params=params));return rid
 def reply(self,msg,result=DEFAULT,error=None):
  self.send(dict(type='response',id=msg['id'],**({'error':error} if error is not None else {'result':default_response(msg['method']) if result is DEFAULT else result})))
 def wait(self,rid,ack=True):
  if rid in self.replies:return self.replies.pop(rid)
  while True:
   x=self.next()
   if x['type']=='request':
    assert x['method'] in ['host.clipboard.write','host.window.visibility'],x
    self.effects.append((x['method'],x['params']))
    if ack:self.reply(x)
    else:self.held.append(x);return x
   elif x['type']=='response':
    if x['id']==rid:return x
    self.replies[x['id']]=x
   else:assert x['type'] in ['cancel','event'],x
 def call(self,m,p,ack=True):return self.wait(self.request(m,p),ack)
 def open(self,cmd,sid='s',ack=True):return self.call('session.open',dict(sessionId=sid,commandName=cmd,preferences={},argumentValues={}),ack)
 def op(self,op,p=None,sid='s',ack=True):return self.call('session.call',dict(sessionId=sid,operation='extension:'+op,payload=p or {}),ack)
 def dispose(self,sid='s'):return self.call('session.dispose',dict(sessionId=sid))
 def close(self):
  if self.p.poll() is None:
   self.p.stdin.close();self.p.wait(timeout=6)
  assert self.p.returncode==0,self.p.stderr.read()
  self.reader.join(timeout=1);self.dir.cleanup()
 def __enter__(self):return self
 def __exit__(self,*_):self.close()
def result(x):assert 'result' in x,x;return x['result']
def action(v,verb,row=''):
 return next(a['id'] for a in v['actions'] if a['id'].split(':',2)[1:]==[verb,row])
def compare(v,w):
 assert v['mode']=='view' and v['refreshMs'] is None,v
 props=v['root']['props'];assert props['selectedItemId']==w['selected'],(props['selectedItemId'],w['selected'])
 rows=v['root']['children'];assert len(rows)==len(w['rows'])
 for r,e in zip(rows,w['rows']):
  p=r['props'];assert [p['id'],p['title'],p['detail']['props']['markdown']]==[e['id'],e['text'],e['markdown']]
  acts=[next(a for a in v['actions'] if a['id']==aid) for aid in p['actionIds']]
  assert [{k:a[k] for k in ['title','shortcut'] if k in a} for a in acts]==e['actions']
 if w['dropdown']:
  assert [{'title':o['props']['title'],'value':o['props']['value']} for o in props['searchBarAccessory']['children']]==w['dropdown']['options']
def source_cases():
 oracle=json.loads((QA/'source-oracle.json').read_text())
 assert (ROOT/'data/compliments.json').read_bytes()==(ROOT/'fixtures/source/src/data/compliments.json').read_bytes()
 assert (ROOT/'data/prompts.json').read_bytes()==(ROOT/'fixtures/source/src/data/prompts.json').read_bytes()
 for c in oracle['cases']:
  with Host(c['samples']) as h:
   v=result(h.open(c['command']))
   if c['command']=='quick-compliment':assert v['mode']=='no-view'
   else:
    compare(v,c['expected'][0])
    for e,w in zip(c['events'],c['expected'][1:]):
     verb=e['type'];p={'actionId':action(v,verb,e.get('row',''))}
     if 'value' in e:p['formValues']={'value':e['value']}
     v=result(h.op('invoke-action',p))
     if verb=='copy':assert v['mode']=='no-view'
     else:compare(v,w)
   expected=[('host.clipboard.write',{'text':e[1]}) if e[0]=='copy' else ('host.window.visibility',{'visible':False}) for e in c['effects'] if e[0]!='hud']
   assert h.effects==expected,(h.effects,expected)
   if c['effects']:assert v['message']==c['effects'][1][1]
   h.dispose()
 print('PASS 164 executed original-source cases vs real SDK process, every record/copy/detail/order/tone/selection/shuffle')
def search_cases():
 cases=json.loads((QA/'search-oracle.json').read_text())
 for command in ['random-compliment','gratitude-note']:
  with Host([0]) as h:
   result(h.open(command))
   for c in [c for c in cases if c['command']==command]:
    v=result(h.op('search-text-changed',{'searchText':c['query']}))
    assert [r['props']['id'] for r in v['root']['children']]==c['ids'],c
    assert v['root']['props']['searchText']==c['query']
   h.dispose()
 print('PASS 26 actual pinned original renderer filter oracles vs Rust pipes (case/space/punctuation/Unicode/context exclusion/order)')
def protocol_cases():
 with Host([0,0.9999999999999999]) as h:
  v=result(h.open('random-compliment'));old=action(v,'copy','warm-001')
  a=h.request('session.call',dict(sessionId='s',operation='extension:search-text-changed',payload={'searchText':'group'}))
  b=h.request('session.call',dict(sessionId='s',operation='extension:search-text-changed',payload={'searchText':'  you  '}))
  rb=result(h.wait(b));h.wait(a)
  assert len(rb['root']['children'])==sum('you' in r['text'].lower() for r in json.loads((ROOT/'data/compliments.json').read_text()))
  assert 'error' in h.op('invoke-action',{'actionId':old});assert not h.effects
  empty=result(h.op('search-text-changed',{'searchText':'absent synthetic phrase'}));assert empty['root']['children']==[]
  again=result(h.op('search-text-changed',{'searchText':''}));assert 'error' in h.op('invoke-action',{'actionId':old})
  oversized=result(h.op('search-text-changed',{'searchText':'x'*4097}));assert oversized['root']['type']=='Detail'
  recovered=result(h.op('invoke-action',{'actionId':action(oversized,'load')}));assert recovered['root']['props']['searchText']==''
  invalid=result(h.op('invoke-action',{'actionId':action(recovered,'tone'),'formValues':{'value':'invalid synthetic tone'}}));assert invalid['root']['type']=='Detail'
  # Even a guessed current-revision row action is unavailable in the recovery view.
  guessed=invalid['actions'][0]['id'].split(':')[0]+':copy:warm-001';assert 'error' in h.op('invoke-action',{'actionId':guessed})
  recovered=result(h.op('invoke-action',{'actionId':action(invalid,'load')}))
  # Current copy cancelled after dispatch; never automatic retry on refresh.
  rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':action(recovered,'copy','warm-001')}))
  reverse=h.wait(rid,ack=False);prepared=reverse['params']
  h.send(dict(type='cancel',requestId=rid,reason='synthetic cancellation'));assert 'error' in h.wait(rid)
  h.reply(reverse) # late ACK is ignored; exact prepared bytes still uncertain.
  recovery=result(h.op('refresh-session'));assert recovery['actions'][0]['title']=='Retry Copy';assert len(h.effects)==1
  r2=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':action(recovery,'retry')}))
  copy=h.wait(r2,ack=False);assert copy['params']==prepared;h.reply(copy)
  close=h.wait(r2,ack=False);assert close['method']=='host.window.visibility';h.reply(close,error={'code':'mock','message':'synthetic failure'})
  recovery=result(h.wait(r2));assert recovery['actions'][0]['title']=='Retry Close'
  success=result(h.op('invoke-action',{'actionId':action(recovery,'retry')}));assert success['mode']=='no-view'
  assert [e[0] for e in h.effects]==['host.clipboard.write','host.clipboard.write','host.window.visibility','host.window.visibility']
  assert result(h.op('refresh-session'))['mode']=='no-view';assert len(h.effects)==4
  h.dispose();assert 'error' in h.op('invoke-action',{'actionId':old})
 for ack in [None,True,False,{}, {'ok':False},{'ok':True,'error':'contradiction'},{'ok':True,'message':False},{'ok':True,'extra':1}]:
  with Host([0]) as h:
   rid=h.request('session.open',dict(sessionId='s',commandName='quick-compliment',preferences={},argumentValues={}))
   x=h.wait(rid,ack=False)
   h.reply(x,result=ack) # explicit None must remain literal null
   recovery=result(h.wait(rid));assert recovery['mode']=='view';assert recovery['actions'][0]['title']=='Retry Copy'
   assert result(h.op('refresh-session'))['mode']=='view';assert len(h.effects)==1
   assert result(h.op('invoke-action',{'actionId':action(recovery,'retry')}))['mode']=='no-view'
   assert h.effects[0]==h.effects[1];h.dispose()
 # Real five-second reverse deadline: no automatic retry, late reply cannot confirm success.
 with Host([0]) as h:
  rid=h.request('session.open',dict(sessionId='s',commandName='quick-compliment',preferences={},argumentValues={}))
  rev=h.wait(rid,ack=False);v=result(h.wait(rid));assert v['actions'][0]['title']=='Retry Copy';assert len(h.effects)==1
  h.reply(rev);assert result(h.op('refresh-session'))['mode']=='view';assert len(h.effects)==1
  assert result(h.op('invoke-action',{'actionId':action(v,'retry')}))['mode']=='no-view';h.dispose()
 # >128 cancelled no-view opens, SDK and adapter cleanup capacity; new open works.
 with Host([0]) as h:
  for i in range(140):
   rid=h.request('session.open',dict(sessionId='c'+str(i),commandName='quick-compliment',preferences={},argumentValues={}))
   rev=h.wait(rid,ack=False);h.send(dict(type='cancel',requestId=rid,reason='capacity test'));assert 'error' in h.wait(rid);h.reply(rev)
  assert result(h.open('quick-compliment'))['mode']=='no-view';h.dispose()
 # Session capacity is explicit; rejection must not execute Quick Copy.
 with Host([0]) as h:
  for i in range(128):assert result(h.open('gratitude-note',sid='full'+str(i)))['mode']=='view'
  assert 'error' in h.open('quick-compliment',sid='overflow');assert not h.effects
  h.dispose('full0');assert result(h.open('quick-compliment',sid='available'))['mode']=='no-view';h.dispose('available')
 # Disposal while waiting, then late acknowledgement. EOF separately closes waiters.
 with Host([0]) as h:
  result(h.open('gratitude-note'));v=result(h.op('refresh-session'));rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':action(v,'copy','prompt-001')}));rev=h.wait(rid,ack=False)
  h.dispose();assert 'error' in h.wait(rid);h.reply(rev)
 with Host([0]) as h:
  rid=h.request('session.open',dict(sessionId='s',commandName='quick-compliment',preferences={},argumentValues={}));h.wait(rid,ack=False)
 print('PASS search replacement/A-B-A/stale actions/oversize reachable Retry/strict clipboard ACK/pinned null visibility/non-null rejection/copy+close timeouts/exact retry/cancel/late ACK/dispose/EOF/140 cancelled opens')
def phase_contract_cases(binary=FIXTURE):
 # Ordinary source flow with actual host defaults: clipboard object, visibility null.
 for command,row in [('random-compliment','warm-001'),('gratitude-note','prompt-001')]:
  with Host([0],binary=binary) as h:
   v=result(h.open(command));assert result(h.op('invoke-action',{'actionId':action(v,'copy',row)}))['mode']=='no-view'
   assert [x[0] for x in h.effects]==['host.clipboard.write','host.window.visibility'];h.dispose()
 with Host([0],binary=binary) as h:
  assert result(h.open('quick-compliment'))['mode']=='no-view'
  assert [x[0] for x in h.effects]==['host.clipboard.write'];h.dispose()
 # Null clipboard must not advance to close, even though null visibility succeeds.
 with Host([0],binary=binary) as h:
  v=result(h.open('gratitude-note'));rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':action(v,'copy','prompt-001')}))
  copy=h.wait(rid,ack=False);h.reply(copy,result=None)
  v=result(h.wait(rid));assert v['actions'][0]['title']=='Retry Copy';assert len(h.effects)==1
  assert result(h.op('invoke-action',{'actionId':action(v,'retry')}))['mode']=='no-view'
  assert h.effects[0]==h.effects[1];assert len(h.effects)==3;h.dispose()
 # Exact selected visibility contract: structured ACKs and every non-null value fail.
 for ack in [{'ok':True},True,False,{}, {'ok':False},{'unknown':None},
             {'ok':True,'message':'synthetic'},[],0,'null']:
  with Host([0],binary=binary) as h:
   v=result(h.open('random-compliment'));old=action(v,'copy','warm-001')
   rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':old}))
   copy=h.wait(rid,ack=False);h.reply(copy,result={'ok':True,'message':'synthetic clipboard success'})
   close=h.wait(rid,ack=False);assert close['method']=='host.window.visibility';h.reply(close,result=ack)
   v=result(h.wait(rid));assert v['actions'][0]['title']=='Retry Close';retry=action(v,'retry')
   assert result(h.op('refresh-session'))['mode']=='view';assert len(h.effects)==2
   assert 'error' in h.op('invoke-action',{'actionId':old});assert len(h.effects)==2
   assert result(h.op('invoke-action',{'actionId':retry}))['mode']=='no-view'
   assert 'error' in h.op('invoke-action',{'actionId':retry})
   assert result(h.op('refresh-session'))['mode']=='no-view'
   assert [x[0] for x in h.effects]==['host.clipboard.write','host.window.visibility','host.window.visibility'];h.dispose()
 # Real five-second close timeout, then late null: no implicit replay or completion.
 with Host([0],binary=binary) as h:
  v=result(h.open('gratitude-note'));rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':action(v,'copy','prompt-001')}))
  copy=h.wait(rid,ack=False);h.reply(copy);close=h.wait(rid,ack=False)
  v=result(h.wait(rid));assert v['actions'][0]['title']=='Retry Close';h.reply(close,result=None)
  assert result(h.op('refresh-session'))['mode']=='view';assert len(h.effects)==2
  retry=action(v,'retry');assert result(h.op('invoke-action',{'actionId':retry}))['mode']=='no-view'
  assert 'error' in h.op('invoke-action',{'actionId':retry});assert len(h.effects)==3;h.dispose()
 # Cancel closing after acknowledged copy; retained checkpoint retries only close.
 with Host([0],binary=binary) as h:
  v=result(h.open('gratitude-note'));old=action(v,'copy','prompt-001');rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':old}))
  copy=h.wait(rid,ack=False);h.reply(copy);close=h.wait(rid,ack=False)
  h.send(dict(type='cancel',requestId=rid,reason='cancel close'));assert 'error' in h.wait(rid);h.reply(close,result=None)
  v=result(h.op('refresh-session'));assert v['actions'][0]['title']=='Retry Close';retry=action(v,'retry')
  assert len(h.effects)==2;assert 'error' in h.op('invoke-action',{'actionId':old})
  assert result(h.op('invoke-action',{'actionId':retry}))['mode']=='no-view'
  assert 'error' in h.op('invoke-action',{'actionId':retry})
  assert result(h.op('refresh-session'))['mode']=='no-view'
  assert [x[0] for x in h.effects]==['host.clipboard.write','host.window.visibility','host.window.visibility'];h.dispose()
 # Host errors leave close-only recovery, with no clipboard replay.
 with Host([0],binary=binary) as h:
  v=result(h.open('gratitude-note'));rid=h.request('session.call',dict(sessionId='s',operation='extension:invoke-action',payload={'actionId':action(v,'copy','prompt-001')}))
  copy=h.wait(rid,ack=False);h.reply(copy);close=h.wait(rid,ack=False);h.reply(close,error={'code':'synthetic','message':'synthetic close failure'})
  v=result(h.wait(rid));assert v['actions'][0]['title']=='Retry Close';retry=action(v,'retry')
  assert result(h.op('invoke-action',{'actionId':retry}))['mode']=='no-view'
  assert 'error' in h.op('invoke-action',{'actionId':retry})
  assert [x[0] for x in h.effects]==['host.clipboard.write','host.window.visibility','host.window.visibility'];h.dispose()
 print('PASS method-specific clipboard/visibility contract, normal browsing/quick, invalid/error/timeout/cancel close, stale Retry:',binary.name)
def storage_cases():
 with tempfile.TemporaryDirectory(dir=QA) as td:
  data=pathlib.Path(td);(data/'kind-words').mkdir();file=data/'kind-words/storage.json'
  file.write_text(json.dumps({'unrelated':{'synthetic':True},'kindWords':{'version':1,'tone':'all','future':'keep'}}))
  with Host([0,0.5],data=data) as h:
   v=result(h.open('random-compliment'));v=result(h.op('invoke-action',{'actionId':action(v,'tone'),'formValues':{'value':'sincere'}}));assert v['root']['props']['searchBarAccessory']['props']['value']=='sincere';h.dispose()
  saved=json.loads(file.read_text());assert saved['unrelated']=={'synthetic':True} and saved['kindWords']['future']=='keep'
  with Host([0,0.5],data=data) as h:
   v=result(h.open('random-compliment'));assert v['root']['props']['searchBarAccessory']['props']['value']=='sincere';assert len(v['root']['children'])==19;h.dispose()
  with Host([0]) as h:assert result(h.open('random-compliment'))['root']['props']['searchBarAccessory']['props']['value']=='all';h.dispose()
  for bad in ['{', '[]','x'*16385,json.dumps({'kindWords':{'version':2,'tone':'all'}})]:
   file.write_text(bad)
   with Host([0],data=data) as h:
    v=result(h.open('random-compliment'));assert v['root']['type']=='Detail' and v['actions'][0]['title']=='Retry';assert file.read_text()==bad
    file.write_text('{}');v=result(h.op('invoke-action',{'actionId':action(v,'load')}));assert v['root']['type']=='List';h.dispose()
  # A failed tone save keeps the desired dropdown input for deliberate Retry.
  file.write_text('{}')
  with Host([0,0.5],data=data) as h:
   v=result(h.open('random-compliment'));file.write_text('{')
   v=result(h.op('invoke-action',{'actionId':action(v,'tone'),'formValues':{'value':'playful'}}));assert v['root']['type']=='Detail'
   file.write_text('{}');v=result(h.op('invoke-action',{'actionId':action(v,'load')}));assert v['root']['props']['searchBarAccessory']['props']['value']=='playful';h.dispose()
  # Adding our own key cannot silently create an unreadable over-count store.
  many={str(i):'synthetic' for i in range(256)};file.write_text(json.dumps(many));before=file.read_bytes()
  with Host([0],data=data) as h:
   v=result(h.open('random-compliment'));v=result(h.op('invoke-action',{'actionId':action(v,'tone'),'formValues':{'value':'warm'}}));assert v['root']['type']=='Detail';assert file.read_bytes()==before;h.dispose()
  file.unlink();target=data/'synthetic.json';target.write_text('{}');file.symlink_to(target)
  with Host([0],data=data) as h:assert result(h.open('random-compliment'))['root']['type']=='Detail';h.dispose()
  assert target.read_text()=='{}'
 print('PASS atomic tone/profile isolation/restart/unknown-key retention/corrupt/schema/size/symlink guards')
if __name__=='__main__':source_cases();search_cases();protocol_cases();phase_contract_cases();storage_cases()
