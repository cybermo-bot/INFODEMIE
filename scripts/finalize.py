from pathlib import Path
root=Path(__file__).resolve().parents[1]
ui=root/'apps/web/app/workspace.tsx'
code=ui.read_text(encoding='utf-8-sig')
code=code.replace("downloadReport(r,'csv')}><Download size={14}/>CSV</button>","downloadReport(r,'csv')}><Download size={14}/>CSV</button><button className=\"btn\" onClick={()=>downloadReport(r,'pdf')}><Download size={14}/>PDF</button>")
code=code.replace("const current=nav.find(n=>n.path===path)||nav.find(n=>path.startsWith(n.path)&&n.key!=='overview');","const current=nav.find(n=>n.path===path)||(path.startsWith('/cases/')?nav.find(n=>n.key==='claims'):nav.find(n=>path.startsWith(n.path)&&n.key!=='overview'));")
ui.write_text(code,encoding='utf-8')
readiness=root/'docs/readiness.md'
code=readiness.read_text(encoding='utf-8')
code=code.replace('Frozen report snapshots; institutional approval before JSON/CSV export','Frozen report snapshots; institutional approval before PDF/JSON/CSV export')
code=code.replace('The original suite has 22 direct API tests','The original suite has 22 direct API tests')
code=code.replace('Additional tests cover new-case claims and secret redaction from audit.','Additional tests cover new-case claims, secret redaction from audit, immutable version history, independent annotation resolution and measured frozen benchmarks.')
code=code.replace('benchmark computations, source revision/edit semantics','source revision/edit semantics')
code=code.replace('PDF/XLSX exports including evaluated Arabic typography','XLSX exports and full linguistic QA of Arabic PDF typography')
code=code.replace('independent annotation conflict resolution, ','complete multi-annotator disagreement reconciliation, ')
code=code.replace('No model is selected nor evaluated.','No model is selected nor evaluated.')
readiness.write_text(code,encoding='utf-8')
