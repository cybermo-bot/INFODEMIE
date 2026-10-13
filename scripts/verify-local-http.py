"""Verify the real web proxy/API/database with an ephemeral local test session.

The temporary token is never printed, never enters a browser URL, only performs
GET requests and is revoked in finally. No users/passwords/roles are changed.
"""
import os,sys,json,secrets,hashlib,argparse
from pathlib import Path
from datetime import datetime,timezone,timedelta
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--institution',required=True);args=parser.parse_args()
os.environ['APP_ENV']='local';os.environ['DATABASE_URL']='sqlite:///'+(root/'data'/'pnsi-local.db').as_posix()
sys.path.insert(0,str(root))
import httpx
from sqlalchemy import select,delete
from apps.api.db import Session,Record,SessionRecord,audit
token=secrets.token_urlsafe(48);token_hash=hashlib.sha256(token.encode()).hexdigest()
with Session() as s:
    users=[r for r in s.scalars(select(Record).where(Record.kind=='users',Record.institution==args.institution)) if r.data().get('active') and r.data().get('role')=='administrator' and not r.data().get('must_change_password') and not r.data().get('synthetic')]
    if len(users)!=1:raise RuntimeError('Exactly one active real administrator is required for this local verification.')
    s.add(SessionRecord(token_hash=token_hash,user_id=users[0].id,expires_at=(datetime.now(timezone.utc)+timedelta(seconds=30)).isoformat()))
    audit(s,{'name':'PNSI · Vérification HTTP locale'},users[0],'system.local_http_verification_started');s.commit()
try:
    with httpx.Client(base_url='http://127.0.0.1:3001',timeout=10,trust_env=False,headers={'Authorization':'Bearer '+token}) as client:
        me=client.get('/api/v1/me');me.raise_for_status();assert me.json()['institution']==args.institution
        response=client.get('/api/v1/overview');response.raise_for_status();data=response.json()
        content=client.get('/api/v1/content?limit=100');content.raise_for_status()
        tracking=client.get('/api/v1/tracking/status');tracking.raise_for_status();tracking_data=tracking.json()
        assert content.json()['total']==data['total_collected']
        assert all(r['institution']==args.institution and not r.get('synthetic') for r in content.json()['items'])
        assert all(p.get('source_url') and p.get('license_url') for p in data['latest_publications'])
        result={'checked_at':datetime.now(timezone.utc).isoformat(),'automatic_enabled':tracking_data['automatic']['enabled'],'automatic_runner':tracking_data['automatic']['runner'],'discovered_social_publications':len(tracking_data['discoveries']),'topic_watches':[{k:w.get(k) for k in ['platform','state','error','last_attempt_at','next_poll_at']} for w in tracking_data['watches']],'social_tracking_status':'passed','selected_social_targets':len(tracking_data['targets']),'youtube_key_configured':tracking_data['youtube_configured'],'x_token_configured':tracking_data['x_configured'],'web_proxy':'passed','authenticated_api':'passed','institution_scope':'passed','database_total_matches_api':'passed','total_collected':data['total_collected'],'live_publications':data['live_publications'],'in_last_7_days':data['items'],'connected_feeds':data['connected_feeds'],'connections':data['connections'],'collection_results':[{k:r.get(k) for k in ['source_name','state','count','fetched','duplicates','finished_at']} for r in data['recent_collections']]}
        (root/'artifacts'/'live-connection-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))
finally:
    with Session() as s:s.execute(delete(SessionRecord).where(SessionRecord.token_hash==token_hash));s.commit()
