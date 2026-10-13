import os,sys,uuid,json
from pathlib import Path
os.environ['APP_ENV']='test'
os.environ['DATABASE_URL']='sqlite:///./test-pnsi.db'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app,redact,login_attempts
from apps.api.db import Base,engine

@pytest.fixture()
def c():
    login_attempts.clear()
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:yield client
@pytest.fixture()
def auth(c):
    cache={}
    def get(role='analyst',inst='demo-onmne'):
        key=role+inst
        if key not in cache:
            r=c.post('/api/v1/auth/login',json={'email':role+'@'+inst+'.local','password':'Pnsi-Demo-2026!'})
            assert r.status_code==200,r.text
            cache[key]={'Authorization':'Bearer '+r.json()['token']}
        return cache[key]
    return get
def items(c,auth,kind,role='analyst',**params):
    r=c.get('/api/v1/'+kind,headers=auth(role),params=params);assert r.status_code==200,r.text;return r.json()['items']
def review(c,auth,path,r,decision,role,rationale='Explicit test rationale, synthetic training only'):
    return c.post('/api/v1/'+path,headers=auth(role),json={'expected_version':r['version'],'decision':decision,'rationale':rationale})
def confirmed(c,auth):
    a=next(x for x in items(c,auth,'assessments') if x['proposed_status']=='contradicted')
    r=review(c,auth,'assessments/'+a['id']+'/review',a,'contradicted','scientific_reviewer');assert r.status_code==200,r.text;return r.json()
def response(c,auth):
    a=confirmed(c,auth)
    r=c.post('/api/v1/responses',headers=auth('communication_editor'),json={'data':{'case_id':a['case_id'],'assessment_id':a['id'],'locale':'fr','channel':'FAQ'}})
    assert r.status_code==200,r.text;return r.json()
def approved(c,auth):
    r=response(c,auth)
    for decision,role in [('request_review','communication_editor'),('scientific','scientific_reviewer'),('language','communication_editor'),('institutional','institutional_approver')]:
        result=review(c,auth,'responses/'+r['id']+'/approve',r,decision,role);assert result.status_code==200,result.text;r=result.json()
    return r

def test_health_and_authentication(c):
    assert c.get('/health/live').status_code==200
    assert c.get('/api/v1/cases').status_code==401
    assert c.post('/api/v1/auth/login',json={'email':'invalid@example.test','password':'bad'}).status_code==401
def test_institution_scope(c,auth):
    case=items(c,auth,'cases')[0]
    assert c.get('/api/v1/cases/'+case['id'],headers=auth('analyst','demo-partner')).status_code==404
    assert c.get('/api/v1/cases',headers=auth('analyst','demo-partner')).json()['total']==0
    assert c.get('/api/v1/overview',headers=auth('analyst','demo-partner')).json()['items']==0
    assert c.get('/api/v1/cases/'+case['id']+'/timeline',headers=auth('analyst','demo-partner')).status_code==404
def test_sensitive_lists_role_gated(c,auth):
    for kind in ['users','audit','settings']:
        assert c.get('/api/v1/'+kind,headers=auth('viewer')).status_code==403
def test_admin_cannot_grant_scientific_authority(c,auth):
    a=items(c,auth,'assessments')[0]
    assert review(c,auth,'assessments/'+a['id']+'/review',a,'insufficient_evidence','administrator').status_code==403
    u=items(c,auth,'users','administrator')[0]
    assert c.patch('/api/v1/users/'+u['id'],headers=auth('administrator'),json={'expected_version':u['version'],'data':{'role':'scientific_reviewer'}}).status_code==422
def test_optimistic_concurrency(c,auth):
    case=items(c,auth,'cases')[0];body={'expected_version':case['version'],'data':{'owner':'Test analyst'}}
    assert c.patch('/api/v1/cases/'+case['id'],headers=auth(),json=body).status_code==200
    assert c.patch('/api/v1/cases/'+case['id'],headers=auth(),json=body).status_code==409
