import os, sys, json
from pathlib import Path
os.environ['APP_ENV']='test'
os.environ['DATABASE_URL']='sqlite:///./test-pnsi.db'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
import apps.api.main as main
from apps.api.db import Base,engine,Session,Record,Event,RecordVersion
from sqlalchemy import select

CODE='test-installation-code-at-least-32-characters'
PASSWORD='Unique-Local-Account-2026!'

@pytest.fixture
def local(monkeypatch):
    monkeypatch.setattr(main,'ENV','local')
    monkeypatch.setenv('LOCAL_SETUP_CODE',CODE)
    main.login_attempts.clear()
    Base.metadata.drop_all(engine)
    with TestClient(main.app) as c:yield c

def setup(c,**changes):
    data={'name':'Local owner','email':'owner@example.test','password':PASSWORD,'role':'administrator','organization':'My organization','setup_code':CODE}
    data.update(changes)
    return c.post('/api/v1/auth/setup',json=data)

def login(c,email='owner@example.test',password=PASSWORD):
    r=c.post('/api/v1/auth/login',json={'email':email,'password':password})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def create(c,headers,role='analyst'):
    return c.post('/api/v1/accounts',headers=headers,json={'name':role,'email':role+'@example.test','role':role,'password':PASSWORD})

def test_empty_installation_requires_code_and_is_one_time(local):
    assert local.get('/api/v1/auth/config').json()=={'mode':'local','configured':False}
    assert setup(local,setup_code='wrong-code-is-not-valid').status_code==403
    assert setup(local,password='Pnsi-Demo-2026!').status_code==422
    assert setup(local,role='scientific_reviewer').status_code==422
    assert setup(local).status_code==200
    assert setup(local).status_code==409
    h=login(local)
    assert local.get('/api/v1/overview',headers=h).json()['cases']==0
    assert local.get('/api/v1/overview',headers=h).json()['items']==0
    assert local.post('/api/v1/auth/login',json={'email':'analyst@demo-onmne.local','password':'Pnsi-Demo-2026!'}).status_code==401
    with Session() as s:
        assert not any(r.data().get('synthetic') for r in s.scalars(select(Record)))
        histories=' '.join(s.scalars(select(RecordVersion.payload)))+' '.join(s.scalars(select(Event.payload)))
        assert PASSWORD not in histories and 'password_hash' not in histories and CODE not in histories

def test_temp_password_gate_and_session_revocation(local):
    assert setup(local).status_code==200
    admin=login(local)
    r=create(local,admin);assert r.status_code==200,r.text
    staff=login(local,'analyst@example.test')
    assert local.get('/api/v1/me',headers=staff).json()['must_change_password']
    assert local.get('/api/v1/cases',headers=staff).status_code==403
    changed=local.post('/api/v1/auth/password',headers=staff,json={'current_password':PASSWORD,'new_password':'A-New-Unique-Password-2026!'})
    assert changed.status_code==200,changed.text
    assert local.get('/api/v1/me',headers=staff).status_code==401
    h=login(local,'analyst@example.test','A-New-Unique-Password-2026!')
    assert local.get('/api/v1/cases',headers=h).status_code==200
    assert create(local,h,'viewer').status_code==403
    assert create(local,admin).status_code==409
    assert create(local,admin,'unrecognized').status_code==422
    reset=local.post('/api/v1/accounts/'+r.json()['id']+'/reset-password',headers=admin,json={'expected_version':2,'temporary_password':'Reset-Unique-Password-2026!'})
    assert reset.status_code==200,reset.text
    assert local.get('/api/v1/me',headers=h).status_code==401
    assert local.get('/api/v1/me',headers=login(local,'analyst@example.test','Reset-Unique-Password-2026!')).json()['must_change_password']

def test_loopback_host_and_origin_guard(local):
    assert local.get('/api/v1/auth/config',headers={'host':'attacker.example'}).status_code==403
    assert local.post('/api/v1/auth/setup',headers={'origin':'https://attacker.example'},json={}).status_code==403
    assert local.get('/api/v1/auth/config',headers={'origin':'http://127.0.0.1:3001'}).status_code==200

