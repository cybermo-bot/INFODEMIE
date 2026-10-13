import json
import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from test_local_accounts import local,setup,login,create
from apps.api import social_tracking as tracking
from apps.api.db import Session,Record,RecordVersion,Event

URL='https://www.youtube.com/watch?v=abcdefghijk'

def account(local):
    setup(local);tracking.cache.clear();tracking.attempts.clear();return login(local)

def target(local,h,url=URL):
    response=local.post('/api/v1/tracking/targets',headers=h,json={'url':url,'purpose':'TEST ONLY: authorised public engagement monitoring','terms_accepted':True})
    assert response.status_code==201,response.text
    return response.json()

def test_target_validation_idempotency_and_no_generic_write(local):
    h=account(local);first=target(local,h);assert target(local,h)['id']==first['id']
    assert local.get('/api/v1/tracking/status',headers=h).json()['observations']==[]
    for url in ('http://www.youtube.com/watch?v=abcdefghijk','https://youtube.com.evil.test/watch?v=abcdefghijk','https://127.0.0.1/watch?v=abcdefghijk','https://www.youtube.com/channel/test'):
        with pytest.raises(HTTPException):tracking.target_url(url)
    assert local.post('/api/v1/tracking/targets',headers=h,json={'url':URL,'purpose':'Monitoring purpose','terms_accepted':False}).status_code==422
    assert local.post('/api/v1/tracking-targets',headers=h,json={'data':{'url':URL}}).status_code==403

def test_missing_key_and_expiry_never_invent_metrics(local,monkeypatch):
    h=account(local);target(local,h);monkeypatch.setattr(tracking,'youtube_key',lambda:'')
    response=local.post('/api/v1/tracking/refresh',headers=h)
    assert response.status_code==200
    assert response.json()['observations']==[] and response.json()['state']=='partial'
    assert 'disconnected' in response.json()['errors'][0]['message']
    assert local.post('/api/v1/tracking/refresh',headers=h).status_code==429
    tracking.cache[next(iter(tracking.cache))]['at']-=901
    assert local.get('/api/v1/tracking/status',headers=h).json()['observations']==[]
    assert not tracking.cache

def test_official_youtube_public_metrics_unknown_and_secret_sanitization(monkeypatch):
    original=httpx.Client
    def handler(request):
        assert request.url.host=='www.googleapis.com'
        return httpx.Response(200,json={'items':[{'id':'abcdefghijk','status':{'privacyStatus':'public'},'snippet':{'title':'TEST ONLY'},'statistics':{'viewCount':'42','commentCount':'0'}}]})
    monkeypatch.setattr(tracking,'youtube_key',lambda:'TEST-SECRET-NEVER-PRINT')
    monkeypatch.setattr(tracking.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    result=tracking.fetch_targets([{'id':'target','platform':'youtube','platform_id':'abcdefghijk','url':URL}])
    assert result[0]['metrics']=={'views':42,'likes':None,'comments':0}
    assert 'TEST-SECRET' not in json.dumps(result)
    def failure(request):return httpx.Response(403,json={'error':'TEST-SECRET-NEVER-PRINT'})
    monkeypatch.setattr(tracking.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(failure),**kwargs))
    with pytest.raises(HTTPException) as error:tracking.fetch_targets([{'id':'target','platform':'youtube','platform_id':'abcdefghijk','url':URL}])
    assert 'TEST-SECRET' not in str(error.value.detail)

