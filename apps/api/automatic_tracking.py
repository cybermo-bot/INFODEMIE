"""Local background monitoring and bounded keyword discovery through official APIs."""
import hashlib,time,threading,re,json
from pathlib import Path
from urllib.parse import quote
from datetime import datetime,timedelta,timezone
from typing import Literal
import httpx
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from .db import Session,Record,add,update,audit,now
from . import social_tracking as social
from .connectors import safe_article_url,publication_date

discovery_cache={}
cycle_lock=threading.Lock()
budget_lock=threading.Lock()
runner={'last_tick_at':None,'state':'not_started'}

def install_requested_scope(s,institution,actor):
    """Owner-requested public monitoring; never impersonates a terms acceptance."""
    words=['vaccination','measles','rougeole','health','remède','تلقيح','لقاح','الحصبة','صحة','tla9i7','s7a']
    existing=list(s.scalars(select(Record).where(Record.kind=='tracking-watches',Record.institution==institution)))
    for platform in ('youtube','bluesky','x','mastodon'):
        query='vaccination,measles,rougeole,لقاح,tla9i7,s7a' if platform=='mastodon' else (' | ' if platform=='youtube' else ' OR ').join(words)
        if any(r.data().get('preset')=='health-four-languages' and r.data()['platform']==platform for r in existing):continue
        if len(existing)>=4:break
        record=add(s,'tracking-watches',institution,{'platform':platform,'query':query,'server':'https://mastodon.social' if platform=='mastodon' else None,'interval_minutes':120 if platform=='mastodon' else 60,'language':'','purpose':'Owner requested public health monitoring: vaccination, measles and health claims; French, English, Arabic and Derja/Arabizi keywords. Geography unknown.','enabled':True,'next_poll_at':now(),'state':'scheduled','preset':'health-four-languages','configured_by':actor.get('id'),'authorization_basis':'Explicit owner request for local public API monitoring. Platform approval/terms remain required for account credentials; no fabricated terms acceptance.','synthetic':False})
        audit(s,actor,record,'tracking.owner_scope_configured');existing.append(record)
    record,config=settings(s,institution)
    values={'enabled':True,'interval_minutes':10,'next_poll_at':now(),'state':'scheduled'}
    if record:update(s,record,values,record.version)
    else:record=add(s,'tracking-settings',institution,values)
    audit(s,actor,record,'tracking.owner_automatic_enabled');s.commit()
    return {'watches':len(existing),'enabled':True}

def later(minutes):return (datetime.now(timezone.utc)+timedelta(minutes=minutes)).isoformat()
def settings(s,institution):
    r=next(iter(s.scalars(select(Record).where(Record.kind=='tracking-settings',Record.institution==institution))),None)
    return r, r.data() if r else {'enabled':True,'interval_minutes':10,'state':'waiting_for_scope','next_poll_at':None}

def put_cache(institution,items,errors):
    social.cache[institution]={'at':time.monotonic(),'items':items,'errors':errors}
    saved=social.cache[institution]
    def expire():
        if social.cache.get(institution) is saved:social.cache.pop(institution,None)
    timer=threading.Timer(900,expire);timer.daemon=True;timer.start()

def reserve_search(platform):
    # Global local-installation ceiling, independent of provider entitlement.
    with budget_lock,Session() as s:
        day=datetime.now(timezone.utc).date().isoformat()
        r=next(iter(s.scalars(select(Record).where(Record.kind=='tracking-budget',Record.institution=='system'))),None)
        counts=r.data().get('counts',{}) if r and r.data().get('day')==day else {}
        if counts.get(platform,0)>=80:raise HTTPException(503,'Local daily search ceiling reached; discovery resumes tomorrow. Provider quotas may be lower.')
        counts[platform]=counts.get(platform,0)+1
        if r:update(s,r,{'day':day,'counts':counts},r.version)
        else:add(s,'tracking-budget','system',{'day':day,'counts':counts})
        s.commit()

