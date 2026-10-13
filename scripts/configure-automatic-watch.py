"""Install the explicitly requested multilingual health scope, without changing accounts."""
import os,sys,argparse,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--institution',required=True);args=parser.parse_args()
os.environ['APP_ENV']='local';os.environ['DATABASE_URL']='sqlite:///'+(root/'data'/'pnsi-local.db').as_posix()
sys.path.insert(0,str(root))
from sqlalchemy import select
from apps.api.db import Session,Record,init
from apps.api.automatic_tracking import install_requested_scope
init()
with Session() as s:
    users=[r for r in s.scalars(select(Record).where(Record.kind=='users',Record.institution==args.institution)) if r.data().get('active') and r.data().get('role')=='administrator' and not r.data().get('synthetic')]
    if len(users)!=1:raise RuntimeError('Exactly one active real administrator is required for owner-requested configuration.')
    print(json.dumps(install_requested_scope(s,args.institution,{'id':users[0].id,'name':'PNSI · Owner-requested local monitoring configuration','institution':args.institution})))
