"""Online SQLite backup, verified before announcing success; never overwrites a backup."""
import argparse, sqlite3
from pathlib import Path
from datetime import datetime, timezone

def backup(source, directory):
    source=Path(source).resolve();directory=Path(directory).resolve()
    if not source.is_file():raise ValueError('No local database exists yet.')
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/('pnsi-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    # Exclusive creation prevents overwriting any existing backup.
    with target.open('xb'):pass
    try:
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(target) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup integrity check failed.')
            if dst.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Backup relationship check failed.')
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=root/'data'/'pnsi-local.db');parser.add_argument('--directory',type=Path,default=root/'data'/'backups')
    args=parser.parse_args();print(backup(args.source,args.directory))
