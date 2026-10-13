"""Create a labeled complete synthetic review/action/report example on localhost only."""
import json,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
import httpx
BASE='http://127.0.0.1:8000/api/v1'
PASSWORD='Pnsi-Demo-2026!'
client=httpx.Client(timeout=30)
tokens={}
def headers(role):
    if role not in tokens:
        r=client.post(BASE+'/auth/login',json={'email':role+'@demo-onmne.local','password':PASSWORD});r.raise_for_status();tokens[role]=r.json()['token']
    return {'Authorization':'Bearer '+tokens[role]}
def request(method,path,role='analyst',**kwargs):
    r=client.request(method,BASE+path,headers={**headers(role),**kwargs.pop('headers',{})},**kwargs);r.raise_for_status();return r.json()
def listing(kind):return request('GET','/'+kind+'?limit=100')['items']
case=next(c for c in listing('cases') if c['code']=='C-001')
existing=[r for r in listing('responses') if r.get('demo_walkthrough')]
if existing:
    print('Complete training example already exists: '+existing[0]['id'])
else:
    a=next(a for a in listing('assessments') if a['case_id']==case['id'])
    a=request('POST','/assessments/'+a['id']+'/review','scientific_reviewer',json={'expected_version':a['version'],'decision':'contradicted','rationale':'SYNTHETIC TRAINING REVIEW: in the provided fictional Z/Y scenario, passage training-z-1 contradicts the universal prevention claim. This is not a real clinical assessment.'})
    r=request('POST','/responses','communication_editor',json={'data':{'case_id':case['id'],'assessment_id':a['id'],'locale':'fr','channel':'FAQ','demo_walkthrough':True}})
    for decision,role in [('request_review','communication_editor'),('scientific','scientific_reviewer'),('language','communication_editor'),('institutional','institutional_approver')]:
        r=request('POST','/responses/'+r['id']+'/approve',role,json={'expected_version':r['version'],'decision':decision,'rationale':'SYNTHETIC TRAINING SIGN-OFF: only fictional fixture evidence and wording were checked. No real institutional approval or medical claim.'})
    action=request('POST','/actions/record','communication_editor',headers={'Idempotency-Key':str(uuid.uuid4())},json={'response_id':r['id'],'expected_version':r['version'],'channel':'Training workshop · no public publication','performed_at':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),'reference':'Synthetic role walkthrough only'})
    report=request('POST','/reports',json={'data':{'title':'PNSI · Brief de démonstration synthétique','type':'weekly','locale':'fr','demo_walkthrough':True}})
    report=request('POST','/reports/'+report['id']+'/review','institutional_approver',json={'expected_version':report['version'],'decision':'approved','rationale':'Synthetic demonstration snapshot checked for fixture coverage and explicit limitations.'})
    folder=Path(__file__).resolve().parents[1]/'artifacts';folder.mkdir(exist_ok=True)
    for locale in ['fr','ar']:
        if locale=='ar':
            report=request('POST','/reports',json={'data':{'title':'PNSI · تقرير تجريبي اصطناعي','type':'weekly','locale':'ar'}})
            report=request('POST','/reports/'+report['id']+'/review','institutional_approver',json={'expected_version':report['version'],'decision':'approved','rationale':'Synthetic Arabic export rendering fixture; wording remains provisional and requires language review.'})
        pdf=client.get(BASE+'/reports/'+report['id']+'/export?format=pdf',headers=headers('institutional_approver'));pdf.raise_for_status();(folder/('report-qa-'+locale+'.pdf')).write_bytes(pdf.content)
    print(json.dumps({'case_id':case['id'],'response_id':r['id'],'action_id':action['id'],'reports':'artifacts/report-qa-fr.pdf and report-qa-ar.pdf'},indent=2))
for token in tokens.values():client.post(BASE+'/auth/logout',headers={'Authorization':'Bearer '+token})
