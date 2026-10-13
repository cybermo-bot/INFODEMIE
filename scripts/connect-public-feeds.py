"""Local maintenance utility to enqueue verified public feeds, never demo fixtures.

It uses the same validated application operation as the administrator UI and
records the maintenance origin explicitly. It does not create users or sessions.
"""
import argparse,os,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--institution',required=True)
args=parser.parse_args()
os.environ['APP_ENV']='local'
os.environ['DATABASE_URL']='sqlite:///'+(root/'data'/'pnsi-local.db').as_posix()
sys.path.insert(0,str(root))
from apps.api.db import Session,Record,init
from apps.api.main import connect_public,PublicConnect
from sqlalchemy import select
init()
with Session() as s:
    admins=[r for r in s.scalars(select(Record).where(Record.kind=='users',Record.institution==args.institution)) if r.data().get('active') and r.data().get('role')=='administrator' and not r.data().get('synthetic')]
    if len(admins)!=1:raise RuntimeError('This utility requires exactly one active real administrator in the specified institution. Use the signed-in administrator UI otherwise.')
    owner=admins[0]
    actor={'id':owner.id,'role':'administrator','institution':args.institution,'name':'PNSI · Maintenance locale demandée par le propriétaire'}
    result=connect_public(PublicConnect(keys=['ecdc-news','ecdc-updates','ecdc-threats']),user=actor,s=s)
    print(json.dumps(result,ensure_ascii=False))
