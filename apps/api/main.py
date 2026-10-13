import os, json, hashlib, secrets, re, csv, io, logging, time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from typing import Any, Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Header, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from .db import Session, Record, RecordVersion, Event, SessionRecord, RetryKey, AccountEmail, WorkerStatus, init, add, update, audit, now, uid
from .seed import seed,check_password,password_hash,ROLES

ENV=os.getenv('APP_ENV','demo')
if ENV not in ('demo','test','local'):raise RuntimeError('Public production deployment requires configured institutional identity. Supported modes: demo, test, local.')
@asynccontextmanager
async def lifespan(app):
    init()
    with Session() as s:
        if ENV in ('demo','test'):seed(s)
        elif any(r.data().get('synthetic') for r in s.scalars(select(Record).where(Record.kind=='users'))):
            raise RuntimeError('Local mode requires a separate database without demonstration accounts.')
    automatic_stop=None
    if ENV=='local' and os.getenv('APP_ENV')=='local':
        import threading
        from .automatic_tracking import loop
        automatic_stop=threading.Event()
        threading.Thread(target=loop,args=(automatic_stop,),daemon=True,name='pnsi-social-monitor').start()
    try:yield
    finally:
        if automatic_stop:automatic_stop.set()
app=FastAPI(title='PNSI API',version='0.1.0',lifespan=lifespan)
def db():
    with Session() as s:
        try:yield s
        except Exception:s.rollback();raise

@app.middleware('http')
async def request_context(request,call_next):
    request.state.request_id=uid()
    if ENV=='local' and request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
        return JSONResponse(status_code=403,content={'message':'Local mode is restricted to this computer.'})
    if ENV=='local':
        from urllib.parse import urlsplit
        if request.url.hostname not in ('127.0.0.1','localhost','::1','testserver'):
            return JSONResponse(status_code=403,content={'message':'Invalid local hostname.'})
        origin=request.headers.get('origin')
        if origin and origin not in ('http://127.0.0.1:3001','http://localhost:3001'):
            return JSONResponse(status_code=403,content={'message':'This origin cannot access the local installation.'})
    response=await call_next(request)
    response.headers['X-Request-ID']=request.state.request_id
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response
@app.exception_handler(HTTPException)
async def error(request,exc):
    return JSONResponse(status_code=exc.status_code,content={'code':{401:'unauthenticated',403:'forbidden',404:'not_found',409:'conflict',422:'validation',429:'rate_limited',503:'unavailable'}.get(exc.status_code,'error'),'message':str(exc.detail),'request_id':request.state.request_id},headers=exc.headers)

