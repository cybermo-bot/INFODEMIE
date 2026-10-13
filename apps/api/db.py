"""Versioned institution-scoped records; PostgreSQL in deployment, SQLite in local demo."""
import os, json, uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, UniqueConstraint, select, ForeignKey, delete, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
class Base(DeclarativeBase): pass
class Record(Base):
    __tablename__='records'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    institution:Mapped[str]=mapped_column(String(64),index=True)
    kind:Mapped[str]=mapped_column(String(64),index=True)
    version:Mapped[int]=mapped_column(Integer,default=1)
    payload:Mapped[str]=mapped_column(Text)
    created_at:Mapped[str]=mapped_column(String(64),default=now)
    updated_at:Mapped[str]=mapped_column(String(64),default=now)
    def data(self): return dict(json.loads(self.payload),id=self.id,version=self.version,created_at=self.created_at,updated_at=self.updated_at,institution=self.institution)
class Event(Base):
    __tablename__='audit_events'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    institution:Mapped[str]=mapped_column(String(64),index=True)
    entity_id:Mapped[str]=mapped_column(String(36),index=True)
    actor:Mapped[str]=mapped_column(String(64))
    action:Mapped[str]=mapped_column(String(100))
    payload:Mapped[str]=mapped_column(Text)
    created_at:Mapped[str]=mapped_column(String(64),default=now)
class SessionRecord(Base):
    __tablename__='sessions'
    token_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[str]=mapped_column(String(36))
    expires_at:Mapped[str]=mapped_column(String(64))
class RetryKey(Base):
    __tablename__='idempotency'
    key:Mapped[str]=mapped_column(String(200),primary_key=True)
    institution:Mapped[str]=mapped_column(String(64))
    operation:Mapped[str]=mapped_column(String(64))
    result_id:Mapped[str]=mapped_column(String(36))
class AccountEmail(Base):
    __tablename__='account_emails'
    email:Mapped[str]=mapped_column(String(200),primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey('records.id',ondelete='CASCADE'),unique=True)
class WorkerStatus(Base):
    __tablename__='worker_status'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    last_seen:Mapped[str]=mapped_column(String(64))
    state:Mapped[str]=mapped_column(String(32))
class RecordVersion(Base):
    __tablename__='record_versions'
    entity_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    version:Mapped[int]=mapped_column(Integer,primary_key=True)
    institution:Mapped[str]=mapped_column(String(64),index=True)
    kind:Mapped[str]=mapped_column(String(64),index=True)
    payload:Mapped[str]=mapped_column(Text)
    captured_at:Mapped[str]=mapped_column(String(64),default=now)
class Relation(Base):
    __tablename__='record_relations'
    child_id:Mapped[str]=mapped_column(ForeignKey('records.id',ondelete='CASCADE'),primary_key=True)
    parent_id:Mapped[str]=mapped_column(ForeignKey('records.id',ondelete='RESTRICT'),primary_key=True)
    relation:Mapped[str]=mapped_column(String(64),primary_key=True)

url=os.getenv('DATABASE_URL','sqlite:///./pnsi.db')
engine=create_engine(url,connect_args={'check_same_thread':False,'timeout':30} if url.startswith('sqlite') else {},pool_pre_ping=True)
if url.startswith('sqlite'):
    @event.listens_for(engine,'connect')
    def sqlite_foreign_keys(connection,record):
        cursor=connection.cursor();cursor.execute('PRAGMA foreign_keys=ON');cursor.close()
Session=sessionmaker(engine,expire_on_commit=False)
def init():
    Base.metadata.create_all(engine)
    with Session() as s:
        # Backfill version snapshots for installations made before this migration.
        for r in s.scalars(select(Record)):
            if not s.get(RecordVersion,(r.id,r.version)):snapshot(s,r)
        def strip_secrets(v):
            if isinstance(v,dict):return {k:strip_secrets(x) for k,x in v.items() if k not in ('password_hash','token','api_key','secret')}
            if isinstance(v,list):return [strip_secrets(x) for x in v]
            return v
        for event in s.scalars(select(Event)):
            if any(k in event.payload for k in ['password_hash','api_key','"token"','"secret"']):event.payload=json.dumps(strip_secrets(json.loads(event.payload)),ensure_ascii=False)
        s.commit()
def snapshot(s,r):
    d=r.data();d.pop('password_hash',None)
    s.add(RecordVersion(entity_id=r.id,version=r.version,institution=r.institution,kind=r.kind,payload=json.dumps(d,ensure_ascii=False)))
def add(s,kind,institution,values):
    r=Record(kind=kind,institution=institution,payload=json.dumps(values,ensure_ascii=False));s.add(r);s.flush();snapshot(s,r)
    for field in ['case_id','source_id','claim_id','assessment_id','response_id','action_id']:
        parent_id=values.get(field)
        if parent_id:
            parent=s.get(Record,parent_id)
            if parent and parent.institution==institution:s.add(Relation(child_id=r.id,parent_id=parent_id,relation=field))
    return r
def audit(s,user,r,action,before=None):
    def safe(v):
        if isinstance(v,dict):return {k:safe(x) for k,x in v.items() if k not in ('password_hash','token','api_key','secret')}
        if isinstance(v,list):return [safe(x) for x in v]
        return v
    s.add(Event(institution=r.institution,entity_id=r.id,actor=user['name'],action=action,payload=json.dumps(safe({'before':before,'after':r.data()}),ensure_ascii=False)))
def update(s,r,values,expected):
    from fastapi import HTTPException
    from sqlalchemy import update as sqlupdate
    if expected!=r.version: raise HTTPException(409,'This record changed. Reload before saving.')
    data=r.data();data.update(values)
    for field in ['case_id','source_id','claim_id','assessment_id','response_id','action_id']:
        if field in values:
            s.execute(delete(Relation).where(Relation.child_id==r.id,Relation.relation==field))
            if values[field]:
                parent=s.get(Record,values[field])
                if not parent or parent.institution!=r.institution:raise HTTPException(422,'Related record is unavailable in this institution.')
                s.add(Relation(child_id=r.id,parent_id=parent.id,relation=field))
    for k in ['id','version','created_at','updated_at','institution']:data.pop(k,None)
    result=s.execute(sqlupdate(Record).where(Record.id==r.id,Record.version==expected).values(payload=json.dumps(data,ensure_ascii=False),version=expected+1,updated_at=now()))
    if result.rowcount!=1:raise HTTPException(409,'This record changed. Reload before saving.')
    s.refresh(r);snapshot(s,r);return r
