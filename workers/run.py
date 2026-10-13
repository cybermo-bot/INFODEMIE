"""Durable database queue. Restart-safe jobs; one worker for the local pilot build."""
import sys,time,json,hashlib,logging,os,re
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from apps.api.db import Session,Record,WorkerStatus,add,update,audit,now,init
from apps.api.main import redact,invalidate_case
from apps.api.connectors import RSSConnector

def process_one():
    with Session() as s:
        pending=[r for r in s.scalars(select(Record).where(Record.kind=='jobs').order_by(Record.created_at)) if r.data()['state']=='queued']
        if not pending:return False
        job=pending[0];jd=job.data();actor={'name':'PNSI local worker','institution':job.institution};update(s,job,{'state':'running','progress':20,'attempts':jd.get('attempts',0)+1},job.version);s.commit()
        try:
            if jd['type']=='verify':
                claim=s.get(Record,jd['claim_id']);cd=claim.data();tokens=set(re.findall(r'\w+',cd['neutral_text'].lower()));links=[]
                for doc in s.scalars(select(Record).where(Record.kind=='documents',Record.institution==job.institution)):
                    dd=doc.data();source=s.get(Record,dd['source_id'])
                    if dd['state']!='approved' or source.data()['state']!='approved':continue
                    for passage in dd['passages']:
                        words=set(re.findall(r'\w+',passage['text'].lower()));score=len(tokens&words)/max(len(tokens),1)
                        if score>=0.15:links.append({'document_id':doc.id,'document_version':doc.version,'passage_id':passage['id'],'relation':'context','relevance_reason':f'Lexical baseline overlap {score:.2f}; relevance and stance require reviewer confirmation.'})
                for old in s.scalars(select(Record).where(Record.kind=='assessments',Record.institution==job.institution)):
                    if old.data().get('claim_id')==claim.id:
                        invalidate_case(s,cd['case_id'],actor);break
                from apps.api.ai import propose,capability,PROMPT_VERSION
                passages=[]
                for link in links[:12]:
                    doc=s.get(Record,link['document_id'])
                    p=next(p for p in doc.data()['passages'] if p['id']==link['passage_id'])
                    passages.append(dict(link,text=p['text']))
                proposal=propose(cd,passages)
                values=proposal or {'proposed_status':'insufficient_evidence','rationale':'Lexical retrieval baseline completed. No model is configured; no automated factual verdict. Review evidence relevance, currentness and contradictions.','limitations':['Lexical baseline is not evaluated multilingual retrieval.','No calibrated model confidence.'],'evidence_links':links[:12]}
                values.update(case_id=cd['case_id'],claim_id=claim.id,review_status='pending',model_run_id=job.id if proposal else None,provider=capability()['provider'],prompt_version=PROMPT_VERSION,synthetic=os.getenv('APP_ENV','demo')=='demo')
                assessment=add(s,'assessments',job.institution,values)
                audit(s,actor,assessment,'assessment.proposed');result={'assessment_id':assessment.id,'passages':len(links)}
            elif jd['type']=='rss':
                source=s.get(Record,jd['source_id'])
                if not source or source.institution!=job.institution:raise ValueError('Source is unavailable.')
                config=source.data();batch=RSSConnector(config).fetch_batch();s.refresh(source)
                if not source.data().get('enabled') or source.data().get('url')!=config['url']:raise ValueError('Source was disabled or reconfigured during collection.')
                existing=list(s.scalars(select(Record).where(Record.kind=='content',Record.institution==job.institution)));seen={r.data().get('platform_item_id') for r in existing if source.id in r.data().get('source_ids',[r.data().get('source_id')])};by_url={r.data().get('source_url'):r for r in existing if r.data().get('source_url')};count=0;duplicates=0
                for item in batch['records']:
                    article=by_url.get(item.get('source_url'))
                    if item['platform_item_id'] in seen or article:
                        duplicates+=1
                        if article and source.id not in article.data().get('source_ids',[article.data().get('source_id')]):
                            before=article.data();update(s,article,{'source_ids':list(dict.fromkeys([*before.get('source_ids',[before['source_id']]),source.id]))},article.version);audit(s,actor,article,'content.observed_in_source',before)
                        continue
                    item.update(text=redact(item['text']),title=redact(item.get('title','')),summary=redact(item.get('summary','')),source_id=source.id,source_ids=[source.id],source_name=config['name'],topic=config.get('topic','À classer'),redacted=True,geography='unknown',synthetic=False);item['original_text']=item['text'];article=add(s,'content',job.institution,item);audit(s,actor,article,'content.collected');seen.add(item['platform_item_id']);count+=1
                    if item.get('source_url'):by_url[item['source_url']]=article
                collected_at=now();next_poll=(datetime.now(timezone.utc)+timedelta(minutes=config.get('poll_interval_minutes',30))).isoformat()
                run=add(s,'collection-runs',job.institution,{'source_id':source.id,'source_name':config['name'],'state':'succeeded','count':count,'fetched':len(batch['records']),'duplicates':duplicates,'watermark':batch['watermark'],'started_at':jd.get('started_at',job.created_at),'finished_at':collected_at,'feed_url':config['url'],'synthetic':False});audit(s,actor,run,'collection.completed');update(s,source,{'last_success':collected_at,'last_attempt_at':collected_at,'next_poll_at':next_poll,'failure_count':0,'last_count':count,'last_fetched':len(batch['records']),'error':None,'state':'ready'},source.version);result={'run_id':run.id,'count':count,'fetched':len(batch['records']),'duplicates':duplicates}
            else:raise ValueError('Unsupported job type')
            update(s,job,{'state':'succeeded','progress':100,'result':result,'finished_at':now()},job.version);audit(s,actor,job,'job.succeeded');s.commit()
        except Exception as exc:
            s.rollback();job=s.get(Record,job.id);update(s,job,{'state':'failed','error':str(exc)[:300],'finished_at':now()},job.version)
            if jd.get('type')=='rss':
                source=s.get(Record,jd['source_id'])
                if source:
                    failures=source.data().get('failure_count',0)+1
                    update(s,source,{'state':'error','error':str(exc)[:300],'failure_count':failures,'last_attempt_at':now(),'next_poll_at':(datetime.now(timezone.utc)+timedelta(minutes=min(30*2**min(failures,3),240))).isoformat()},source.version)
            audit(s,actor,job,'job.failed');s.commit()
        return True