def test_owner_cannot_lock_out_the_installation(local):
    owner=setup(local).json()['user'];h=login(local)
    assert local.patch('/api/v1/users/'+owner['id'],headers=h,json={'expected_version':owner['version'],'data':{'active':False}}).status_code==422
    assert local.post('/api/v1/accounts/'+owner['id']+'/reset-password',headers=h,json={'expected_version':owner['version'],'temporary_password':'Reset-Password-For-Owner!'}).status_code==422

def test_local_refuses_synthetic_database(monkeypatch):
    Base.metadata.drop_all(engine)
    monkeypatch.setattr(main,'ENV','demo')
    with TestClient(main.app):pass
    monkeypatch.setattr(main,'ENV','local')
    with pytest.raises(RuntimeError,match='separate database'):
        with TestClient(main.app):pass

def test_real_import_to_review_and_approved_response(local):
    assert setup(local).status_code==200
    admin=login(local);accounts={}
    for role in ('analyst','scientific_reviewer','communication_editor','institutional_approver'):
        assert create(local,admin,role).status_code==200
        h=login(local,role+'@example.test')
        assert local.post('/api/v1/auth/password',headers=h,json={'current_password':PASSWORD,'new_password':'Personal-'+role+'-Password!'}).status_code==200
        accounts[role]=login(local,role+'@example.test','Personal-'+role+'-Password!')
    h=accounts['analyst']
    source=local.get('/api/v1/sources',headers=h).json()['items'][0]
    data={'source_id':source['id'],'permission':'Owner supplied authorized private question for this test','preview':False,'items':[{'text':'Question personnelle : quels éléments sont disponibles ?','language':'fr'}]}
    result=local.post('/api/v1/imports',headers={**h,'Idempotency-Key':'local-real-import'},json=data)
    assert result.status_code==200,result.text
    repeat=local.post('/api/v1/imports',headers={**h,'Idempotency-Key':'local-real-import-repeat'},json=data)
    assert repeat.status_code==200 and repeat.json()['count']==0 and repeat.json()['duplicates']==1
    content=local.get('/api/v1/content',headers=h).json()['items'][0]
    assert content['synthetic'] is False
    result=local.post('/api/v1/content/'+content['id']+'/case',headers=h,json={'title':'Question à examiner'})
    assert result.status_code==200,result.text
    case=result.json()
    claim=local.get('/api/v1/claims',headers=h).json()['items'][0]
    assert local.post('/api/v1/claims/'+claim['id']+'/verify',headers=h,json={}).status_code==202
    from workers.run import process_one
    assert process_one()
    a=local.get('/api/v1/assessments',headers=h).json()['items'][0]
    assert a['synthetic'] is False
    result=local.post('/api/v1/assessments/'+a['id']+'/review',headers=accounts['scientific_reviewer'],json={'expected_version':a['version'],'decision':'insufficient_evidence','rationale':'Aucun document approuvé disponible. Ne pas conclure.'})
    assert result.status_code==200,result.text
    result=local.post('/api/v1/responses',headers=accounts['communication_editor'],json={'data':{'case_id':case['id'],'assessment_id':a['id'],'locale':'fr','channel':'FAQ'}})
    assert result.status_code==200,result.text
    response=result.json();assert 'synthétique' not in response['body'] and response['synthetic'] is False
    for decision,role in [('request_review','communication_editor'),('scientific','scientific_reviewer'),('language','communication_editor'),('institutional','institutional_approver')]:
        result=local.post('/api/v1/responses/'+response['id']+'/approve',headers=accounts[role],json={'expected_version':response['version'],'decision':decision,'rationale':'Examen indépendant de cette réponse prudente sans conclusion factuelle.'})
        assert result.status_code==200,result.text
        response=result.json()
    assert response['state']=='approved'
