import pytest

from pnsi.authz.permissions import (
    EDITORIAL_PERMISSIONS,
    NAV_ITEMS,
    ROLE_PERMISSIONS,
    SENSITIVE_ROLES,
    Permission,
    nav_for,
    permissions_for,
)
from pnsi.enums import Role


def nav_keys(role: Role) -> list[str]:
    return [n.key for n in nav_for(permissions_for([role]))]


def test_every_role_has_permissions():
    assert set(ROLE_PERMISSIONS) == set(Role)
    for role, perms in ROLE_PERMISSIONS.items():
        assert perms, role


def test_administrateur_has_no_editorial_rights():
    assert not ROLE_PERMISSIONS[Role.ADMINISTRATEUR] & EDITORIAL_PERMISSIONS


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (Role.CABINET, ["cabinet", "rapports"]),
        (Role.RELAIS_TERRAIN, ["terrain"]),
        (Role.PARTENAIRE, ["partenaires", "rapports"]),
        (Role.REVISEUR_LINGUISTIQUE, ["dossiers", "reponses"]),
        (Role.ADMINISTRATEUR, ["sources", "administration"]),
    ],
)
def test_menu_per_role(role, expected):
    assert nav_keys(role) == expected


def test_read_only_roles_cannot_write():
    for role in (Role.CABINET, Role.PARTENAIRE):
        assert not ROLE_PERMISSIONS[role] & EDITORIAL_PERMISSIONS


def test_only_approbateur_approves_for_publication():
    holders = {r for r, p in ROLE_PERMISSIONS.items() if Permission.RESPONSES_APPROVE in p}
    assert holders == {Role.APPROBATEUR}


def test_scientific_review_belongs_to_referent():
    holders = {r for r, p in ROLE_PERMISSIONS.items() if Permission.ASSESSMENTS_REVIEW in p}
    assert holders == {Role.REFERENT_SCIENTIFIQUE}


def test_drafting_and_approval_are_separate_roles():
    assert Permission.RESPONSES_APPROVE not in ROLE_PERMISSIONS[Role.REDACTEUR]
    assert Permission.RESPONSES_DRAFT not in ROLE_PERMISSIONS[Role.APPROBATEUR]


def test_sensitive_roles():
    assert {Role.REFERENT_SCIENTIFIQUE, Role.APPROBATEUR} == SENSITIVE_ROLES


def test_combined_roles_union_permissions():
    combined = permissions_for([Role.ANALYSTE, Role.REDACTEUR])
    assert Permission.RESPONSES_DRAFT in combined
    assert Permission.SIGNALS_TRIAGE in combined


def test_nav_paths_unique_and_every_permission_used_somewhere():
    assert len({n.path for n in NAV_ITEMS}) == len(NAV_ITEMS)
    granted = set().union(*ROLE_PERMISSIONS.values())
    assert set(Permission) == granted
