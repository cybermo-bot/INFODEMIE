import json
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from test_local_accounts import local,setup,login,create
from apps.api.db import Session,Record,add,update,now
from apps.api import automatic_tracking as auto,social_tracking as social

def owner(local):
    setup(local);social.cache.clear();social.attempts.clear();auto.discovery_cache.clear();return login(local)

def test_auto_selected_monitor_runs_without_browser_and_respects_due_pause(local,monkeypatch):
    h=owner(local)
    local.post('/api/v1/tracking/targets',headers=h,json={'url':'https://www.youtube.com/watch?v=abcdefghijk','purpose':'TEST ONLY automatic engagement','terms_accepted':True})
    calls=[]
    def fetch(targets):calls.append(targets);return [{'target_id':targets[0]['id'],'platform':'youtube','metrics':{'views':42},'observed_at':now()}]
    monkeypatch.setattr(social,'fetch_targets',fetch)
    assert auto.run_once()==1 and len(calls)==1
    status=local.get('/api/v1/tracking/status',headers=h).json();assert status['automatic']['enabled'] and status['observations'][0]['metrics']['views']==42
    assert auto.run_once()==0 and len(calls)==1
    assert local.put('/api/v1/tracking/automatic',headers=h,json={'enabled':False,'interval_minutes':10}).status_code==200
    assert auto.run_once()==0
    assert local.put('/api/v1/tracking/automatic',headers=h,json={'enabled':True,'interval_minutes':5}).status_code==200
    assert auto.run_once()==1

def test_discovery_error_backoff_retry_after_and_no_fabrication(local,monkeypatch):
    h=owner(local)
    result=local.post('/api/v1/tracking/watches',headers=h,json={'platform':'bluesky','query':'vaccination','purpose':'TEST ONLY authorised health watch','terms_accepted':True});assert result.status_code==201
    monkeypatch.setattr(auto,'discover',lambda w:(_ for _ in ()).throw(HTTPException(503,'Service denied request',headers={'Retry-After':'20000'})))
    assert auto.run_once()==1
    status=local.get('/api/v1/tracking/status',headers=h).json();assert status['discoveries']==[]
    watch=status['watches'][0];assert watch['state']=='error' and watch['error']=='Service denied request'
    assert watch['next_poll_at']>auto.later(300) and auto.run_once()==0
    assert local.put('/api/v1/tracking/automatic',headers=h,json={'enabled':True,'interval_minutes':1}).status_code==422

def test_owner_multilingual_scope_idempotency_roles_and_budget(local):
    h=owner(local);me=local.get('/api/v1/me',headers=h).json()
    with Session() as s:
        actor={'id':me['id'],'name':'TEST owner request','institution':me['institution']}
        assert auto.install_requested_scope(s,me['institution'],actor)['watches']==4
        assert auto.install_requested_scope(s,me['institution'],actor)['watches']==4
    status=local.get('/api/v1/tracking/status',headers=h).json();assert len(status['watches'])==4
    youtube=next(w for w in status['watches'] if w['platform']=='youtube')
    assert 'vaccination' in youtube['query'] and 'rougeole' in youtube['query'] and 'لقاح' in youtube['query'] and 'tla9i7' in youtube['query']
    assert 'terms_accepted_at' not in youtube # Never invents owner review of terms.
    create(local,h,'analyst');other=login(local,'analyst@example.test')
    assert local.put('/api/v1/tracking/automatic',headers=other,json={'enabled':False}).status_code==403
    assert local.delete('/api/v1/tracking/watches/'+youtube['id'],headers=other).status_code==403
    auto.reserve_search('youtube')
    with Session() as s:
        budget=s.scalar(select(Record).where(Record.kind=='tracking-budget'));update(s,budget,{'counts':{'youtube':80}},budget.version);s.commit()
    try:auto.reserve_search('youtube');assert False
    except HTTPException as exc:assert 'daily' in exc.detail

