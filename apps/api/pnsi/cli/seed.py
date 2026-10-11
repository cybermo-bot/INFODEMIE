"""Seed the development database: ONMNE and one account per role.

Idempotent: existing accounts are left untouched unless --reset-passwords is
given. New passwords are random and written to data/seed-credentials.txt
(gitignored, mode 600). They are never printed or logged.

Usage: uv run python -m pnsi.cli.seed [--reset-passwords]
"""

from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from pnsi.audit import service as audit
from pnsi.auth.security import hash_password
from pnsi.db import get_sessionmaker
from pnsi.enums import Locale, Role
from pnsi.models import Institution, Membership, MembershipRole, User
from pnsi.settings import get_settings

INSTITUTION = {
    "code": "ONMNE",
    "name_fr": "Observatoire National des Maladies Nouvelles et Émergentes",
    "name_ar": "المرصد الوطني للأمراض الجديدة والمستجدة",
    "name_en": "National Observatory of New and Emerging Diseases",
}

DISPLAY_NAMES = {
    Role.ANALYSTE: "Compte de test · Analyste",
    Role.REFERENT_SCIENTIFIQUE: "Compte de test · Référent scientifique",
    Role.REDACTEUR: "Compte de test · Rédacteur",
    Role.REVISEUR_LINGUISTIQUE: "Compte de test · Réviseur linguistique",
    Role.APPROBATEUR: "Compte de test · Approbateur",
    Role.CABINET: "Compte de test · Cabinet",
    Role.PARTENAIRE: "Compte de test · Partenaire",
    Role.RELAIS_TERRAIN: "Compte de test · Relais terrain",
    Role.ADMINISTRATEUR: "Compte de test · Administrateur",
}

SEED_JUSTIFICATION = "Compte de développement créé par make seed (étape 1)."


def seed_email(role: Role) -> str:
    return f"{role.value.replace('_', '.')}@pnsi.local"


def seed(db: Session, reset_passwords: bool = False) -> dict[str, str]:
    """Create what is missing. Returns {email: password} for accounts given a new password."""
    institution = db.scalar(select(Institution).where(Institution.code == INSTITUTION["code"]))
    if institution is None:
        institution = Institution(**INSTITUTION)
        db.add(institution)
        db.flush()
        audit.record(
            db,
            "institution.created",
            institution_id=institution.id,
            object_type="institution",
            object_id=institution.id,
            context={"source": "seed"},
        )

    new_passwords: dict[str, str] = {}
    for role in Role:
        email = seed_email(role)
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            password = secrets.token_urlsafe(15)
            user = User(
                email=email,
                display_name=DISPLAY_NAMES[role],
                password_hash=hash_password(password),
                locale=Locale.FR,
            )
            db.add(user)
            db.flush()
            membership = Membership(user_id=user.id, institution_id=institution.id)
            membership.roles = [MembershipRole(role=role, justification=SEED_JUSTIFICATION)]
            db.add(membership)
            db.flush()
            audit.record(
                db,
                "user.created",
                institution_id=institution.id,
                object_type="user",
                object_id=user.id,
                changes={"roles": {"from": [], "to": [role.value]}},
                context={"source": "seed"},
            )
            new_passwords[email] = password
        elif reset_passwords:
            password = secrets.token_urlsafe(15)
            user.password_hash = hash_password(password)
            audit.record(
                db,
                "user.password_reset",
                institution_id=institution.id,
                object_type="user",
                object_id=user.id,
                context={"source": "seed"},
            )
            new_passwords[email] = password
    return new_passwords


def write_credentials(path: Path, passwords: dict[str, str]) -> None:
    existing: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line and not line.startswith("#"):
                email, pw = line.split("\t", 1)
                existing[email] = pw
    existing.update(passwords)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# PNSI development accounts. Local only, never commit or share.", "# email\tpassword"]
    lines += [f"{email}\t{pw}" for email, pw in sorted(existing.items())]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset-passwords", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    with get_sessionmaker()() as db, db.begin():
        passwords = seed(db, reset_passwords=args.reset_passwords)
    path = settings.data_dir / "seed-credentials.txt"
    if passwords:
        write_credentials(path, passwords)
    print(f"Seed done: {len(passwords)} account(s) with a new password. See {path}")


if __name__ == "__main__":
    main()