def test_protected_fields(c,auth):
    case=items(c,auth,'cases')[0]
    assert c.patch('/api/v1/cases/'+case['id'],headers=auth(),json={'expected_version':case['version'],'data':{'evidence_status':'supported'}}).status_code==422
def test_factual_verdict_requires_citations(c,auth):
    a=next(x for x in items(c,auth,'assessments') if not x['evidence_links'])
    assert review(c,auth,'assessments/'+a['id']+'/review',a,'supported','scientific_reviewer').status_code==422
    assert review(c,auth,'assessments/'+a['id']+'/review',a,'insufficient_evidence','scientific_reviewer').status_code==200
def test_draft_requires_confirmed_assessment(c,auth):
    a=items(c,auth,'assessments')[0]
    assert c.post('/api/v1/responses',headers=auth('communication_editor'),json={'data':{'case_id':a['case_id'],'assessment_id':a['id']}}).status_code==422
def test_cannot_bypass_review_stages(c,auth):
    r=response(c,auth)
    assert review(c,auth,'responses/'+r['id']+'/approve',r,'institutional','institutional_approver').status_code==422
    assert review(c,auth,'responses/'+r['id']+'/approve',r,'scientific','analyst').status_code==403
def test_exact_version_approval(c,auth):
    r=approved(c,auth)
    assert r['approval']['exact_version']==r['version']
    assert r['approval']['assessment_version']==r['assessment_version']
    assert len(r['approval']['evidence_snapshot_hash'])==64
def test_edit_invalidates_approval(c,auth):
    r=approved(c,auth)
    result=c.put('/api/v1/responses/'+r['id'],headers=auth('communication_editor'),json={'expected_version':r['version'],'body':'New factual wording, needs fresh reviews','locale':'fr','channel':'FAQ'})
    assert result.status_code==200,result.text
    d=result.json();assert d['state']=='draft' and d['approval'] is None and d['scientific_review'] is None
def test_uncertain_draft_preserves_uncertainty(c,auth):
    a=next(x for x in items(c,auth,'assessments') if x['proposed_status']=='insufficient_evidence')
    a=review(c,auth,'assessments/'+a['id']+'/review',a,'insufficient_evidence','scientific_reviewer').json()
    r=c.post('/api/v1/responses',headers=auth('communication_editor'),json={'data':{'case_id':a['case_id'],'assessment_id':a['id'],'locale':'en'}}).json()
    assert 'does not allow a definitive conclusion' in r['body']
def test_action_requires_approval(c,auth):
    r=response(c,auth)
    result=c.post('/api/v1/actions/record',headers={**auth('communication_editor'),'Idempotency-Key':str(uuid.uuid4())},json={'response_id':r['id'],'expected_version':r['version'],'channel':'FAQ','performed_at':'2026-10-01T12:00:00+00:00'})
    assert result.status_code==422
def test_action_idempotency_and_follow_up(c,auth):
    r=approved(c,auth);headers={**auth('communication_editor'),'Idempotency-Key':str(uuid.uuid4())};body={'response_id':r['id'],'expected_version':r['version'],'channel':'FAQ','performed_at':'2026-10-01T12:00:00+00:00'}
    a=c.post('/api/v1/actions/record',headers=headers,json=body);assert a.status_code==200,a.text
    b=c.post('/api/v1/actions/record',headers=headers,json=body);assert a.json()['id']==b.json()['id']
    f=items(c,auth,'follow-ups');assert sorted(x['window_hours'] for x in f)==[48,168,720]
def test_evidence_withdrawal_invalidates(c,auth):
    r=approved(c,auth);d=items(c,auth,'documents')[0]
    result=review(c,auth,'documents/'+d['id']+'/review',d,'withdrawn','scientific_reviewer');assert result.status_code==200
    r=c.get('/api/v1/responses/'+r['id'],headers=auth()).json();assert r['approval'] is None and r['state']=='changes_requested'
