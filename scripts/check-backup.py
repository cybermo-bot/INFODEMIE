"""Online SQLite backup to a separate file; never replaces the live database."""
import sqlite3,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
folder=root/'artifacts';folder.mkdir(exist_ok=True)
source=sqlite3.connect(root/'pnsi.db')
target=sqlite3.connect(folder/'restore-check.db')
source.backup(target)
integrity=target.execute('PRAGMA integrity_check').fetchone()[0]
counts=dict(target.execute('SELECT kind,COUNT(*) FROM records GROUP BY kind').fetchall())
original=dict(source.execute('SELECT kind,COUNT(*) FROM records GROUP BY kind').fetchall())
assert integrity=='ok' and counts==original
assert target.execute('SELECT COUNT(*) FROM record_versions').fetchone()[0]>0
print(json.dumps({'integrity':integrity,'record_counts_match':counts==original,'actions':counts.get('actions',0),'follow_ups':counts.get('follow-ups',0),'version_rows':target.execute('SELECT COUNT(*) FROM record_versions').fetchone()[0]},indent=2))
source.close();target.close()
