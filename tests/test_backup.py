import importlib.util, sqlite3
from pathlib import Path

def test_online_backup_can_be_opened_and_restored_without_overwriting(tmp_path):
    script=Path(__file__).resolve().parents[1]/'scripts'/'backup-local.py'
    spec=importlib.util.spec_from_file_location('pnsi_backup',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=tmp_path/'live.db'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, text TEXT)')
        db.execute('INSERT INTO records(text) VALUES (?)',('Passage عربي privé',));db.commit()
        first=module.backup(source,tmp_path/'backups');second=module.backup(source,tmp_path/'backups')
        assert first!=second and first.exists() and second.exists()
        db.execute('INSERT INTO records(text) VALUES (?)',('Later update',));db.commit()
    restored=tmp_path/'restored.db';restored.write_bytes(first.read_bytes())
    with sqlite3.connect(restored) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT text FROM records').fetchall()==[('Passage عربي privé',)]
    with sqlite3.connect(source) as db:
        assert db.execute('SELECT COUNT(*) FROM records').fetchone()[0]==2