def test_import_preview_redaction_and_dedup(c,auth):
    source=next(x for x in items(c,auth,'sources') if x['platform']=='manual')
    body={'source_id':source['id'],'permission':'Authorized synthetic test fixture','items':[{'text':'Contact @private person@example.test +216 22 333 444','language':'fr','published_at':'2026-10-01T00:00:00+00:00'}],'preview':True}
    p=c.post('/api/v1/imports',headers=auth(),json=body);assert p.status_code==200
    assert '@private' not in p.json()['preview'][0]['text'];assert 'person@example.test' not in p.json()['preview'][0]['text']
    body['preview']=False;headers={**auth(),'Idempotency-Key':str(uuid.uuid4())}
    a=c.post('/api/v1/imports',headers=headers,json=body);b=c.post('/api/v1/imports',headers=headers,json=body);assert a.json()['id']==b.json()['id']
    headers['Idempotency-Key']=str(uuid.uuid4());d=c.post('/api/v1/imports',headers=headers,json=body);assert d.json()['count']==0
def test_import_validation_is_atomic(c,auth):
    source=next(x for x in items(c,auth,'sources') if x['platform']=='manual');n=len(items(c,auth,'content'))
    r=c.post('/api/v1/imports',headers={**auth(),'Idempotency-Key':str(uuid.uuid4())},json={'source_id':source['id'],'permission':'Authorized synthetic fixture','preview':False,'items':[{'text':'Valid text'},{'text':''}]})
    assert r.status_code==422 and len(items(c,auth,'content'))==n
def test_report_snapshot_and_export_gate(c,auth):
    r=c.post('/api/v1/reports',headers=auth(),json={'data':{'title':'Test report','type':'weekly'}}).json()
    assert c.get('/api/v1/reports/'+r['id']+'/export',headers=auth()).status_code==422
    r=review(c,auth,'reports/'+r['id']+'/review',r,'approved','institutional_approver').json()
    assert c.get('/api/v1/reports/'+r['id']+'/export?format=csv',headers=auth('viewer')).status_code==200
    assert r['snapshot']['items']==56
    pdf=c.get('/api/v1/reports/'+r['id']+'/export?format=pdf',headers=auth('viewer'))
    assert pdf.status_code==200,pdf.text[:200]
    assert pdf.content.startswith(b'%PDF-') and len(pdf.content)>10000
def test_jobs_and_worker(c,auth):
    from workers.run import process_one
    claim=items(c,auth,'claims')[0]
    a=c.post('/api/v1/claims/'+claim['id']+'/verify',headers=auth());b=c.post('/api/v1/claims/'+claim['id']+'/verify',headers=auth())
    assert a.status_code==202 and a.json()['id']==b.json()['id']
    assert process_one()
    job=c.get('/api/v1/jobs/'+a.json()['id'],headers=auth()).json();assert job['state']=='succeeded'
def test_ssrf_blocked():
    from apps.api.connectors import validate_url
    from fastapi import HTTPException
    for url in ['http://example.com/rss','https://127.0.0.1/feed','https://localhost/feed','https://user:pass@example.com/feed','https://example.com:8080/feed']:
        with pytest.raises(HTTPException):validate_url(url)
def test_logout_revokes_session(c,auth):
    h=auth();assert c.post('/api/v1/auth/logout',headers=h).status_code==200
    assert c.get('/api/v1/me',headers=h).status_code==401
def test_pagination_limits(c,auth):
    a=c.get('/api/v1/content?limit=10',headers=auth()).json();assert len(a['items'])==10 and a['next_cursor']==10
    assert c.get('/api/v1/content?limit=101',headers=auth()).status_code==422

def test_new_case_creates_traceable_claim(c,auth):
    r=c.post('/api/v1/cases',headers=auth(),json={'data':{'title':'New synthetic atomic claim','priority':20,'topic':'Prévention','language':'fr'}})
    assert r.status_code==200,r.text
    claim=items(c,auth,'claims',case_id=r.json()['id']);assert len(claim)==1
    assert claim[0]['neutral_text']=='New synthetic atomic claim'
