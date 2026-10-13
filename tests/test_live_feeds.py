from datetime import datetime,timezone,timedelta
from test_local_accounts import local,setup,login
from apps.api.connectors import RSSConnector
from apps.api.db import Session,Record,add,update,now
from sqlalchemy import select
from workers.run import process_one,schedule_due,heartbeat

def rss_item():
    return {'title':'TEST ONLY: real connector workflow fixture','summary':'Public test metadata','text':'TEST ONLY: real connector workflow fixture\nPublic test metadata','published_at':now(),'publication_date_known':True,'collected_at':now(),'source_url':'https://www.ecdc.europa.eu/en/test-fixture','platform_item_id':'test-guid','language':'en','content_type':'institutional_news','attribution':'ECDC','license_url':'https://creativecommons.org/licenses/by/4.0/','modifications':'Plain text extraction'}

def test_rss_atom_metadata_dates_and_unsafe_markup():
    connector=RSSConnector({'language':'en','name':'TEST RSS'})
    xml=b'''<rss><channel><language>en-GB</language><item><title>Title &amp; facts</title><description>&lt;p&gt;A &amp; B&lt;/p&gt;&lt;script&gt;hidden&lt;/script&gt;</description><link>https://example.org/article</link><guid>guid-1</guid><pubDate>Fri, 09 Oct 2026 15:30:22 +0200</pubDate></item><item><title>Undated</title><link>javascript:alert(1)</link><pubDate>invalid</pubDate></item></channel></rss>'''
    records=connector.parse_feed(xml)['records'];first=records[0]
    assert first['title']=='Title & facts' and first['summary']=='A & B' and first['language']=='en'
    assert first['published_at']=='2026-10-09T13:30:22+00:00' and first['source_url']=='https://example.org/article'
    assert records[1]['published_at'] is None and not records[1]['publication_date_known'] and records[1]['source_url'] is None
    atom=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>atom-1</id><title>Atom title</title><updated>2026-10-09T10:00:00Z</updated><link href="https://example.org/atom"/></entry></feed>'''
    first=connector.parse_feed(atom)['records'][0]
    assert first['published_at']=='2026-10-09T10:00:00+00:00' and first['source_url']=='https://example.org/atom'
    import pytest
    with pytest.raises(ValueError):connector.parse_feed(b'<!DOCTYPE rss><rss/>')

def connect(local,monkeypatch):
    assert setup(local).status_code==200
    h=login(local)
    monkeypatch.setattr('apps.api.connectors.validate_url',lambda url:'www.ecdc.europa.eu')
    r=local.post('/api/v1/connectors/public',headers=h,json={'keys':['ecdc-news','ecdc-updates','ecdc-threats']})
    assert r.status_code==202,r.text
    return h,r.json()

def test_live_pipeline_idempotency_attribution_and_cross_feed_dedup(local,monkeypatch):
    h,connected=connect(local,monkeypatch)
    repeat=local.post('/api/v1/connectors/public',headers=h,json={'keys':['ecdc-news','ecdc-updates','ecdc-threats']})
    assert repeat.status_code==202 and repeat.json()['items']==connected['items']
    monkeypatch.setattr(RSSConnector,'fetch_batch',lambda self:{'records':[rss_item()],'watermark':now()})
    assert schedule_due()==0
    for _ in range(3):assert process_one()
    overview=local.get('/api/v1/overview',headers=h).json()
    assert overview['items']==1 and overview['live_publications']==1 and overview['connected_feeds']==3
    first=overview['latest_publications'][0]
    assert len(first['source_ids'])==3 and first['synthetic'] is False and first['source_url'].startswith('https://') and first['license_url']
    assert len(overview['recent_collections'])==3 and sum(x['count'] for x in overview['recent_collections'])==1
    heartbeat();assert local.get('/api/v1/overview',headers=h).json()['connections']['worker']=='connected'
    heartbeat('stopped');assert local.get('/api/v1/overview',headers=h).json()['connections']['worker']=='not_responding'
    assert schedule_due()==0
    r=local.post('/api/v1/sources/'+connected['items'][0]['source_id']+'/collect',headers=h)
    assert r.status_code==202
    assert local.post('/api/v1/sources/'+connected['items'][0]['source_id']+'/collect',headers=h).json()['id']==r.json()['id']

def test_failed_feed_does_not_create_replacement_data_and_has_backoff(local,monkeypatch):
    h,connected=connect(local,monkeypatch)
    def failure(self):raise ConnectionError('Network unavailable in test')
    monkeypatch.setattr(RSSConnector,'fetch_batch',failure)
    assert process_one()
    overview=local.get('/api/v1/overview',headers=h).json()
    assert overview['items']==0 and overview['live_publications']==0 and overview['connections']['failed']==1
    source=local.get('/api/v1/sources/'+connected['items'][0]['source_id'],headers=h).json()
    assert source['state']=='error' and source['next_poll_at']>now() and 'Network unavailable' in source['error']
    assert schedule_due()==0

def test_catalog_unknown_key_rejected_and_undated_content_is_honest(local,monkeypatch):
    h,connected=connect(local,monkeypatch)
    assert local.post('/api/v1/connectors/public',headers=h,json={'keys':['private-server']}).status_code==422
    with Session() as s:
        source=s.get(Record,connected['items'][0]['source_id'])
        add(s,'content',source.institution,dict(rss_item(),published_at=None,publication_date_known=False,source_id=source.id,source_name='TEST ONLY',synthetic=False))
        s.commit()
    overview=local.get('/api/v1/overview',headers=h).json()
    assert overview['items']==1 and overview['undated_items']==1 and overview['latest_publications'][0]['published_at'] is None