def discover(watch):
    platform=watch['platform'];q=watch['query'];targets=[]
    if platform=='youtube' and not social.youtube_key():raise HTTPException(503,'YouTube discovery is waiting for your API key.')
    if platform=='x' and not social.x_token():raise HTTPException(503,'X discovery is waiting for approved recent-search API access and your token.')
    if platform!='mastodon':reserve_search(platform)
    with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
        if platform=='mastodon':
            server=watch.get('server','https://mastodon.social').rstrip('/');host=social.validate_url(server)
            try:credentials=json.loads((Path(__file__).resolve().parents[2]/'data'/'social-credentials.json').read_text(encoding='utf-8'))
            except (OSError,ValueError):credentials={}
            tokens=credentials.get('mastodon_tokens',{}) if isinstance(credentials,dict) else {};token=tokens.get(host,'') if isinstance(tokens,dict) else ''
            headers={'Authorization':'Bearer '+token} if isinstance(token,str) and token else None
            found={};cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
            for tag in watch['query'].split(',')[:6]:
                tag=tag.strip().lstrip('#')
                if not re.fullmatch(r'\w{1,30}',tag):raise HTTPException(422,'Mastodon discovery requires up to six comma-separated hashtags.')
                reserve_search(platform)
                posts=social.official_get(client,server+'/api/v1/timelines/tag/'+quote(tag,safe=''),{'limit':10},headers,expect_array=True)
                for p in posts:
                    link=safe_article_url(p.get('url',''));published=publication_date(p.get('created_at',''))
                    if p.get('visibility')!='public' or not link or not published or not cutoff<=published<=now():continue
                    if watch.get('language') and p.get('language')!=watch['language']:continue
                    found[link]={'target_id':hashlib.sha256(link.encode()).hexdigest()[:24],'watch_id':watch['id'],'query':q,'discovered':True,'platform':'mastodon','source_url':link,'state':'observed','title':None,'published_at':published,'observed_at':now(),'provenance':'Mastodon public hashtag timeline · '+host,'metrics':{k:social.count(p.get(field)) for k,field in [('likes','favourites_count'),('reposts','reblogs_count'),('replies','replies_count'),('quotes','quotes_count')]}}
            return sorted(found.values(),key=lambda p:p['published_at'],reverse=True)[:10]
        elif platform=='youtube':
            params={'part':'snippet','type':'video','order':'date','maxResults':10,'q':q,'key':social.youtube_key(),'publishedAfter':(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()}
            if watch.get('language'):params['relevanceLanguage']=watch['language']
            data=social.official_get(client,'https://www.googleapis.com/youtube/v3/search',params)
            urls=['https://www.youtube.com/watch?v='+item.get('id',{}).get('videoId','') for item in data.get('items',[])]
        elif platform=='x':
            query=q+(' lang:'+watch['language'] if watch.get('language') else '')
            data=social.official_get(client,'https://api.x.com/2/tweets/search/recent',{'query':query,'max_results':10,'tweet.fields':'public_metrics'},{'Authorization':'Bearer '+social.x_token()})
            urls=['https://x.com/i/status/'+item.get('id','') for item in data.get('data',[])]
        else:
            params={'q':q,'sort':'latest','limit':10,'since':(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()}
            if watch.get('language'):params['lang']=watch['language']
            data=social.official_get(client,'https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts',params)
            urls=[]
            for item in data.get('posts',[]):
                uri=item.get('uri','')
                if uri.startswith('at://') and '/app.bsky.feed.post/' in uri:
                    actor,rkey=uri.removeprefix('at://').split('/app.bsky.feed.post/',1)
                    urls.append('https://bsky.app/profile/'+actor+'/post/'+rkey)
    for url in dict.fromkeys(urls[:10]):
        try:p,pid,canonical=social.target_url(url)
        except HTTPException:continue
        targets.append({'id':hashlib.sha256(canonical.encode()).hexdigest()[:24],'platform':p,'platform_id':pid,'url':canonical})
    observations=social.fetch_targets(targets) if targets else []
    for o in observations:o.update(watch_id=watch['id'],query=q,discovered=True)
    return observations

def automatic_status(s,user):
    _,config=settings(s,user['institution'])
    watches=[r.data() for r in s.scalars(select(Record).where(Record.kind=='tracking-watches',Record.institution==user['institution']))]
    current=[]
    for key,saved in list(discovery_cache.items()):
        if time.monotonic()-saved['at']>=saved.get('ttl',900):discovery_cache.pop(key,None)
    for w in watches:
        saved=discovery_cache.get(w['id'])
        if saved:current.extend(saved['items'])
    return {'automatic':{**config,'runner':dict(runner)},'watches':watches,'discoveries':current}

def run_once():
    if not cycle_lock.acquire(blocking=False):return 0
    completed=0
    try:
        with Session() as s:
            institutions={r.institution for r in s.scalars(select(Record).where(Record.kind.in_(['tracking-targets','tracking-watches','tracking-settings'])))}
        for institution in institutions:
            with Session() as s:
                config_record,config=settings(s,institution)
                if not config.get('enabled'):continue
                targets=[r.data() for r in s.scalars(select(Record).where(Record.kind=='tracking-targets',Record.institution==institution))]
                watches=[r.data() for r in s.scalars(select(Record).where(Record.kind=='tracking-watches',Record.institution==institution))]
                if not targets and not watches:continue
                if not config_record:
                    config_record=add(s,'tracking-settings',institution,{**config,'next_poll_at':now()});s.commit();config=config_record.data()
                due_targets=targets and (not config.get('next_poll_at') or config['next_poll_at']<=now())
                due_watches=[w for w in watches if w.get('enabled',True) and (w.get('next_poll_at',now())<=now() or (w.get('state')=='waiting_for_credentials' and ((w['platform']=='youtube' and social.youtube_key()) or (w['platform']=='x' and social.x_token()))))]
                if not due_targets and not due_watches:continue
                if due_targets:update(s,config_record,{'state':'running','next_poll_at':later(config['interval_minutes'])},config_record.version)
                for w in due_watches:
                    record=s.get(Record,w['id']);update(s,record,{'state':'running','next_poll_at':later(w.get('interval_minutes',60))},record.version)
                s.commit()
            if due_targets:
                items=[];errors=[];retry_minutes=0
                for platform in ('youtube','bluesky','mastodon','x'):
                    selected=[t for t in targets if t['platform']==platform]
                    if not selected:continue
                    try:items.extend(social.fetch_targets(selected))
                    except HTTPException as exc:
                        errors.append({'platform':platform,'message':exc.detail})
                        retry_minutes=max(retry_minutes,int((exc.headers or {}).get('Retry-After','0'))/60)
                    except Exception:errors.append({'platform':platform,'message':'Source response unavailable or invalid; no data fabricated.'})
                with Session() as s:
                    record,current=settings(s,institution)
                    if current.get('enabled'):
                        existing={r.id for r in s.scalars(select(Record).where(Record.kind=='tracking-targets',Record.institution==institution))}
                        put_cache(institution,[o for o in items if o['target_id'] in existing],errors)
                        failures=current.get('failure_count',0)+1 if errors else 0
                        wait=max(retry_minutes,min(config['interval_minutes']*2**min(failures,5),360))
                        update(s,record,{'state':'partial' if errors else 'observed','last_attempt_at':now(),'last_success_at':now() if not errors else current.get('last_success_at'),'failure_count':failures,'next_poll_at':later(wait),'errors':errors},record.version);s.commit()
                completed+=1
            for w in due_watches:
                error=None;items=[];retry_minutes=0
                try:items=discover(w)
                except HTTPException as exc:
                    error=str(exc.detail);retry_minutes=int((exc.headers or {}).get('Retry-After','0'))/60
                except Exception:error='Source response unavailable or invalid; no data fabricated.'
                with Session() as s:
                    record=s.get(Record,w['id']);_,current=settings(s,institution)
                    if not record or not current.get('enabled'):continue
                    if error:discovery_cache.pop(w['id'],None)
                    else:
                        ttl=w.get('interval_minutes',60)*60+900
                        discovery_cache[w['id']]={'at':time.monotonic(),'items':items,'ttl':ttl}
                        saved=discovery_cache[w['id']]
                        def expire(key=w['id'],value=saved):
                            if discovery_cache.get(key) is value:discovery_cache.pop(key,None)
                        timer=threading.Timer(ttl,expire);timer.daemon=True;timer.start()
                    failures=record.data().get('failure_count',0)+1 if error else 0
                    state='waiting_for_credentials' if error and 'waiting for' in error else 'error' if error else 'observed'
                    update(s,record,{'state':state,'error':error,'last_attempt_at':now(),'failure_count':failures,'next_poll_at':later(max(retry_minutes,min(w.get('interval_minutes',60)*2**min(failures,3),480)))},record.version);s.commit()
                completed+=1
        return completed
    finally:cycle_lock.release()

def loop(stop):
    runner['state']='running'
    with Session() as s:
        for r in s.scalars(select(Record).where(Record.kind.in_(['tracking-settings','tracking-watches']))):
            if r.data().get('state') in ('running','observed'):update(s,r,{'state':'scheduled','next_poll_at':now()},r.version)
        s.commit()
    while not stop.is_set():
        runner['last_tick_at']=now()
        try:run_once();runner['state']='running'
        except Exception:runner['state']='error' # No request or credential details are leaked.
        stop.wait(30)
    runner['state']='stopped'

class AutoConfig(BaseModel):
    enabled:bool
    interval_minutes:Literal[5,10,15,30,60]=10
class Watch(BaseModel):
    platform:Literal['youtube','bluesky','x','mastodon']
    query:str=Field(min_length=2,max_length=150)
    language:Literal['','en','fr','ar']=''
    purpose:str=Field(min_length=10,max_length=300)
    terms_accepted:bool
    server:str=Field(default='https://mastodon.social',max_length=200)

def register(app,current,db,require,rows,get,env):
    def local_only():
        if env()!='local':raise HTTPException(403,'Automatic social monitoring is local only.')
    @app.put('/api/v1/tracking/automatic')
    def configure(body:AutoConfig,user=Depends(current),s=Depends(db)):
        local_only();require(user,'administrator');record,_=settings(s,user['institution'])
        values={'enabled':body.enabled,'interval_minutes':body.interval_minutes,'next_poll_at':now(),'state':'scheduled' if body.enabled else 'paused'}
        if record:update(s,record,values,record.version)
        else:record=add(s,'tracking-settings',user['institution'],values)
        audit(s,user,record,'tracking.automatic_configured');s.commit();return record.data()
    @app.post('/api/v1/tracking/watches',status_code=201)
    def watch(body:Watch,user=Depends(current),s=Depends(db)):
        local_only();require(user,'administrator')
        if not body.terms_accepted:raise HTTPException(422,'Review source terms and document the discovery purpose.')
        query=body.query.strip()
        if len(query)<2:raise HTTPException(422,'Enter a meaningful topic query.')
        existing=rows(s,'tracking-watches',user)
        prior=next((r for r in existing if r.data()['platform']==body.platform and r.data()['query']==query and r.data()['language']==body.language and (body.platform!='mastodon' or r.data().get('server','https://mastodon.social').rstrip('/')==body.server.rstrip('/'))),None)
        if prior:return prior.data()
        if len(existing)>=4:raise HTTPException(422,'At most four automatic topic searches are supported locally.')
        if body.platform=='mastodon':
            from urllib.parse import urlparse
            social.validate_url(body.server)
            if urlparse(body.server).path not in ('','/') or urlparse(body.server).query:raise HTTPException(422,'Use the Mastodon server root URL.')
            if len(query.split(','))>6 or any(not re.fullmatch(r'\w{1,30}',tag.strip().lstrip('#')) for tag in query.split(',')):raise HTTPException(422,'Use up to six comma-separated hashtags.')
        record=add(s,'tracking-watches',user['institution'],{**body.model_dump(exclude={'terms_accepted'}),'query':query,'interval_minutes':120 if body.platform=='mastodon' else 60,'enabled':True,'next_poll_at':now(),'state':'scheduled','configured_by':user['id'],'terms_accepted_at':now(),'synthetic':False})
        audit(s,user,record,'tracking.watch_created');s.commit();return record.data()
    @app.delete('/api/v1/tracking/watches/{id}')
    def remove(id:str,user=Depends(current),s=Depends(db)):
        local_only();require(user,'administrator');record=get(s,'tracking-watches',id,user)
        from .db import RecordVersion,Event
        from sqlalchemy import delete
        s.execute(delete(RecordVersion).where(RecordVersion.entity_id==id));s.execute(delete(Event).where(Event.entity_id==id));s.delete(record);s.commit();discovery_cache.pop(id,None);return {'removed':True,'backup_notice':'Existing offline backups require separate removal handling.'}
