"""Role to permission matrix and the navigation it unlocks (decision D14).

Roles and their screens come from blueprint §8, responsibilities from spec §3.
The menu is derived from permissions, but the backend checks every call: a
hidden menu item is not a security boundary.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from pnsi.enums import Role


class Permission(StrEnum):
    CABINET_READ = "cabinet.read"
    MONITORING_READ = "monitoring.read"
    PARTNER_VIEWS_READ = "partner_views.read"
    SIGNALS_READ = "signals.read"
    SIGNALS_TRIAGE = "signals.triage"
    HEALTH_SIGNALS_READ = "health_signals.read"
    HEALTH_SIGNALS_FORWARD = "health_signals.forward"
    CASES_READ = "cases.read"
    CASES_WRITE = "cases.write"
    CASES_ASSIGN = "cases.assign"
    NARRATIVES_READ = "narratives.read"
    NARRATIVES_WRITE = "narratives.write"
    VERIFICATION_REQUEST = "verification.request"
    EVIDENCE_READ = "evidence.read"
    EVIDENCE_REVIEW = "evidence.review"
    ASSESSMENTS_REVIEW = "assessments.review"
    RESPONSES_READ = "responses.read"
    RESPONSES_DRAFT = "responses.draft"
    RESPONSES_SCIENTIFIC_APPROVE = "responses.scientific_approve"
    RESPONSES_LANGUAGE_APPROVE = "responses.language_approve"
    RESPONSES_APPROVE = "responses.approve"
    APPROVALS_READ = "approvals.read"
    ACTIONS_READ = "actions.read"
    ACTIONS_RECORD = "actions.record"
    ALERTS_READ = "alerts.read"
    ALERTS_ACK = "alerts.ack"
    FIELD_REPORTS_SUBMIT = "field_reports.submit"
    REPORTS_READ = "reports.read"
    REPORTS_CREATE = "reports.create"
    SOURCES_READ = "sources.read"
    SOURCES_MANAGE = "sources.manage"
    USERS_MANAGE = "users.manage"
    AUDIT_READ = "audit.read"
    JOBS_MANAGE = "jobs.manage"


P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ANALYSTE: frozenset({
        P.MONITORING_READ, P.SIGNALS_READ, P.SIGNALS_TRIAGE, P.HEALTH_SIGNALS_READ,
        P.HEALTH_SIGNALS_FORWARD, P.CASES_READ, P.CASES_WRITE, P.CASES_ASSIGN,
        P.NARRATIVES_READ, P.NARRATIVES_WRITE, P.VERIFICATION_REQUEST, P.EVIDENCE_READ,
        P.RESPONSES_READ, P.ACTIONS_READ, P.ALERTS_READ, P.ALERTS_ACK, P.REPORTS_READ,
        P.REPORTS_CREATE, P.SOURCES_READ,
    }),
    Role.REFERENT_SCIENTIFIQUE: frozenset({
        P.SIGNALS_READ, P.HEALTH_SIGNALS_READ, P.CASES_READ, P.NARRATIVES_READ,
        P.EVIDENCE_READ, P.EVIDENCE_REVIEW, P.ASSESSMENTS_REVIEW, P.VERIFICATION_REQUEST,
        P.RESPONSES_READ, P.RESPONSES_SCIENTIFIC_APPROVE, P.REPORTS_READ,
    }),
    Role.REDACTEUR: frozenset({
        P.CASES_READ, P.EVIDENCE_READ, P.RESPONSES_READ, P.RESPONSES_DRAFT,
        P.ACTIONS_READ, P.ACTIONS_RECORD,
    }),
    Role.REVISEUR_LINGUISTIQUE: frozenset({
        P.CASES_READ, P.RESPONSES_READ, P.RESPONSES_LANGUAGE_APPROVE,
    }),
    Role.APPROBATEUR: frozenset({
        P.CASES_READ, P.EVIDENCE_READ, P.RESPONSES_READ, P.RESPONSES_APPROVE,
        P.APPROVALS_READ, P.ACTIONS_READ, P.ACTIONS_RECORD, P.ALERTS_READ, P.ALERTS_ACK,
        P.REPORTS_READ,
    }),
    Role.CABINET: frozenset({P.CABINET_READ, P.REPORTS_READ}),
    Role.PARTENAIRE: frozenset({P.PARTNER_VIEWS_READ, P.REPORTS_READ}),
    Role.RELAIS_TERRAIN: frozenset({P.FIELD_REPORTS_SUBMIT}),
    # Platform operator: no editorial rights (blueprint §8, spec §3).
    Role.ADMINISTRATEUR: frozenset({
        P.SOURCES_READ, P.SOURCES_MANAGE, P.USERS_MANAGE, P.AUDIT_READ, P.JOBS_MANAGE,
    }),
}  # fmt: skip

EDITORIAL_PERMISSIONS = frozenset({
    P.SIGNALS_TRIAGE, P.CASES_WRITE, P.CASES_ASSIGN, P.NARRATIVES_WRITE, P.EVIDENCE_REVIEW,
    P.ASSESSMENTS_REVIEW, P.RESPONSES_DRAFT, P.RESPONSES_SCIENTIFIC_APPROVE,
    P.RESPONSES_LANGUAGE_APPROVE, P.RESPONSES_APPROVE, P.ACTIONS_RECORD,
})  # fmt: skip

# Roles that carry scientific or institutional authority. Granting one needs a
# written justification and can never be done by the person to themselves.
SENSITIVE_ROLES = frozenset({Role.REFERENT_SCIENTIFIQUE, Role.APPROBATEUR})


@dataclass(frozen=True)
class NavItem:
    key: str
    path: str
    permission: Permission
    stage: int  # build stage that delivers the screen


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("cabinet", "/cabinet", P.CABINET_READ, 6),
    NavItem("veille", "/veille", P.MONITORING_READ, 6),
    NavItem("partenaires", "/partenaires", P.PARTNER_VIEWS_READ, 6),
    NavItem("signaux", "/signaux", P.SIGNALS_READ, 2),
    NavItem("signaux_sanitaires", "/signaux-sanitaires", P.HEALTH_SIGNALS_READ, 6),
    NavItem("dossiers", "/dossiers", P.CASES_READ, 5),
    NavItem("narratifs", "/narratifs", P.NARRATIVES_READ, 4),
    NavItem("reponses", "/reponses", P.RESPONSES_READ, 5),
    NavItem("approbations", "/approbations", P.APPROVALS_READ, 5),
    NavItem("alertes", "/alertes", P.ALERTS_READ, 6),
    NavItem("actions", "/actions", P.ACTIONS_READ, 5),
    NavItem("terrain", "/terrain", P.FIELD_REPORTS_SUBMIT, 6),
    NavItem("preuves", "/preuves", P.EVIDENCE_READ, 4),
    NavItem("rapports", "/rapports", P.REPORTS_READ, 6),
    NavItem("sources", "/sources", P.SOURCES_READ, 2),
    NavItem("administration", "/administration", P.USERS_MANAGE, 1),
)


def permissions_for(roles: Iterable[Role]) -> frozenset[Permission]:
    perms: set[Permission] = set()
    for role in roles:
        perms |= ROLE_PERMISSIONS[role]
    return frozenset(perms)


def nav_for(permissions: Iterable[Permission]) -> list[NavItem]:
    granted = set(permissions)
    return [item for item in NAV_ITEMS if item.permission in granted]
