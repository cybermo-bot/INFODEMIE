"""Official read-only APIs. Only user-selected URLs persist; API data stays in memory."""
import os,re,json,time,threading
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import httpx
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
from .db import add,audit,now
from .connectors import validate_url

cache={}
attempts={}
lock=threading.Lock()

def youtube_key():
    key=os.getenv('YOUTUBE_API_KEY','').strip()
    if key:return key
    try:
        value=json.loads((Path(__file__).resolve().parents[2]/'data'/'social-credentials.json').read_text(encoding='utf-8'))
        return value.get('youtube_api_key','').strip() if isinstance(value,dict) and isinstance(value.get('youtube_api_key',''),str) else ''
    except (OSError,ValueError):return ''

def x_token():
    value=os.getenv('X_BEARER_TOKEN','').strip()
    if value:return value
    try:
        credentials=json.loads((Path(__file__).resolve().parents[2]/'data'/'social-credentials.json').read_text(encoding='utf-8'))
        token=credentials.get('x_bearer_token','') if isinstance(credentials,dict) else ''
        return token.strip() if isinstance(token,str) else ''
    except (OSError,ValueError):return ''

def target_url(value):
    try:p=urlparse(value);port=p.port
    except ValueError:raise HTTPException(422,'Invalid publication URL.')
    if p.scheme!='https' or p.username or p.password or port not in (None,443):raise HTTPException(422,'Use an original public HTTPS YouTube, Bluesky or Mastodon post link.')
    if p.hostname in ('youtube.com','www.youtube.com','m.youtube.com','youtu.be'):
        video=p.path.strip('/') if p.hostname=='youtu.be' else (parse_qs(p.query).get('v',[''])[0] if p.path=='/watch' else p.path.split('/')[-1] if p.path.startswith(('/shorts/','/live/')) else '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video):raise HTTPException(422,'A specific YouTube video URL is required.')
        return 'youtube',video,'https://www.youtube.com/watch?v='+video
    if p.hostname=='bsky.app':
        match=re.fullmatch(r'/profile/([A-Za-z0-9.:%_-]+)/post/([A-Za-z0-9]+)',p.path)
        if match:return 'bluesky',match.group(1)+'/'+match.group(2),'https://bsky.app'+p.path
    if p.hostname in ('x.com','www.x.com','twitter.com','www.twitter.com'):
        match=re.fullmatch(r'/[A-Za-z0-9_]+/status/([0-9]{1,25})',p.path)
        if match:return 'x',match.group(1),'https://x.com'+p.path
    match=re.fullmatch(r'/(?:@[A-Za-z0-9_.-]+/|users/[A-Za-z0-9_.-]+/statuses/)([0-9]{1,30})',p.path)
    if match:
        validate_url(value)
        return 'mastodon',match.group(1),'https://'+p.hostname+p.path
    raise HTTPException(422,'Supported now: individual YouTube videos, X posts, Bluesky posts and public Mastodon statuses. Other integrations require a dedicated adapter.')

def official_get(client,url,params,headers=None,expect_array=False):
    try:
        with client.stream('GET',url,params=params,headers={'User-Agent':'PNSI-OfficialAPI/0.1',**(headers or {})}) as response:
            if response.status_code!=200:
                code=response.status_code
                retry=response.headers.get('Retry-After','')
                if not retry.isdigit():
                    try:
                        from email.utils import parsedate_to_datetime
                        from datetime import datetime,timezone
                        retry=str(max(0,int((parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())))
                    except (ValueError,TypeError,OverflowError):retry='0'
                retry=str(min(int(retry),86400))
                raise HTTPException(503,f'Official API returned HTTP {code}. Check access, quota and service availability; no alternate scraping endpoint is used.',headers={'Retry-After':retry})
            chunks=[];size=0
            for chunk in response.iter_bytes():
                size+=len(chunk)
                if size>1_000_000:raise HTTPException(503,'Official API response exceeds the local size limit.')
                chunks.append(chunk)
        parsed=json.loads(b''.join(chunks))
        if not isinstance(parsed,list if expect_array else dict):raise HTTPException(503,'Official API returned an invalid response.')
        return parsed
    except HTTPException:raise
    except (httpx.HTTPError,ValueError):raise HTTPException(503,'Official API connection unavailable. Credentials and response bodies are not logged.')

def count(value):
    # Missing and malformed measurements stay unknown, never zero.
    if isinstance(value,bool):return None
    if isinstance(value,int) and value>=0:return value
    if isinstance(value,str) and value.isdigit() and len(value)<=20:return int(value)
    return None

def fetch_targets(targets):
    results=[]
    with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
        yt=[t for t in targets if t['platform']=='youtube']
        if yt:
            key=youtube_key()
            if not key:raise HTTPException(503,'YouTube is disconnected: configure youtube_api_key in data/social-credentials.json on this PC.')
            data=official_get(client,'https://www.googleapis.com/youtube/v3/videos',{'part':'snippet,statistics,status','id':','.join(t['platform_id'] for t in yt),'key':key})
            by_id={v['id']:v for v in data.get('items',[]) if v.get('status',{}).get('privacyStatus')=='public'}
            for t in yt:
                v=by_id.get(t['platform_id']);stats=(v or {}).get('statistics',{})
                results.append({'target_id':t['id'],'platform':'youtube','source_url':t['url'],'state':'observed' if v else 'unavailable','title':(v or {}).get('snippet',{}).get('title'),'metrics':{k:count(stats.get(field)) for k,field in [('views','viewCount'),('likes','likeCount'),('comments','commentCount')]},'observed_at':now(),'provenance':'YouTube Data API v3 · videos.list'})
        for t in [t for t in targets if t['platform']=='bluesky']:
            actor,rkey=t['platform_id'].rsplit('/',1)
            if not actor.startswith('did:'):
                actor=official_get(client,'https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle',{'handle':actor}).get('did','')
            if not re.fullmatch(r'did:[A-Za-z0-9:._%-]+',actor):raise HTTPException(503,'Bluesky identity could not be resolved.')
            data=official_get(client,'https://public.api.bsky.app/xrpc/app.bsky.feed.getPosts',{'uris':'at://'+actor+'/app.bsky.feed.post/'+rkey})
            posts=data.get('posts',[]);p=posts[0] if posts else None
            # Do not copy authors, handles, full post text or media into the database.
            results.append({'target_id':t['id'],'platform':'bluesky','source_url':t['url'],'state':'observed' if p else 'unavailable','title':None,'metrics':{k:count((p or {}).get(field)) for k,field in [('likes','likeCount'),('reposts','repostCount'),('replies','replyCount'),('quotes','quoteCount')]},'observed_at':now(),'provenance':'Bluesky public AppView · getPosts'})
        for t in [t for t in targets if t['platform']=='mastodon']:
            host=validate_url(t['url'])
            try:credentials=json.loads((Path(__file__).resolve().parents[2]/'data'/'social-credentials.json').read_text(encoding='utf-8'))
            except (OSError,ValueError):credentials={}
            tokens=credentials.get('mastodon_tokens',{}) if isinstance(credentials,dict) else {}
            token=tokens.get(host,'') if isinstance(tokens,dict) else ''
            if not isinstance(token,str):token=''
            data=official_get(client,'https://'+host+'/api/v1/statuses/'+t['platform_id'],{}, {'Authorization':'Bearer '+token} if token else None)
            public=data.get('visibility')=='public'
            results.append({'target_id':t['id'],'platform':'mastodon','source_url':t['url'],'state':'observed' if public else 'unavailable','title':None,'metrics':{k:count(data.get(field)) if public else None for k,field in [('likes','favourites_count'),('reposts','reblogs_count'),('replies','replies_count'),('quotes','quotes_count')]},'observed_at':now(),'provenance':'Mastodon official status API · server '+host})
        xt=[t for t in targets if t['platform']=='x']
        if xt:
            token=x_token()
            if not token:raise HTTPException(503,'X is disconnected: configure x_bearer_token in data/social-credentials.json with approved API access.')
            data=official_get(client,'https://api.x.com/2/tweets',{'ids':','.join(t['platform_id'] for t in xt),'tweet.fields':'public_metrics'},{'Authorization':'Bearer '+token})
            by_id={v['id']:v for v in data.get('data',[])}
            for t in xt:
                p=by_id.get(t['platform_id']);metrics=(p or {}).get('public_metrics',{})
                results.append({'target_id':t['id'],'platform':'x','source_url':t['url'],'state':'observed' if p else 'unavailable','title':None,'metrics':{k:count(metrics.get(field)) for k,field in [('likes','like_count'),('reposts','retweet_count'),('replies','reply_count'),('quotes','quote_count'),('impressions','impression_count')]},'observed_at':now(),'provenance':'X official API v2 · post lookup'})
    return results

class Target(BaseModel):
    url:str=Field(min_length=10,max_length=500)
    purpose:str=Field(min_length=10,max_length=300)
    terms_accepted:bool

def register(app,current,db,require,rows,get,env):
    def local_only():
        if env()!='local':raise HTTPException(403,'Social tracking is available in the separate local installation.')

    @app.get('/api/v1/tracking/status')
    def status(user=Depends(current),s=Depends(db)):
        from .automatic_tracking import automatic_status
        local_only();targets=[r.data() for r in rows(s,'tracking-targets',user)]
        for institution,saved in list(cache.items()):
            if time.monotonic()-saved['at']>=900:cache.pop(institution,None)
        saved=cache.get(user['institution']);fresh=saved and time.monotonic()-saved['at']<900
        target_ids={t['id'] for t in targets}
        return {**automatic_status(s,user),'targets':targets,'youtube_configured':bool(youtube_key()),'x_configured':bool(x_token()),'observations':[o for o in saved['items'] if o['target_id'] in target_ids] if fresh else [],'errors':saved.get('errors',[]) if fresh else [],'state':('partial' if saved.get('errors') else 'observed') if fresh else 'not_observed','can_configure':user['role']=='administrator','can_refresh':user['role'] in ('administrator','operator','analyst'),'retention':'Selected-post API observations expire after 15 minutes; automatic search observations expire after their polling interval plus 15 minutes (maximum 135 minutes). No API observations are persisted; restarting clears process memory. Selected URLs and purpose persist until removed. No historical engagement, reach estimates or cross-platform totals.','unimplemented':['Facebook / Instagram','TikTok','Reddit','Telegram']}

    @app.post('/api/v1/tracking/targets',status_code=201)
    def create(body:Target,user=Depends(current),s=Depends(db)):
        local_only();require(user,'administrator')
        if not body.terms_accepted:raise HTTPException(422,'Review and accept the source terms and document your monitoring purpose.')
        platform,pid,url=target_url(body.url)
        existing=rows(s,'tracking-targets',user)
        prior=next((t for t in existing if t.data()['url']==url),None)
        if prior:return prior.data()
        if len(existing)>=20:raise HTTPException(422,'Local monitoring is limited to 20 selected posts/videos.')
        target=add(s,'tracking-targets',user['institution'],{'platform':platform,'platform_id':pid,'url':url,'purpose':body.purpose,'terms_accepted_at':now(),'configured_by':user['id'],'synthetic':False})
        audit(s,user,target,'tracking.target_added');s.commit();cache.pop(user['institution'],None);return target.data()

    @app.delete('/api/v1/tracking/targets/{id}')
    def remove(id:str,user=Depends(current),s=Depends(db)):
        local_only();require(user,'administrator');target=get(s,'tracking-targets',id,user)
        # Remove URL/purpose from record history and audit as well as the active target.
        from .db import RecordVersion,Event
        from sqlalchemy import delete
        s.execute(delete(RecordVersion).where(RecordVersion.entity_id==target.id))
        s.execute(delete(Event).where(Event.entity_id==target.id))
        s.delete(target);s.commit();cache.pop(user['institution'],None);return {'removed':True,'backup_notice':'Existing offline backups are not rewritten; restore must reapply removals before monitoring.'}

    @app.post('/api/v1/tracking/refresh')
    def refresh(user=Depends(current),s=Depends(db)):
        local_only();require(user,'administrator','operator','analyst');targets=[r.data() for r in rows(s,'tracking-targets',user)]
        if not targets:raise HTTPException(422,'Select public posts/videos before requesting observations.')
        with lock:
            t=time.monotonic()
            if t-attempts.get(user['institution'],-1000)<60:raise HTTPException(429,'Wait one minute before another API request.',headers={'Retry-After':'60'})
            attempts[user['institution']]=t
        # A failed refresh clears previous data, so the interface cannot display stale success.
        cache.pop(user['institution'],None)
        observations=[];errors=[]
        for platform in ('youtube','bluesky','mastodon','x'):
            selected=[t for t in targets if t['platform']==platform]
            if not selected:continue
            try:observations.extend(fetch_targets(selected))
            except HTTPException as exc:errors.append({'platform':platform,'message':exc.detail})
        cache[user['institution']]={'at':time.monotonic(),'items':observations,'errors':errors}
        cached=cache[user['institution']]
        def expire():
            if cache.get(user['institution']) is cached:cache.pop(user['institution'],None)
        timer=threading.Timer(900,expire);timer.daemon=True;timer.start()
        return {'observations':observations,'errors':errors,'state':'partial' if errors else 'observed','checked_at':now()}
