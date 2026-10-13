"""Verified public RSS catalog. Attribution and license travel with each item."""
LICENSE_URL='https://creativecommons.org/licenses/by/4.0/'
PERMISSION_URL='https://www.ecdc.europa.eu/en/ecdc-intellectual-property-notices'
CATALOG={
    'ecdc-news':{'name':'ECDC · Actualités sanitaires','url':'https://www.ecdc.europa.eu/en/taxonomy/term/1307/feed','topic':'Actualités sanitaires'},
    'ecdc-updates':{'name':'ECDC · Mises à jour épidémiologiques','url':'https://www.ecdc.europa.eu/en/taxonomy/term/1310/feed','topic':'Surveillance'},
    'ecdc-threats':{'name':'ECDC · Rapports sur les menaces transmissibles','url':'https://www.ecdc.europa.eu/en/taxonomy/term/1505/feed','topic':'Surveillance'},
}
def source_config(key):
    return dict(CATALOG[key],catalog_key=key,platform='rss',enabled=True,state='pending_collection',language='en',languages='en',owner='Responsable de veille',poll_interval_minutes=30,retention_days=90,synthetic=False,last_success=None,
                attribution='European Centre for Disease Prevention and Control (ECDC)',license_url=LICENSE_URL,permission_url=PERMISSION_URL,
                permission='ECDC-owned RSS metadata under CC BY 4.0. Attribution and source links retained. Text normalized to plain text; no logos, images, third-party documents or endorsement.',
                modifications='Texte RSS converti en texte brut; redaction automatique des identifiants éventuels.',content_type='institutional_news')