def current(request:Request,authorization:str=Header(default=''),s=Depends(db)):
    token=authorization.removeprefix('Bearer ')
    session=s.get(SessionRecord,hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires_at<now():raise HTTPException(401,'Sign in to continue.')
    r=s.get(Record,session.user_id)
    if not r or not r.data()['active']:raise HTTPException(401,'Session is no longer active.')
    d=r.data();d.pop('password_hash',None)
    if d.get('must_change_password') and request.url.path not in ('/api/v1/me','/api/v1/auth/password','/api/v1/auth/logout'):
        raise HTTPException(403,'Change your temporary password before continuing.')
    return d
def require(user,*roles):
    if user['role'] not in roles:raise HTTPException(403,'Your role cannot perform this operation.')
def get(s,kind,id,user):
    r=s.get(Record,id)
    if not r or r.kind!=kind or r.institution!=user['institution']:raise HTTPException(404,'Record unavailable in this institution.')
    return r
def rows(s,kind,user):return s.scalars(select(Record).where(Record.kind==kind,Record.institution==user['institution']).order_by(Record.created_at.desc())).all()
def clean(r):
    d=r.data();d.pop('password_hash',None);return d

login_attempts=defaultdict(list)
class Login(BaseModel):
    email:str=Field(max_length=200)
    password:str=Field(max_length=200)
@app.post('/api/v1/auth/login')
def login(body:Login,request:Request,s=Depends(db)):
    ip=request.client.host if request.client else 'unknown';t=time.monotonic()
    login_attempts[ip]=[x for x in login_attempts[ip] if t-x<60]
    if len(login_attempts[ip])>=20:raise HTTPException(429,'Too many sign-in attempts. Try again in one minute.',headers={'Retry-After':'60'})
    login_attempts[ip].append(t)
    r=next((x for x in s.scalars(select(Record).where(Record.kind=='users')) if x.data()['email']==body.email.lower()),None)
    if not r or not r.data()['active'] or not check_password(body.password,r.data()['password_hash']):raise HTTPException(401,'Invalid sign-in details.')
    token=secrets.token_urlsafe(48)
    s.add(SessionRecord(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=r.id,expires_at=(datetime.now(timezone.utc)+timedelta(hours=8)).isoformat()));audit(s,clean(r),r,'session.created');s.commit()
    return {'token':token,'user':clean(r),'mode':ENV}
@app.post('/api/v1/auth/logout')
def logout(user=Depends(current),authorization:str=Header(default=''),s=Depends(db)):
    s.execute(delete(SessionRecord).where(SessionRecord.token_hash==hashlib.sha256(authorization.removeprefix('Bearer ').encode()).hexdigest()));s.commit();return {'ok':True}
@app.get('/api/v1/me')
def me(user=Depends(current)):return user
@app.get('/health/live')
def health():return {'status':'ok','mode':ENV}
@app.get('/health/ready')
def ready(s=Depends(db)):
    s.execute(select(Record.id).limit(1));return {'status':'ready'}

@app.get('/api/v1/auth/config')
def auth_config(s=Depends(db)):
    return {'mode':ENV,'configured':bool(s.scalar(select(Record.id).where(Record.kind=='users').limit(1)))}

def strong_password(value):
    if len(value)<12 or value=='Pnsi-Demo-2026!' or len(set(value))<6:
        raise HTTPException(422,'Use a unique password of at least 12 characters (at least 6 distinct characters).')

class AccountCreate(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    email:str=Field(min_length=5,max_length=200,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password:str=Field(min_length=12,max_length=200)
    role:Literal['analyst','scientific_reviewer','communication_editor','institutional_approver','viewer','administrator','operator']
class LocalSetup(AccountCreate):
    organization:str=Field(min_length=2,max_length=150)
    setup_code:str=Field(min_length=16,max_length=200)

def enroll(s,body,institution,temporary):
    from sqlalchemy.exc import IntegrityError
    strong_password(body.password)
    email=body.email.strip().lower()
    if any(r.data()['email']==email for r in s.scalars(select(Record).where(Record.kind=='users'))):
        raise HTTPException(409,'An account with this email already exists.')
    r=add(s,'users',institution,{'name':body.name.strip(),'email':email,'role':body.role,'active':True,'locale':'fr','timezone':'Africa/Tunis','password_hash':password_hash(body.password),'synthetic':False,'must_change_password':temporary})
    s.add(AccountEmail(email=email,user_id=r.id))
    try:s.flush()
    except IntegrityError:
        s.rollback();raise HTTPException(409,'An account with this email already exists.')
    return r

@app.post('/api/v1/auth/setup')
def setup_local(body:LocalSetup,request:Request,s=Depends(db)):
    from sqlalchemy.exc import IntegrityError
    if ENV!='local':raise HTTPException(403,'Setup is only available in local mode.')
    setup_secret=os.getenv('LOCAL_SETUP_CODE','')
    if not setup_secret or not secrets.compare_digest(body.setup_code,setup_secret):
        raise HTTPException(403,'Invalid setup code. Use the code displayed by the local launcher.')
    if s.scalar(select(Record.id).where(Record.kind=='users').limit(1)):
        raise HTTPException(409,'This installation is already configured.')
    if body.role!='administrator':raise HTTPException(422,'The first account must be an administrator.')
    inst=uid();add(s,'institutions',inst,{'name':body.organization.strip(),'synthetic':False})
    r=enroll(s,body,inst,False)
    add(s,'sources',inst,{'name':'Import manuel autorisé','platform':'manual','state':'ready','enabled':True,'permission':'Permission required for each import','languages':'fr, en, ar, derja','owner':body.name,'retention_days':90,'synthetic':False})
    s.add(RetryKey(key='local-installation-bootstrap',institution=inst,operation='setup',result_id=r.id))
    audit(s,clean(r),r,'installation.initialized')
    try:s.commit()
    except IntegrityError:
        s.rollback();raise HTTPException(409,'This installation is already configured.')
    return {'user':clean(r),'mode':ENV}

@app.post('/api/v1/accounts')
def create_account(body:AccountCreate,user=Depends(current),s=Depends(db)):
    require(user,'administrator')
    if ENV!='local':raise HTTPException(403,'Real account provisioning requires local mode.')
    r=enroll(s,body,user['institution'],True);audit(s,user,r,'account.created');s.commit();return clean(r)

class PasswordChange(BaseModel):
    current_password:str=Field(max_length=200)
    new_password:str=Field(min_length=12,max_length=200)
@app.post('/api/v1/auth/password')
def change_password(body:PasswordChange,user=Depends(current),s=Depends(db)):
    r=get(s,'users',user['id'],user)
    if not check_password(body.current_password,r.data()['password_hash']):raise HTTPException(403,'Current password is incorrect.')
    strong_password(body.new_password)
    if check_password(body.new_password,r.data()['password_hash']):raise HTTPException(422,'Choose a different password.')
    update(s,r,{'password_hash':password_hash(body.new_password),'must_change_password':False},r.version)
    s.execute(delete(SessionRecord).where(SessionRecord.user_id==r.id));audit(s,user,r,'account.password_changed');s.commit()
    return {'ok':True,'sign_in_required':True}

class PasswordReset(BaseModel):
    expected_version:int=Field(ge=1)
    temporary_password:str=Field(min_length=12,max_length=200)
@app.post('/api/v1/accounts/{id}/reset-password')
def reset_password(id:str,body:PasswordReset,user=Depends(current),s=Depends(db)):
    require(user,'administrator')
    r=get(s,'users',id,user)
    if r.id==user['id']:raise HTTPException(422,'Use your profile to change your own password.')
    strong_password(body.temporary_password)
    update(s,r,{'password_hash':password_hash(body.temporary_password),'must_change_password':True},body.expected_version)
    s.execute(delete(SessionRecord).where(SessionRecord.user_id==r.id));audit(s,user,r,'account.password_reset');s.commit();return clean(r)

KINDS={'sources','collection-runs','content','claims','cases','narratives','evidence-sources','documents','assessments','responses','actions','follow-ups','alerts','reports','audit','users','institutions','jobs','annotations','evaluations','settings','decisions'}
CREATE_ROLES={'sources':['administrator'],'evidence-sources':['scientific_reviewer'],'documents':['scientific_reviewer'],'cases':['analyst'],'claims':['analyst'],'narratives':['analyst'],'responses':['communication_editor'],'annotations':['analyst','scientific_reviewer'],'evaluations':['scientific_reviewer'],'decisions':['administrator'],'reports':['analyst','institutional_approver']}
EDIT_FIELDS={'cases':{'owner','reviewer','due_at','status','topic','priority','priority_rationale','harm'},'sources':{'name','url','permission','languages','owner','retention_days'},'evidence-sources':{'name','organization','permission','scope'},'documents':{'title','review_date'},'narratives':{'title','rationale','state'},'annotations':{'label','rationale','uncertainty'},'decisions':{'title','owner','state','rationale','due_at'},'settings':{'raw_retention_hours','redacted_retention_days','default_locale','default_timezone'},'users':{'active'},'follow-ups':{'state','baseline_count','observed_count','coverage_comparable','limitations','interpretation'},'alerts':{'state','owner','rationale'}}
EDIT_ROLES={'cases':['analyst'],'sources':['administrator'],'evidence-sources':['scientific_reviewer'],'documents':['scientific_reviewer'],'narratives':['analyst'],'annotations':['analyst','scientific_reviewer'],'decisions':['administrator'],'settings':['administrator'],'users':['administrator'],'follow-ups':['analyst'],'alerts':['analyst']}
class Create(BaseModel):
    data:dict[str,Any]
class Mutation(BaseModel):
    expected_version:int=Field(ge=1)
    data:dict[str,Any]
def bounded(data):
    if len(json.dumps(data))>200000:raise HTTPException(422,'Record exceeds the size limit.')
def validate_values(kind,data):
    if 'priority' in data and (not isinstance(data['priority'],(int,float)) or not 0<=data['priority']<=100):raise HTTPException(422,'Priority must be between 0 and 100.')
    for field in ['raw_retention_hours','redacted_retention_days','retention_days','baseline_count','observed_count']:
        if field in data and data[field] is not None and (not isinstance(data[field],int) or data[field]<0):raise HTTPException(422,field+' must be a non-negative integer.')
    if kind=='follow-ups' and data.get('state')=='completed' and not data.get('interpretation'):raise HTTPException(422,'A completed observation requires interpretation and coverage limits.')
def scope_kind(kind,user):
    if kind not in KINDS:raise HTTPException(404,'Unknown resource.')
    if kind in ('users','settings','institutions'):require(user,'administrator')
    if kind=='audit':require(user,'administrator','scientific_reviewer','institutional_approver','operator')
    if kind in ('jobs','collection-runs'):require(user,'operator','administrator','analyst')

@app.get('/api/v1/overview')
def overview(q:str='',topic:str='',language:str='',days:int=Query(7,ge=1,le=365),user=Depends(current),s=Depends(db)):
    cases=[r.data() for r in rows(s,'cases',user) if (not q or q.casefold() in r.payload.casefold()) and (not topic or r.data().get('topic')==topic) and (not language or r.data().get('language')==language)]
    ids={x['id'] for x in cases};cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    def observed_at(item):return item.get('published_at') or item.get('collected_at') or item['created_at']
    all_content=[r.data() for r in rows(s,'content',user) if (not q or q.casefold() in r.payload.casefold()) and (not topic or r.data().get('topic')==topic) and (not language or r.data().get('language')==language)]
    content=[item for item in all_content if cutoff<=observed_at(item)<=now()]
    trend=Counter(observed_at(x)[:10] for x in content)
    jobs=[r.data() for r in rows(s,'jobs',user)];sources=[r.data() for r in rows(s,'sources',user)]
    worker=s.get(WorkerStatus,'polling');worker_alive=bool(worker and worker.state=='running' and worker.last_seen>=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat())
    connections={'api':'connected','database':'connected','worker':'connected' if worker_alive else 'not_responding','worker_last_seen':worker.last_seen if worker else None,'checked_at':now(),'queued':sum(j['state']=='queued' for j in jobs),'running':sum(j['state']=='running' for j in jobs),'failed':sum(j['state']=='failed' for j in jobs),'last_collection_at':max((source['last_success'] for source in sources if source.get('last_success')),default=None)}
    live={'total_collected':len(all_content),'live_publications':sum(not x.get('synthetic',False) and x.get('content_type') in ('institutional_news','rss_publication') for x in all_content),'connected_feeds':sum(x.get('platform')=='rss' and x.get('enabled',False) and bool(x.get('last_success')) for x in sources),'connections':connections,'latest_publications':sorted(content,key=observed_at,reverse=True)[:8],'recent_collections':sorted((r.data() for r in rows(s,'collection-runs',user)),key=lambda x:x['created_at'],reverse=True)[:5],'undated_items':sum(not x.get('published_at') for x in all_content),'catalog_available':ENV=='local' and user['role']=='administrator'}
    return {**live,'mode':ENV,'items':len(content),'cases':len(cases),'needs_review':sum(x.data()['review_status']!='confirmed' for x in rows(s,'assessments',user) if x.data().get('case_id') in ids),'approved_responses':sum(x.data()['state']=='approved' for x in rows(s,'responses',user) if x.data().get('case_id') in ids),'high_priority':sum(x.get('priority',0)>=70 for x in cases),'trend':[{'date':k,'count':v} for k,v in sorted(trend.items())],'topics':dict(Counter(x.get('topic','Unknown') for x in content)),'languages':dict(Counter(x.get('language','unknown') for x in content)),'queue':sorted(cases,key=lambda x:x.get('priority',0),reverse=True)[:5],'sources':[r.data() for r in rows(s,'sources',user)],'coverage':('Selected authorized local imports and enabled RSS sources. Geography unknown. Counts are collected items, not people reached.' if ENV=='local' else 'Selected synthetic imports. No live platform coverage. Geography unknown. Counts are collected items, not people reached.'),'timezone':'Africa/Tunis'}

@app.get('/api/v1/cases/{id}/timeline')
def timeline(id:str,user=Depends(current),s=Depends(db)):
    get(s,'cases',id,user)
    entities={id}
    for kind in ['claims','assessments','responses','actions','follow-ups']:
        entities.update(r.id for r in rows(s,kind,user) if r.data().get('case_id')==id)
    return {'items':[{'id':e.id,'action':e.action,'actor':e.actor,'created_at':e.created_at,'details':json.loads(e.payload)} for e in s.scalars(select(Event).where(Event.institution==user['institution'],Event.entity_id.in_(entities)).order_by(Event.created_at.desc()))]}

@app.patch('/api/v1/{kind}/{id}')
def edit_record(kind:str,id:str,body:Mutation,user=Depends(current),s=Depends(db)):
    if kind not in EDIT_ROLES:raise HTTPException(403,'This resource requires a dedicated versioned workflow operation.')
    require(user,*EDIT_ROLES[kind]);r=get(s,kind,id,user);bounded(body.data)
    validate_values(kind,body.data)
    if not set(body.data)<=EDIT_FIELDS[kind]:raise HTTPException(422,'Protected or unknown fields cannot be changed here.')
    if kind=='users' and id==user['id'] and body.data.get('active') is False:
        raise HTTPException(422,'You cannot deactivate your own administrator account.')
    if kind=='sources' and r.data().get('enabled'):raise HTTPException(422,'Disable the source before changing configuration.')
    if kind=='narratives' and body.data.get('state') not in (None,'proposed','confirmed'):raise HTTPException(422,'Invalid narrative state.')
    if kind=='users' and id==user['id']:raise HTTPException(422,'You cannot deactivate your own account.')
    if kind=='alerts' and body.data.get('state') not in (None,'open','acknowledged','escalated','closed'):raise HTTPException(422,'Invalid alert state.')
    if kind=='follow-ups' and body.data.get('state') not in (None,'pending','completed'):raise HTTPException(422,'Invalid follow-up state.')
    before=r.data();update(s,r,body.data,body.expected_version);audit(s,user,r,kind+'.updated',before);s.commit();return clean(r)

def validate_evidence(s,a,user):
    for link in a.data().get('evidence_links',[]):
        d=get(s,'documents',link['document_id'],user)
        source=get(s,'evidence-sources',d.data()['source_id'],user)
        if d.data()['state']!='approved' or source.data()['state']!='approved' or d.version!=link['document_version']:raise HTTPException(422,'Cited evidence is stale or not approved. Scientific re-review is required.')
        if not any(p['id']==link['passage_id'] for p in d.data()['passages']):raise HTTPException(422,'Citation does not resolve to a stored passage.')
def invalidate_case(s,case_id,user):
    for a in rows(s,'assessments',user):
        if a.data().get('case_id')==case_id:
            before=a.data();update(s,a,{'review_status':'stale','reviewer_id':None},a.version);audit(s,user,a,'assessment.invalidated',before)
    for r in rows(s,'responses',user):
        if r.data().get('case_id')==case_id:
            before=r.data();update(s,r,{'state':'changes_requested','approval':None,'scientific_review':None,'language_review':None},r.version);audit(s,user,r,'response.invalidated',before)

class Review(BaseModel):
    expected_version:int=Field(ge=1)
    decision:str
    rationale:str=Field(min_length=5,max_length=10000)
    evidence_links:list[dict[str,Any]]|None=None

STATUSES={'supported','contradicted','misleading','insufficient_evidence','conflicting_evidence','not_factual','unassessed'}
@app.post('/api/v1/assessments/{id}/review')
def review_assessment(id:str,body:Review,user=Depends(current),s=Depends(db)):
    require(user,'scientific_reviewer');r=get(s,'assessments',id,user)
    if body.decision not in STATUSES-{'unassessed'}:raise HTTPException(422,'Choose a valid assessment status.')
    links=body.evidence_links if body.evidence_links is not None else r.data()['evidence_links']
    if body.decision in ('supported','contradicted','misleading','conflicting_evidence') and not links:raise HTTPException(422,'A substantive factual conclusion requires approved evidence passages.')
    if body.decision=='supported' and not any(l.get('relation')=='supports' for l in links):raise HTTPException(422,'Supported conclusions require supporting evidence.')
    if body.decision=='contradicted' and not any(l.get('relation')=='contradicts' for l in links):raise HTTPException(422,'Contradicted conclusions require contradicting evidence.')
    for link in links:
        if link.get('relation') not in ('supports','contradicts','context'):raise HTTPException(422,'Invalid evidence relationship.')
        d=get(s,'documents',link.get('document_id',''),user)
        if d.version!=link.get('document_version') or d.data()['state']!='approved' or not any(p['id']==link.get('passage_id') for p in d.data()['passages']):raise HTTPException(422,'Evidence version or passage is unavailable.')
        if get(s,'evidence-sources',d.data()['source_id'],user).data()['state']!='approved':raise HTTPException(422,'Evidence source is not approved.')
    before=r.data();update(s,r,{'proposed_status':body.decision,'review_status':'confirmed','rationale':body.rationale,'evidence_links':links,'reviewer_id':user['id'],'reviewed_at':now()},body.expected_version)
    for response in rows(s,'responses',user):
        if response.data().get('assessment_id')==r.id:
            old=response.data();update(s,response,{'state':'changes_requested','approval':None,'scientific_review':None,'language_review':None},response.version);audit(s,user,response,'response.assessment_changed',old)
    case=get(s,'cases',r.data()['case_id'],user);update(s,case,{'evidence_status':body.decision,'status':'assessed'},case.version)
    audit(s,user,r,'assessment.reviewed',before);s.commit();return r.data()

@app.post('/api/v1/{kind}/{id}/review')
def registry_review(kind:str,id:str,body:Review,user=Depends(current),s=Depends(db)):
    if kind not in ('documents','evidence-sources','reports'):raise HTTPException(404,'Review operation unavailable.')
    require(user,'institutional_approver' if kind=='reports' else 'scientific_reviewer')
    if body.decision not in ('approved','suspended','withdrawn','changes_requested'):raise HTTPException(422,'Invalid review decision.')
    r=get(s,kind,id,user)
    if body.decision=='approved' and kind!='reports' and not r.data().get('permission'):raise HTTPException(422,'Documented storage/access permission is required.')
    before=r.data();update(s,r,{'state':body.decision,'reviewer':user['name'],'reviewed_at':now(),'review_rationale':body.rationale},body.expected_version);audit(s,user,r,kind+'.reviewed',before)
    if kind in ('documents','evidence-sources'):
        affected=[]
        for a in rows(s,'assessments',user):
            for l in a.data().get('evidence_links',[]):
                d=get(s,'documents',l['document_id'],user)
                if (kind=='documents' and d.id==id) or (kind=='evidence-sources' and d.data()['source_id']==id):affected.append(a.data()['case_id'])
        for case_id in set(affected):invalidate_case(s,case_id,user)
    s.commit();return r.data()

def draft_body(a,locale):
    status=a['proposed_status'];uncertain=status in ('insufficient_evidence','conflicting_evidence','not_factual')
    lead={'fr':'Les éléments disponibles restent insuffisants pour conclure.' if uncertain else 'Voici les éléments examinés par la revue scientifique.','en':'Available evidence does not allow a definitive conclusion.' if uncertain else 'Here is the information examined during scientific review.','ar':'الأدلة المتاحة لا تسمح باستنتاج نهائي.' if uncertain else 'هذه المعلومات التي تم فحصها خلال المراجعة العلمية.','derja':'المعطيات الموجودة ما تكفيش باش نعطيو نتيجة نهائية.' if uncertain else 'هاذي المعطيات اللي تراجعت علمياً.'}.get(locale,'Available evidence requires review.')
    note=('Démonstration synthétique · texte à réviser. Aucune recommandation médicale.' if locale=='fr' else 'Synthetic training draft. Language review required. No medical recommendation.') if a.get('synthetic') else {'fr':'Brouillon à vérifier. Validation scientifique, linguistique et institutionnelle requise avant diffusion.','ar':'مسودة تتطلب مراجعة علمية ولغوية ومؤسسية قبل النشر.'}.get(locale,'Draft requires scientific, language and institutional approval before distribution.')
    return lead+'\n\n'+a['rationale']+'\n\n'+note
class ResponseEdit(BaseModel):
    expected_version:int=Field(ge=1)
    body:str=Field(min_length=5,max_length=20000)
    locale:Literal['fr','en','ar','derja','derja-latin']='fr'
    channel:str=Field(max_length=100,default='FAQ')
@app.put('/api/v1/responses/{id}')
def edit_response(id:str,body:ResponseEdit,user=Depends(current),s=Depends(db)):
    require(user,'communication_editor');r=get(s,'responses',id,user)
    a=get(s,'assessments',r.data()['assessment_id'],user)
    if a.data()['review_status']!='confirmed':raise HTTPException(422,'Scientific re-review is required before editing this response.')
    before=r.data();update(s,r,{'body':body.body,'locale':body.locale,'channel':body.channel,'state':'draft','assessment_version':a.version,'approval':None,'scientific_review':None,'language_review':None},body.expected_version);audit(s,user,r,'response.revised',before);s.commit();return r.data()
@app.post('/api/v1/responses/{id}/approve')
def approve_response(id:str,body:Review,user=Depends(current),s=Depends(db)):
    r=get(s,'responses',id,user);d=r.data();a=get(s,'assessments',d['assessment_id'],user)
    if a.data()['review_status']!='confirmed' or a.version!=d['assessment_version']:raise HTTPException(422,'Assessment changed or requires review.')
    validate_evidence(s,a,user)
    before=d
    if body.decision=='request_review':
        require(user,'communication_editor')
        if d['state'] not in ('draft','changes_requested'):raise HTTPException(422,'Response is already under review.')
        values={'state':'scientific_review'}
    elif body.decision=='scientific':
        require(user,'scientific_reviewer')
        if d['state']!='scientific_review':raise HTTPException(422,'Response is not awaiting scientific review.')
        values={'state':'language_review','scientific_review':{'user_id':user['id'],'at':now(),'rationale':body.rationale}}
    elif body.decision=='language':
        require(user,'communication_editor')
        if d['state']!='language_review':raise HTTPException(422,'Response is not awaiting language review.')
        values={'state':'institutional_review','language_review':{'user_id':user['id'],'at':now(),'rationale':body.rationale}}
    elif body.decision=='institutional':
        require(user,'institutional_approver')
        if d['state']!='institutional_review' or not d.get('scientific_review') or not d.get('language_review'):raise HTTPException(422,'Scientific and language reviews are required.')
        if d['scientific_review']['user_id']==user['id']:raise HTTPException(422,'Independent institutional approval is required.')
        snapshot=hashlib.sha256(json.dumps(a.data()['evidence_links'],sort_keys=True).encode()).hexdigest()
        values={'state':'approved','approval':{'id':uid(),'approver_id':user['id'],'role':user['role'],'exact_version':r.version+1,'assessment_id':a.id,'assessment_version':a.version,'evidence_snapshot_hash':snapshot,'body_hash':hashlib.sha256(d['body'].encode()).hexdigest(),'at':now(),'rationale':body.rationale}}
    elif body.decision=='reject':
        require(user,'scientific_reviewer','communication_editor','institutional_approver');values={'state':'changes_requested','approval':None,'reason':body.rationale,'scientific_review':None,'language_review':None}
    else:raise HTTPException(422,'Invalid review stage.')
    update(s,r,values,body.expected_version);audit(s,user,r,'response.'+body.decision,before);s.commit();return r.data()

class ActionCreate(BaseModel):
    response_id:str
    expected_version:int=Field(ge=1)
    channel:str=Field(min_length=2,max_length=100)
    performed_at:datetime
    reference:str|None=Field(default=None,max_length=500)
@app.post('/api/v1/actions/record')
def record_action(body:ActionCreate,idempotency_key:str=Header(min_length=8,max_length=150),user=Depends(current),s=Depends(db)):
    require(user,'institutional_approver','communication_editor')
    key=hashlib.sha256((user['institution']+'action'+idempotency_key).encode()).hexdigest()
    prior=s.get(RetryKey,key)
    if prior:return get(s,'actions',prior.result_id,user).data()
    r=get(s,'responses',body.response_id,user);d=r.data()
    if r.version!=body.expected_version:raise HTTPException(409,'Response version changed.')
    if d['state']!='approved' or not d.get('approval') or d['approval']['exact_version']!=r.version:raise HTTPException(422,'An approved exact response version is required.')
    a=get(s,'assessments',d['assessment_id'],user)
    if a.version!=d['assessment_version'] or a.data()['review_status']!='confirmed':raise HTTPException(422,'Assessment is stale.')
    validate_evidence(s,a,user)
    performed=body.performed_at
    if performed.tzinfo is None:raise HTTPException(422,'Publication timestamp needs a timezone.')
    if performed>datetime.now(timezone.utc)+timedelta(minutes=1):raise HTTPException(422,'An action must already have occurred.')
    action=add(s,'actions',user['institution'],{'case_id':d['case_id'],'response_id':r.id,'approved_variant_version':r.version,'body':d['body'],'locale':d['locale'],'approval':d['approval'],'channel':body.channel,'performed_at':performed.astimezone(timezone.utc).isoformat(),'actor_id':user['id'],'actor':user['name'],'reference':body.reference,'synthetic':ENV=='demo'})
    for hours in [48,168,720]:
        add(s,'follow-ups',user['institution'],{'case_id':d['case_id'],'action_id':action.id,'window_hours':hours,'due_at':(performed+timedelta(hours=hours)).isoformat(),'state':'pending','coverage_comparable':None,'baseline_count':None,'observed_count':None,'limitations':'Source coverage must be checked; changes do not establish causality.','synthetic':ENV=='demo'})
    s.add(RetryKey(key=key,institution=user['institution'],operation='action',result_id=action.id));audit(s,user,action,'action.recorded');s.commit();return action.data()

def redact(text):
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email redacted]',text)
    text=re.sub(r'(?<!\w)@[\w.]+','[handle redacted]',text)
    text=re.sub(r'(?<!\w)(?:\+?\d[\d ()-]{6,}\d)(?!\w)','[phone redacted]',text)
    return text
class ImportBatch(BaseModel):
    source_id:str
    permission:str=Field(min_length=10,max_length=2000)
    items:list[dict[str,Any]]=Field(min_length=1,max_length=500)
    preview:bool=True
@app.post('/api/v1/imports')
def imports(body:ImportBatch,idempotency_key:str=Header(default=''),user=Depends(current),s=Depends(db)):
    require(user,'analyst');source=get(s,'sources',body.source_id,user)
    if source.data().get('platform')!='manual':raise HTTPException(422,'Select a manual import source.')
    errors=[];valid=[]
    for i,item in enumerate(body.items):
        text=item.get('text','')
        if not isinstance(text,str) or not text.strip() or len(text)>20000:errors.append({'row':i+1,'message':'Text must contain 1–20000 characters.'});continue
        if item.get('language','unknown') not in ('fr','en','ar','derja','derja-latin','mixed','unknown'):errors.append({'row':i+1,'message':'Unsupported language code.'});continue
        try:
            date=datetime.fromisoformat(item.get('published_at',now()).replace('Z','+00:00'))
            if date.tzinfo is None:raise ValueError()
        except (ValueError,TypeError):errors.append({'row':i+1,'message':'published_at requires an ISO timestamp with timezone.'});continue
        text=redact(text)
        # Missing publication dates must not turn the same file into new items on every retry.
        identity=json.dumps([text,date.astimezone(timezone.utc).isoformat() if item.get('published_at') else None,item.get('language','unknown'),item.get('topic','À classer')],ensure_ascii=False)
        valid.append({'text':text,'original_text':text,'source_id':source.id,'source_name':source.data()['name'],'language':item.get('language','unknown'),'topic':item.get('topic','À classer'),'published_at':date.astimezone(timezone.utc).isoformat(),'publication_date_known':bool(item.get('published_at')),'platform_item_id':hashlib.sha256(identity.encode()).hexdigest(),'geography':'unknown','redacted':True,'permission':body.permission,'synthetic':ENV=='demo'})
    if body.preview:return {'preview':valid,'errors':errors,'redaction_note':'Automatic redaction is a first pass. Review names and residual identifying context before committing.'}
    if errors:raise HTTPException(422,json.dumps(errors))
    if len(idempotency_key)<8:raise HTTPException(422,'An Idempotency-Key is required.')
    key=hashlib.sha256((user['institution']+'import'+idempotency_key).encode()).hexdigest()
    prior=s.get(RetryKey,key)
    if prior:return get(s,'collection-runs',prior.result_id,user).data()
    existing={x.data().get('platform_item_id') for x in rows(s,'content',user) if x.data().get('source_id')==source.id};count=0
    for item in valid:
        if item['platform_item_id'] not in existing:
            r=add(s,'content',user['institution'],item);audit(s,user,r,'content.imported');existing.add(item['platform_item_id']);count+=1
    run=add(s,'collection-runs',user['institution'],{'source_id':source.id,'state':'succeeded','count':count,'duplicates':len(valid)-count,'permission':body.permission,'watermark':now(),'synthetic':ENV=='demo'})
    s.add(RetryKey(key=key,institution=user['institution'],operation='import',result_id=run.id));update(s,source,{'last_success':now()},source.version);audit(s,user,run,'import.completed');s.commit();return run.data()

class FromContent(BaseModel):
    title:str=Field(min_length=5,max_length=2000)
@app.post('/api/v1/content/{id}/case')
def content_case(id:str,body:FromContent,user=Depends(current),s=Depends(db)):
    require(user,'analyst');item=get(s,'content',id,user)
    if item.data().get('case_id'):return get(s,'cases',item.data()['case_id'],user).data()
    case=add(s,'cases',user['institution'],{'title':body.title,'original_text':item.data()['text'],'language':item.data()['language'],'topic':item.data()['topic'],'code':'C-'+uid()[:6].upper(),'owner':user['name'],'status':'new','evidence_status':'unassessed','priority':0,'completeness':25,'priority_rationale':'Manual harm assessment needed; no automatic verdict.','synthetic':ENV=='demo'})
    claim=add(s,'claims',user['institution'],{'case_id':case.id,'original_text':item.data()['text'],'neutral_text':body.title,'language':item.data()['language'],'topic':item.data()['topic'],'claim_type':'question' if '?' in item.data()['text'] else 'assertion','synthetic':ENV=='demo'})
    update(s,item,{'case_id':case.id},item.version);audit(s,user,case,'case.created_from_content');s.commit();return case.data()

@app.post('/api/v1/claims/{id}/verify',status_code=202)
def verify(id:str,user=Depends(current),s=Depends(db)):
    require(user,'analyst','scientific_reviewer');claim=get(s,'claims',id,user)
    existing=next((r for r in rows(s,'jobs',user) if r.data().get('claim_id')==id and r.data()['state'] in ('queued','running')),None)
    if existing:return existing.data()
    job=add(s,'jobs',user['institution'],{'title':'Evidence retrieval · '+claim.data()['neutral_text'][:80],'type':'verify','claim_id':id,'case_id':claim.data()['case_id'],'state':'queued','progress':0,'attempts':0,'requested_by':user['id'],'synthetic':ENV=='demo'});audit(s,user,job,'verification.queued');s.commit();return job.data()

@app.post('/api/v1/jobs/{id}/retry')
def retry_job(id:str,user=Depends(current),s=Depends(db)):
    require(user,'operator');r=get(s,'jobs',id,user)
    if r.data()['state']!='failed':raise HTTPException(422,'Only failed jobs can be retried.')
    update(s,r,{'state':'queued','error':None},r.version);audit(s,user,r,'job.retried');s.commit();return r.data()

@app.get('/api/v1/reports/{id}/export')
def export_report(id:str,format:Literal['json','csv','pdf']='json',user=Depends(current),s=Depends(db)):
    r=get(s,'reports',id,user)
    if r.data()['state']!='approved':raise HTTPException(422,'Report requires institutional approval before export.')
    snapshot=r.data()['snapshot'];audit(s,user,r,'report.exported');s.commit()
    if format=='pdf':
        from .reports import render_pdf
        try:content=render_pdf(r.data())
        except ValueError as exc:raise HTTPException(503,str(exc))
        return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="pnsi-report-{id[:8]}.pdf"'})
    if format=='json':return Response(json.dumps(r.data(),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="pnsi-report-{id[:8]}.json"'})
    buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['case','claim','evidence_status','priority','coverage'])
    def safe(v):
        v=str(v);return "'"+v if v.lstrip().startswith(('=','+','-','@')) else v
    for case in snapshot['queue']:writer.writerow([safe(case.get(k,'')) for k in ('code','title','evidence_status','priority')]+[safe(r.data()['coverage'])])
    return Response('\ufeff'+buf.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="pnsi-report-{id[:8]}.csv"'})

@app.post('/api/v1/sources/{id}/enable')
def enable_source(id:str,body:Review,user=Depends(current),s=Depends(db)):
    require(user,'administrator');r=get(s,'sources',id,user);d=r.data()
    if body.decision not in ('enable','disable'):raise HTTPException(422,'Choose enable or disable.')
    if body.decision=='enable':
        if not d.get('permission') or not d.get('url'):raise HTTPException(422,'Exact feed URL and documented access permission required.')
        if d.get('platform')!='rss':raise HTTPException(422,'This connector is not implemented. Use authorized imports or RSS.')
        from .connectors import validate_url
        validate_url(d['url'])
    before=r.data();update(s,r,{'enabled':body.decision=='enable','state':'ready' if body.decision=='enable' else 'disabled','permission_reviewed_by':user['id']},body.expected_version);audit(s,user,r,'source.'+body.decision,before);s.commit();return r.data()
@app.post('/api/v1/sources/{id}/collect',status_code=202)
def collect(id:str,user=Depends(current),s=Depends(db)):
    require(user,'operator','administrator');source=get(s,'sources',id,user)
    if not source.data().get('enabled') or source.data().get('platform')!='rss':raise HTTPException(422,'An enabled permitted RSS source is required.')
    job=queue_collection(s,source,user);s.commit();return job.data()

def queue_collection(s,source,user):
    prior=next((r for r in rows(s,'jobs',user) if r.data().get('source_id')==source.id and r.data()['state'] in ('queued','running')),None)
    if prior:return prior
    job=add(s,'jobs',user['institution'],{'title':'RSS · '+source.data()['name'],'type':'rss','source_id':source.id,'state':'queued','progress':0,'attempts':0,'requested_by':user['id']});audit(s,user,job,'collection.queued');return job

class PublicConnect(BaseModel):
    keys:list[Literal['ecdc-news','ecdc-updates','ecdc-threats']]=Field(min_length=1,max_length=3)
@app.post('/api/v1/connectors/public',status_code=202)
def connect_public(body:PublicConnect,user=Depends(current),s=Depends(db)):
    require(user,'administrator')
    if ENV!='local':raise HTTPException(403,'Connect live feeds in your separate local installation.')
    from .public_sources import source_config
    from .connectors import validate_url
    configs=[source_config(key) for key in dict.fromkeys(body.keys)]
    for config in configs:validate_url(config['url'])
    result=[]
    for config in configs:
        source=next((r for r in rows(s,'sources',user) if r.data().get('url')==config['url']),None)
        if source and not source.data().get('enabled'):raise HTTPException(409,'Re-enable the existing source before connecting it again.')
        if not source:
            source=add(s,'sources',user['institution'],dict(config,owner=user['name'],permission_reviewed_by=user['id']))
            audit(s,user,source,'source.public_feed_connected')
        job=queue_collection(s,source,user);result.append({'source_id':source.id,'job_id':job.id})
    s.commit();return {'items':result,'message':'Collection queued. Results appear after a successful external response.'}

@app.delete('/api/v1/content/{id}')
def delete_content(id:str,body:Review,user=Depends(current),s=Depends(db)):
    require(user,'administrator');r=get(s,'content',id,user)
    if r.version!=body.expected_version:raise HTTPException(409,'Content version changed.')
    case_id=r.data().get('case_id')
    source_text=r.data().get('original_text',r.data().get('text',''))
    def scrub(value):
        if isinstance(value,str):return value.replace(source_text,'[Removed source content]') if source_text else value
        if isinstance(value,list):return [scrub(v) for v in value]
        if isinstance(value,dict):return {k:scrub(v) for k,v in value.items()}
        return value
    # Redact the object and audit payload; report snapshots contain aggregates only.
    for e in s.scalars(select(Event).where(Event.institution==user['institution'])):
        e.payload=json.dumps(scrub(json.loads(e.payload)),ensure_ascii=False)
        if id in e.payload:e.payload=json.dumps({'deleted_content_id':id,'reason':'Retention/deletion propagation'})
    for historical in s.scalars(select(RecordVersion).where(RecordVersion.institution==user['institution'])):
        historical.payload=json.dumps(scrub(json.loads(historical.payload)),ensure_ascii=False)
    for derived in rows(s,'reports',user):
        old=derived.data();new=scrub(old)
        if new!=old:
            update(s,derived,{'snapshot':new['snapshot'],'state':'withdrawn','privacy_redacted_at':now(),'privacy_rationale':'Source deletion propagated; create a fresh reviewed snapshot.'},derived.version)
            audit(s,user,derived,'report.privacy_redacted')
    if case_id:
        case=get(s,'cases',case_id,user);update(s,case,{'original_text':'[Source content removed]','title':scrub(case.data()['title'])},case.version);invalidate_case(s,case_id,user)
        for claim in rows(s,'claims',user):
            if claim.data().get('case_id')==case_id:update(s,claim,{'original_text':'[Source content removed]','neutral_text':scrub(claim.data()['neutral_text'])},claim.version)
        for kind in ['assessments','responses','actions','annotations']:
            for derived in rows(s,kind,user):
                old=derived.data();new=scrub(old)
                if new!=old:update(s,derived,new,derived.version)
    s.execute(delete(RecordVersion).where(RecordVersion.entity_id==id,RecordVersion.institution==user['institution']))
    tombstone=add(s,'decisions',user['institution'],{'title':'Source deletion','entity_id':id,'rationale':body.rationale,'state':'completed'});audit(s,user,tombstone,'content.deleted');s.delete(r);s.commit();return {'ok':True}

@app.put('/api/v1/profile')
def profile(body:Create,user=Depends(current),s=Depends(db)):
    d=body.data
    if not set(d)<= {'locale','timezone'}:raise HTTPException(422,'Only locale and timezone can be updated.')
    if d.get('locale','fr') not in ('fr','en','ar','derja','derja-latin'):raise HTTPException(422,'Invalid locale.')
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    try:ZoneInfo(d.get('timezone','Africa/Tunis'))
    except ZoneInfoNotFoundError:raise HTTPException(422,'Unknown timezone.')
    r=get(s,'users',user['id'],user);update(s,r,d,r.version);audit(s,user,r,'profile.updated');s.commit();return clean(r)

@app.post('/api/v1/{kind}')
def create_record(kind:str,body:Create,user=Depends(current),s=Depends(db)):
    if kind not in CREATE_ROLES:raise HTTPException(403,'Use the dedicated workflow operation for this resource.')
    require(user,*CREATE_ROLES[kind]);bounded(body.data)
    validate_values(kind,body.data)
    d={k:v for k,v in body.data.items() if k not in ('id','institution','version','state','approval','password_hash')}
    d['synthetic']=ENV=='demo'
    if kind=='claims':
        get(s,'cases',d.get('case_id',''),user)
        if not d.get('original_text') or not d.get('neutral_text'):raise HTTPException(422,'Original and neutral claim text are required.')
    if kind=='annotations':
        if d.get('label') not in STATUSES:raise HTTPException(422,'Choose a valid annotation label.')
        d.update(annotator_id=user['id'],review_state='pending')
    if kind=='cases':
        if not d.get('title'):raise HTTPException(422,'Claim wording is required.')
        d.update(status='new',evidence_status='unassessed',code='C-'+uid()[:6].upper(),owner=user['name'],priority=d.get('priority',0),completeness=25)
    if kind in ('sources','evidence-sources','documents'):d.update(state='pending',enabled=False)
    if kind=='sources':d['platform']='rss';d['last_success']=None
    if kind=='documents':
        ev=get(s,'evidence-sources',d.get('source_id',''),user)
        if ev.data()['state']!='approved':raise HTTPException(422,'Evidence source must be approved.')
        if not d.get('passages') or not d.get('permission') or not d.get('effective_date'):raise HTTPException(422,'Passages, effective date and storage permission are required.')
        for p in d['passages']:
            p['id']=uid()
            if not p.get('text') or not p.get('page'):raise HTTPException(422,'Each passage needs text and page.')
        d['checksum']=hashlib.sha256(json.dumps(d['passages']).encode()).hexdigest()
    if kind=='responses':
        case=get(s,'cases',d.get('case_id',''),user)
        assessment=get(s,'assessments',d.get('assessment_id',''),user)
        if assessment.data().get('case_id')!=case.id or assessment.data()['review_status']!='confirmed':raise HTTPException(422,'A confirmed current assessment is required.')
        validate_evidence(s,assessment,user)
        d.update(state='draft',assessment_version=assessment.version,body=d.get('body') or draft_body(assessment.data(),d.get('locale','fr')),locale=d.get('locale','fr'),script=d.get('script','latin'),channel=d.get('channel','FAQ'),citation_ids=[l['passage_id'] for l in assessment.data()['evidence_links']],approval=None,scientific_review=None,language_review=None,generated_by='deterministic-reviewed-assessment-template-v1')
    if kind=='reports':
        snapshot=overview(user=user,s=s,days=7)
        snapshot['queue']=[r.data() for r in rows(s,'cases',user)]
        snapshot['assessments']=[r.data() for r in rows(s,'assessments',user)]
        snapshot['responses']=[r.data() for r in rows(s,'responses',user) if r.data()['state']=='approved']
        snapshot['actions']=[r.data() for r in rows(s,'actions',user)]
        snapshot['follow_ups']=[r.data() for r in rows(s,'follow-ups',user)]
        d.update(state='draft',snapshot=snapshot,cutoff=now(),coverage='Selected collected items; no population or causal inference.')
    r=add(s,kind,user['institution'],d)
    if kind=='cases':
        add(s,'claims',user['institution'],{'case_id':r.id,'original_text':d.get('original_text',d['title']),'neutral_text':d['title'],'language':d.get('language','unknown'),'topic':d.get('topic','À classer'),'claim_type':'assertion','synthetic':ENV=='demo'})
    audit(s,user,r,kind+'.created');s.commit();return clean(r)



@app.get('/api/v1/system/capabilities')
def capabilities(user=Depends(current)):
    from .ai import capability
    return {'mode':ENV,'inference':capability(),'auto_publish':False,'storage':'manual passages; file uploads unavailable','queue':'durable single worker','identity':'local accounts with revocable sessions' if ENV=='local' else 'development sessions; production blocked'}

@app.get('/api/v1/versions/{kind}/{id}')
def versions(kind:str,id:str,user=Depends(current),s=Depends(db)):
    scope_kind(kind,user);get(s,kind,id,user)
    return {'items':[json.loads(v.payload) for v in s.scalars(select(RecordVersion).where(RecordVersion.entity_id==id,RecordVersion.institution==user['institution']).order_by(RecordVersion.version.desc()))]}

class CaseAssociation(BaseModel):
    expected_version:int=Field(ge=1)
    case_id:str|None=None
    rationale:str=Field(min_length=5,max_length=5000)
@app.put('/api/v1/content/{id}/association')
def associate(id:str,body:CaseAssociation,user=Depends(current),s=Depends(db)):
    require(user,'analyst');r=get(s,'content',id,user)
    if body.case_id:get(s,'cases',body.case_id,user)
    before=r.data();update(s,r,{'case_id':body.case_id,'association_rationale':body.rationale},body.expected_version);audit(s,user,r,'content.association_changed',before);s.commit();return r.data()

class NarrativeMembership(BaseModel):
    expected_version:int=Field(ge=1)
    case_ids:list[str]=Field(max_length=100)
    rationale:str=Field(min_length=5,max_length=5000)
@app.put('/api/v1/narratives/{id}/members')
def narrative_members(id:str,body:NarrativeMembership,user=Depends(current),s=Depends(db)):
    require(user,'analyst');r=get(s,'narratives',id,user)
    for case_id in body.case_ids:get(s,'cases',case_id,user)
    before=r.data();update(s,r,{'case_ids':list(dict.fromkeys(body.case_ids)),'rationale':body.rationale,'state':'confirmed','confirmed_by':user['id']},body.expected_version);audit(s,user,r,'narrative.members_reviewed',before);s.commit();return r.data()

@app.post('/api/v1/evaluation/freeze')
def freeze_dataset(body:Create,user=Depends(current),s=Depends(db)):
    require(user,'scientific_reviewer')
    annotations=[r.data() for r in rows(s,'annotations',user)]
    if not annotations:raise HTTPException(422,'No annotations exist. Create independent reviewed annotations first.')
    version=body.data.get('dataset_version')
    if not version:raise HTTPException(422,'Dataset version is required.')
    dataset=[a for a in annotations if a.get('dataset_version')==version]
    if not dataset:raise HTTPException(422,'No annotations match this dataset version.')
    # Only reviewer-approved reference labels form a release benchmark.
    if any(a.get('review_state')!='resolved' for a in dataset):raise HTTPException(422,'Resolve independent annotations before freezing the benchmark.')
    d={'title':body.data.get('title','Frozen benchmark'),'dataset_version':version,'state':'frozen','dataset':dataset,'checksum':hashlib.sha256(json.dumps(dataset,sort_keys=True).encode()).hexdigest(),'metrics':None,'release_status':'not_evaluated','rationale':'Frozen reviewed labels. No model performance implied.','synthetic':ENV=='demo'}
    r=add(s,'evaluations',user['institution'],d);audit(s,user,r,'benchmark.frozen');s.commit();return r.data()

class AnnotationResolve(BaseModel):
    expected_version:int=Field(ge=1)
    reference_label:str
    rationale:str=Field(min_length=5,max_length=5000)
@app.post('/api/v1/annotations/{id}/resolve')
def resolve_annotation(id:str,body:AnnotationResolve,user=Depends(current),s=Depends(db)):
    require(user,'scientific_reviewer');r=get(s,'annotations',id,user)
    if body.reference_label not in STATUSES:raise HTTPException(422,'Invalid reference label.')
    if r.data().get('annotator_id')==user['id']:raise HTTPException(422,'An independent reviewer must resolve the label.')
    before=r.data();update(s,r,{'reference_label':body.reference_label,'review_state':'resolved','resolved_by':user['id'],'review_rationale':body.rationale},body.expected_version);audit(s,user,r,'annotation.resolved',before);s.commit();return r.data()

class EvaluationRun(BaseModel):
    expected_version:int=Field(ge=1)
    model_version:str=Field(min_length=2,max_length=200)
    predictions:dict[str,str]
@app.post('/api/v1/evaluations/{id}/measure')
def measure(id:str,body:EvaluationRun,user=Depends(current),s=Depends(db)):
    require(user,'scientific_reviewer');r=get(s,'evaluations',id,user);d=r.data()
    if d['state']!='frozen':raise HTTPException(422,'A frozen dataset is required.')
    dataset=d['dataset']
    if set(body.predictions)!={a['id'] for a in dataset}:raise HTTPException(422,'Predictions must match the entire frozen dataset exactly.')
    if any(x not in STATUSES for x in body.predictions.values()):raise HTTPException(422,'Invalid prediction status.')
    def metrics(items):
        labels=sorted({a['reference_label'] for a in items}|{body.predictions[a['id']] for a in items});table={l:{p:0 for p in labels} for l in labels}
        for a in items:table[a['reference_label']][body.predictions[a['id']]]+=1
        per={}
        for l in labels:
            tp=table[l][l];fp=sum(table[x][l] for x in labels if x!=l);fn=sum(table[l][x] for x in labels if x!=l)
            per[l]={'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'support':sum(table[l].values())}
        return {'sample_size':len(items),'accuracy':sum(table[l][l] for l in labels)/len(items),'per_class':per,'confusion_matrix':table,'calibration':None,'latency':None,'cost':None}
    result={'overall':metrics(dataset),'by_language':{lang:metrics([a for a in dataset if a.get('language','unknown')==lang]) for lang in {a.get('language','unknown') for a in dataset}},'model_version':body.model_version,'dataset_checksum':d['checksum'],'measured_at':now(),'limitations':['Small fixture samples do not establish clinical or national performance.','No release thresholds approved.','Calibration, cost and latency not supplied.']}
    before=d;update(s,r,{'metrics':result,'release_status':'requires_threshold_review'},body.expected_version);audit(s,user,r,'evaluation.measured',before);s.commit();return r.data()

@app.get('/api/v1/{kind}')
def list_records(kind:str,q:str='',topic:str='',language:str='',state:str='',case_id:str='',limit:int=Query(50,ge=1,le=100),cursor:int=Query(0,ge=0),user=Depends(current),s=Depends(db)):
    scope_kind(kind,user)
    if kind=='audit':
        events=s.scalars(select(Event).where(Event.institution==user['institution']).order_by(Event.created_at.desc())).all()
        data=[{'id':e.id,'title':e.action,'action':e.action,'actor':e.actor,'entity_id':e.entity_id,'created_at':e.created_at,'details':json.loads(e.payload)} for e in events if not q or q.casefold() in (e.action+e.actor).casefold()]
    else:
        data=[clean(r) for r in rows(s,kind,user) if (not q or q.casefold() in r.payload.casefold()) and (not topic or r.data().get('topic')==topic) and (not language or r.data().get('language')==language) and (not case_id or r.data().get('case_id')==case_id) and (not state or r.data().get('state',r.data().get('status'))==state)]
    return {'items':data[cursor:cursor+limit],'total':len(data),'next_cursor':cursor+limit if cursor+limit<len(data) else None}
from .social_tracking import register as register_tracking
register_tracking(app,current,db,require,rows,get,lambda:ENV)
from .automatic_tracking import register as register_automatic_tracking
register_automatic_tracking(app,current,db,require,rows,get,lambda:ENV)

@app.get('/api/v1/{kind}/{id}')
def read_record(kind:str,id:str,user=Depends(current),s=Depends(db)):
    scope_kind(kind,user);return clean(get(s,kind,id,user))