def recover():
    with Session() as s:
        for job in s.scalars(select(Record).where(Record.kind=='jobs')):
            if job.data()['state']=='running':update(s,job,{'state':'queued','error':'Recovered after worker restart'},job.version)
        s.commit()

def heartbeat(state='running'):
    with Session() as s:
        r=s.get(WorkerStatus,'polling')
        if r:r.last_seen=now();r.state=state
        else:s.add(WorkerStatus(id='polling',last_seen=now(),state=state))
        s.commit()

def schedule_due():
    with Session() as s:
        queued={r.data().get('source_id') for r in s.scalars(select(Record).where(Record.kind=='jobs')) if r.data().get('state') in ('queued','running')}
        count=0
        for source in s.scalars(select(Record).where(Record.kind=='sources')):
            config=source.data()
            if config.get('platform')!='rss' or not config.get('enabled') or not config.get('poll_interval_minutes') or source.id in queued:continue
            if config.get('next_poll_at',now())>now():continue
            actor={'name':'PNSI scheduled collector','institution':source.institution}
            job=add(s,'jobs',source.institution,{'title':'RSS · '+config['name'],'type':'rss','source_id':source.id,'state':'queued','progress':0,'attempts':0,'scheduled':True});audit(s,actor,job,'collection.scheduled');queued.add(source.id);count+=1
        s.commit();return count

if __name__=='__main__':
    init();recover();last_schedule=0
    try:
        while True:
            heartbeat()
            if time.monotonic()-last_schedule>=30:schedule_due();last_schedule=time.monotonic()
            if not process_one():time.sleep(2)
    finally:heartbeat('stopped')