def test_out_of_range_priority(c,auth):
    assert c.post('/api/v1/cases',headers=auth(),json={'data':{'title':'Invalid priority case','priority':101}}).status_code==422
def test_audit_never_contains_password_hash(c,auth):
    auth('administrator')
    events=items(c,auth,'audit','administrator')
    assert 'password_hash' not in json.dumps(events)
def test_immutable_versions_and_scoping(c,auth):
    r=approved(c,auth)
    history=c.get('/api/v1/versions/responses/'+r['id'],headers=auth()).json()['items']
    assert len(history)==5 and history[0]['state']=='approved' and history[-1]['state']=='draft'
    assert c.get('/api/v1/versions/responses/'+r['id'],headers=auth('analyst','demo-partner')).status_code==404
def test_independent_annotation_and_measured_benchmark(c,auth):
    a=c.post('/api/v1/annotations',headers=auth(),json={'data':{'title':'Synthetic reference sample','label':'insufficient_evidence','language':'fr','dataset_version':'TEST-1','annotator_id':c.get('/api/v1/me',headers=auth()).json()['id']}}).json()
    frozen=c.post('/api/v1/evaluation/freeze',headers=auth('scientific_reviewer'),json={'data':{'dataset_version':'TEST-1'}});assert frozen.status_code==422
    a=c.post('/api/v1/annotations/'+a['id']+'/resolve',headers=auth('scientific_reviewer'),json={'expected_version':a['version'],'reference_label':'insufficient_evidence','rationale':'Independent review of synthetic test reference'}).json()
    frozen=c.post('/api/v1/evaluation/freeze',headers=auth('scientific_reviewer'),json={'data':{'dataset_version':'TEST-1'}}).json()
    measured=c.post('/api/v1/evaluations/'+frozen['id']+'/measure',headers=auth('scientific_reviewer'),json={'expected_version':frozen['version'],'model_version':'test-fixture-v1','predictions':{a['id']:'insufficient_evidence'}})
    assert measured.status_code==200,measured.text
    assert measured.json()['metrics']['overall']['accuracy']==1.0
    assert measured.json()['metrics']['overall']['sample_size']==1
    assert measured.json()['release_status']=='requires_threshold_review'
def test_citation_schema_rejects_unknown_fields():
    from apps.api.schemas import AssessmentProposal
    from pydantic import ValidationError
    with pytest.raises(ValidationError):AssessmentProposal.model_validate({'proposed_status':'supported','rationale':'some rationale','evidence_links':[],'limitations':['limited'],'execute_command':'forbidden'})
def test_content_deletion_propagates_to_snapshot_versions(c,auth):
    item=items(c,auth,'content')[0];original=item['original_text']
    report=c.post('/api/v1/reports',headers=auth(),json={'data':{'title':'Snapshot before deletion','type':'weekly'}}).json()
    deletion=c.request('DELETE','/api/v1/content/'+item['id'],headers=auth('administrator'),json={'expected_version':item['version'],'decision':'delete','rationale':'Authorized retention deletion in isolated test fixture'})
    assert deletion.status_code==200,deletion.text
    r=c.get('/api/v1/reports/'+report['id'],headers=auth()).json()
    assert original not in json.dumps(r,ensure_ascii=False)
    assert r['state']=='withdrawn'
    versions=c.get('/api/v1/versions/reports/'+report['id'],headers=auth()).json()
    assert original not in json.dumps(versions,ensure_ascii=False)
def test_overview_counts_unassigned_authorized_imports(c,auth):
    source=next(x for x in items(c,auth,'sources') if x['platform']=='manual')
    result=c.post('/api/v1/imports',headers={**auth(),'Idempotency-Key':str(uuid.uuid4())},json={'source_id':source['id'],'permission':'Synthetic UI-equivalent authorized test fixture','preview':False,'items':[{'text':'Unassigned synthetic imported question','language':'fr','topic':'Prévention'}]})
    assert result.status_code==200,result.text
    overview=c.get('/api/v1/overview',headers=auth()).json()
    assert overview['items']==57 and overview['cases']==6