def test_official_mastodon_hashtag_discovery_dedup_public_only_transient(local,monkeypatch):
    owner(local);original=httpx.Client
    monkeypatch.setattr(social,'validate_url',lambda url:'mastodon.test')
    monkeypatch.setattr(auto,'reserve_search',lambda platform:None)
    def handler(request):
        assert request.url.host=='mastodon.test' and '/api/v1/timelines/tag/' in request.url.path
        return httpx.Response(200,json=[{'url':'https://mastodon.test/@user/123','visibility':'public','created_at':now(),'reblogs_count':2,'favourites_count':5,'replies_count':0,'content':'DO NOT STORE BODY','account':{'username':'DO NOT STORE AUTHOR'}},{'url':'https://mastodon.test/@user/999','visibility':'private','created_at':now(),'favourites_count':99}])
    monkeypatch.setattr(auto.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    result=auto.discover({'id':'TEST-watch','platform':'mastodon','query':'vaccination,measles','server':'https://mastodon.test'})
    assert len(result)==1 and result[0]['metrics']['likes']==5
    assert 'DO NOT STORE' not in json.dumps(result)
    assert auto.discover({'id':'TEST-watch','platform':'mastodon','query':'vaccination','server':'https://mastodon.test','language':'fr'})==[]
    with Session() as s:assert not s.scalar(select(Record).where(Record.kind=='content'))

def test_discoveries_expire_and_scoped_watch_delete(local,monkeypatch):
    h=owner(local);w=local.post('/api/v1/tracking/watches',headers=h,json={'platform':'bluesky','query':'measles','purpose':'TEST ONLY public health monitoring','terms_accepted':True}).json()
    monkeypatch.setattr(auto,'discover',lambda watch:[{'target_id':'TEST','watch_id':watch['id'],'metrics':{'likes':2}}])
    assert auto.run_once()==1
    assert len(local.get('/api/v1/tracking/status',headers=h).json()['discoveries'])==1
    auto.discovery_cache[w['id']]['at']-=auto.discovery_cache[w['id']]['ttl']+1
    assert local.get('/api/v1/tracking/status',headers=h).json()['discoveries']==[]
    with Session() as s:
        other=add(s,'tracking-watches','other-institution',{'platform':'bluesky','query':'TEST','language':''});s.commit();other_id=other.id
    assert local.delete('/api/v1/tracking/watches/'+other_id,headers=h).status_code==404
    assert local.delete('/api/v1/tracking/watches/'+w['id'],headers=h).status_code==200

def test_new_credentials_wake_waiting_watch_without_restart(local,monkeypatch):
    h=owner(local)
    local.post('/api/v1/tracking/watches',headers=h,json={'platform':'youtube','query':'vaccination','purpose':'TEST ONLY authorised watch','terms_accepted':True})
    monkeypatch.setattr(social,'youtube_key',lambda:'')
    monkeypatch.setattr(auto,'discover',lambda w:(_ for _ in ()).throw(HTTPException(503,'YouTube discovery is waiting for your API key.')))
    assert auto.run_once()==1
    watch=local.get('/api/v1/tracking/status',headers=h).json()['watches'][0];assert watch['state']=='waiting_for_credentials' and watch['next_poll_at']>now()
    monkeypatch.setattr(social,'youtube_key',lambda:'TEST-KEY')
    monkeypatch.setattr(auto,'discover',lambda w:[])
    assert auto.run_once()==1
    assert local.get('/api/v1/tracking/status',headers=h).json()['watches'][0]['state']=='observed'

def test_official_keyword_search_routes_and_safe_normalization(local,monkeypatch):
    owner(local);original=httpx.Client;calls=[]
    monkeypatch.setattr(social,'youtube_key',lambda:'TEST-KEY')
    monkeypatch.setattr(social,'x_token',lambda:'TEST-TOKEN')
    monkeypatch.setattr(auto,'reserve_search',lambda platform:None)
    def handler(request):
        calls.append(request)
        if request.url.host=='www.googleapis.com':
            assert request.url.path=='/youtube/v3/search' and request.url.params['type']=='video'
            return httpx.Response(200,json={'items':[{'id':{'videoId':'abcdefghijk'}}]})
        if request.url.host=='api.x.com':
            assert request.url.path=='/2/tweets/search/recent' and request.headers['authorization']=='Bearer TEST-TOKEN'
            return httpx.Response(200,json={'data':[{'id':'123456','text':'DO NOT STORE'}]})
        assert request.url.host=='public.api.bsky.app' and request.url.path.endswith('searchPosts')
        return httpx.Response(200,json={'posts':[{'uri':'at://did:plc:test/app.bsky.feed.post/abc123','record':{'text':'DO NOT STORE'}}]})
    monkeypatch.setattr(auto.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    targets=[]
    def fetch(selected):targets.extend(selected);return [{'target_id':t['id'],'platform':t['platform'],'source_url':t['url'],'metrics':{'likes':1}} for t in selected]
    monkeypatch.setattr(social,'fetch_targets',fetch)
    for platform in ('youtube','x','bluesky'):
        result=auto.discover({'id':'TEST-'+platform,'platform':platform,'query':'vaccination','language':''})
        assert len(result)==1 and result[0]['discovered']
        assert 'DO NOT STORE' not in json.dumps(result) and 'TEST-KEY' not in json.dumps(result)
    assert len(calls)==3 and {t['platform'] for t in targets}=={'youtube','x','bluesky'}