def test_bluesky_official_uri_metrics_without_content_storage(monkeypatch):
    original=httpx.Client
    def handler(request):
        assert request.url.host=='public.api.bsky.app'
        if request.url.path.endswith('resolveHandle'):return httpx.Response(200,json={'did':'did:plc:test'})
        assert request.url.params['uris']=='at://did:plc:test/app.bsky.feed.post/abc123'
        return httpx.Response(200,json={'posts':[{'record':{'text':'DO NOT STORE FULL CONTENT'},'author':{'handle':'DO NOT STORE AUTHOR'},'likeCount':3,'repostCount':2,'replyCount':0}]})
    monkeypatch.setattr(tracking.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    result=tracking.fetch_targets([{'id':'target','platform':'bluesky','platform_id':'example.test/abc123','url':'https://bsky.app/profile/example.test/post/abc123'}])
    assert result[0]['metrics']=={'likes':3,'reposts':2,'replies':0,'quotes':None}
    assert 'DO NOT STORE' not in json.dumps(result)

def test_role_gate_and_full_target_removal(local):
    h=account(local);t=target(local,h);create(local,h,'analyst');analyst=login(local,'analyst@example.test')
    assert local.delete('/api/v1/tracking/targets/'+t['id'],headers=analyst).status_code==403
    assert local.post('/api/v1/tracking/targets',headers=analyst,json={'url':URL,'purpose':'Authorised monitoring','terms_accepted':True}).status_code==403
    assert local.delete('/api/v1/tracking/targets/'+t['id'],headers=h).status_code==200
    with Session() as s:
        assert s.get(Record,t['id']) is None
        assert not s.scalar(select(RecordVersion).where(RecordVersion.entity_id==t['id']))
        assert not s.scalar(select(Event).where(Event.entity_id==t['id']))

def test_mastodon_public_metrics_private_rejection_and_host_validation(monkeypatch):
    original=httpx.Client
    monkeypatch.setattr(tracking,'validate_url',lambda value:'public-mastodon.example')
    def handler(request):
        assert request.url.host=='public-mastodon.example' and request.url.path=='/api/v1/statuses/123'
        return httpx.Response(200,json={'visibility':'public','reblogs_count':2,'replies_count':0,'favourites_count':7,'content':'DO NOT STORE'})
    monkeypatch.setattr(tracking.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    t={'id':'target','platform':'mastodon','platform_id':'123','url':'https://public-mastodon.example/@user/123'}
    assert tracking.target_url(t['url'])[:2]==('mastodon','123')
    result=tracking.fetch_targets([t]);assert result[0]['metrics']=={'likes':7,'reposts':2,'replies':0,'quotes':None}
    assert 'DO NOT STORE' not in json.dumps(result)
    monkeypatch.setattr(tracking.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'visibility':'private','favourites_count':7})),**kwargs))
    private=tracking.fetch_targets([t])[0];assert private['state']=='unavailable' and all(v is None for v in private['metrics'].values())

def test_independent_platform_failures_and_institution_scope(local,monkeypatch):
    h=account(local);t=target(local,h);target(local,h,'https://bsky.app/profile/example.test/post/abc123')
    def fetch(selected):
        if selected[0]['platform']=='youtube':raise HTTPException(503,'Missing configured key')
        return [{'target_id':selected[0]['id'],'platform':'bluesky','metrics':{'likes':2},'observed_at':'TEST ONLY'}]
    monkeypatch.setattr(tracking,'fetch_targets',fetch)
    result=local.post('/api/v1/tracking/refresh',headers=h).json()
    assert result['state']=='partial' and len(result['observations'])==1 and result['errors'][0]['platform']=='youtube'
    from apps.api.db import add
    with Session() as s:
        other=add(s,'tracking-targets','other-institution',{'url':URL,'platform':'youtube','platform_id':'abcdefghijk','purpose':'OTHER INSTITUTION'});s.commit();other_id=other.id
    assert other_id not in {r['id'] for r in local.get('/api/v1/tracking/status',headers=h).json()['targets']}
    assert local.delete('/api/v1/tracking/targets/'+other_id,headers=h).status_code==404

def test_x_official_bearer_metrics_and_unavailable_post(monkeypatch):
    original=httpx.Client
    monkeypatch.setattr(tracking,'x_token',lambda:'TEST-X-SECRET')
    def handler(request):
        assert request.url.host=='api.x.com' and request.url.path=='/2/tweets'
        assert request.headers['authorization']=='Bearer TEST-X-SECRET'
        return httpx.Response(200,json={'data':[{'id':'123456','text':'DO NOT STORE','public_metrics':{'like_count':9,'retweet_count':2,'reply_count':0}}]})
    monkeypatch.setattr(tracking.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    _,pid,url=tracking.target_url('https://twitter.com/example/status/123456')
    result=tracking.fetch_targets([{'id':'target','platform':'x','platform_id':pid,'url':url},{'id':'missing','platform':'x','platform_id':'999999','url':'https://x.com/example/status/999999'}])
    assert result[0]['metrics']=={'likes':9,'reposts':2,'replies':0,'quotes':None,'impressions':None}
    assert result[1]['state']=='unavailable' and all(v is None for v in result[1]['metrics'].values())
    assert 'TEST-X-SECRET' not in json.dumps(result) and 'DO NOT STORE' not in json.dumps(result)
