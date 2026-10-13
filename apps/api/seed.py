import hashlib, os, secrets
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from .db import Record,add,now,audit

ROLES=['analyst','scientific_reviewer','communication_editor','institutional_approver','viewer','administrator','operator']
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()
def check_password(password,encoded):
    return secrets.compare_digest(password_hash(password,encoded.split(':')[0]),encoded)
def seed(s):
    if s.scalar(select(Record).where(Record.kind=='users')):return
    for institution in ['demo-onmne','demo-partner']:
        add(s,'institutions',institution,{'name':'PNSI · Atelier de démonstration' if institution=='demo-onmne' else 'Partenaire · Espace isolé','synthetic':True})
        for role in ROLES:
            add(s,'users',institution,{'name':{'analyst':'Amira · Analyste','scientific_reviewer':'Sami · Revue scientifique','communication_editor':'Lina · Communication','institutional_approver':'Nadia · Validation','viewer':'Youssef · Observateur','administrator':'Admin · Institution','operator':'Ops · Plateforme'}[role], 'email':role+'@'+institution+'.local','role':role,'active':True,'locale':'fr','timezone':'Africa/Tunis','password_hash':password_hash(os.getenv('DEMO_PASSWORD','Pnsi-Demo-2026!')),'synthetic':True})
    inst='demo-onmne'; actor={'name':'Initialisation · données synthétiques'}
    sources=[]
    for name,platform,state,lang in [('Import autorisé','manual','ready','fr, ar, Derja'),('Flux RSS de démonstration','rss','not_configured','fr'),('YouTube Data API','youtube','not_configured','multilingual'),('Bluesky','bluesky','pending_permission','multilingual'),('Meta Content Library','meta','unavailable','multilingual'),('X API','x','disabled','multilingual')]:
        sources.append(add(s,'sources',inst,{'name':name,'platform':platform,'state':state,'enabled':platform=='manual','url':'','permission':'Synthetic demonstration only' if platform=='manual' else '', 'languages':lang,'owner':'Source steward · à désigner','retention_days':90,'last_success':now() if platform=='manual' else None,'error':'Access approval and configuration required' if platform!='manual' else None,'synthetic':True}))
    ev=add(s,'evidence-sources',inst,{'name':'Corpus de formation PNSI','organization':'Atelier synthétique','state':'approved','permission':'Synthetic training fixture, no clinical authority','scope':'Products Z, Q and illness Y only','reviewer':'Fixture scientifique','synthetic':True})
    doc=add(s,'documents',inst,{'title':'Guide de formation · produit Z et maladie Y','source_id':ev.id,'state':'approved','language':'fr','edition':'TRAINING-1','effective_date':'2026-10-01','review_date':'2027-01-01','url':'','permission':'Synthetic training only','checksum':hashlib.sha256(b'synthetic-training-v1').hexdigest(),'passages':[{'id':'training-z-1','page':1,'text':'Donnée synthétique : le produit Z ne prévient pas la maladie Y dans ce scénario de formation. Cette phrase ne constitue pas une recommandation médicale.'},{'id':'training-z-2','page':2,'text':'Donnée synthétique : les données sur le produit Q restent insuffisantes; aucune conclusion définitive ne peut être proposée.'}],'synthetic':True})
    claims=[('Le produit Z prévient toujours la maladie Y.','contradicted','Vaccination',82,'fr'),('هل المنتج Q يحمي من المرض Y؟','insufficient_evidence','Prévention',67,'ar'),('Le dispositif R détecte le signal S dans ce scénario.','supported','Surveillance',43,'fr'),('Produit Z : une observation suffit pour conclure.','misleading','Médicaments',74,'fr'),('Produit Q et maladie Y : résultats divergents.','conflicting_evidence','Prévention',61,'fr'),('3lech ma famech information 3al service T?','not_factual','Accès aux soins',36,'derja-latin')]
    for i,(text,status,topic,priority,lang) in enumerate(claims):
        case=add(s,'cases',inst,{'code':f'C-{i+1:03d}','title':text,'original_text':text,'language':lang,'topic':topic,'status':'in_review' if i!=2 else 'assessed','evidence_status':status,'priority':priority,'completeness':75,'harm':round(priority/100,2),'growth':None,'engagement':0.4,'exposure_proxy':0.3,'priority_rationale':'Synthetic analyst priority. Growth missing; completeness 75%. Weights require validation.','owner':'Amira · Analyste','reviewer':'Sami · Revue scientifique','due_at':(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat(),'synthetic':True})
        claim=add(s,'claims',inst,{'case_id':case.id,'original_text':text,'neutral_text':text,'language':lang,'topic':topic,'claim_type':'question' if i in (1,5) else 'assertion','synthetic':True})
        assessment=add(s,'assessments',inst,{'case_id':case.id,'claim_id':claim.id,'proposed_status':status,'review_status':'pending','rationale':'Proposition synthétique pour tester la revue. Aucune conclusion clinique réelle.','limitations':['Corpus de formation uniquement','Couverture sélectionnée; géographie inconnue'],'evidence_links':[{'document_id':doc.id,'document_version':1,'passage_id':'training-z-1' if i==0 else 'training-z-2','relation':'contradicts' if i==0 else 'context','relevance_reason':'Fixture de formation uniquement'}] if i in (0,1) else [],'reviewer_id':None,'synthetic':True})
        for j in range([16,9,6,12,8,5][i]):
            add(s,'content',inst,{'text':text,'original_text':text,'translation':'Translation awaiting language review' if lang!='fr' else None,'source_id':sources[0].id,'source_name':'Import autorisé · synthétique','case_id':case.id,'language':lang,'topic':topic,'stance':claim.data()['claim_type'],'published_at':(datetime.now(timezone.utc)-timedelta(days=j%7,hours=j)).isoformat(),'platform_item_id':f'seed-{i}-{j}','geography':'unknown','redacted':True,'synthetic':True})
        audit(s,actor,case,'case.seeded')
        if priority>=70:add(s,'alerts',inst,{'case_id':case.id,'title':text,'severity':'high','state':'open','rationale':'Priorité synthétique ≥70; seuil pilote non validé.','owner':'Amira · Analyste','due_at':case.data()['due_at'],'synthetic':True})
    for theme in ['Vaccination','Prévention','Accès aux soins']:
        add(s,'narratives',inst,{'title':theme,'state':'proposed','rationale':'Regroupement de formation à confirmer par un analyste','synthetic':True})
    add(s,'settings',inst,{'external_ai_enabled':False,'auto_publish_enabled':False,'raw_retention_hours':24,'redacted_retention_days':90,'default_locale':'fr','default_timezone':'Africa/Tunis','translation_state':'provisional','synthetic':True})
    s.commit()
