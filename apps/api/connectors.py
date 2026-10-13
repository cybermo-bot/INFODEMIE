"""Permission-gated RSS. Redirects and private destinations are rejected."""
import socket,ipaddress,re,hashlib,html
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
from xml.etree import ElementTree
from email.utils import parsedate_to_datetime
import httpx
from fastapi import HTTPException
from .db import now
def validate_url(url):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise HTTPException(422,'A public HTTPS feed without embedded credentials is required.')
    try:addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    except OSError:raise HTTPException(422,'Feed host could not be resolved.')
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise HTTPException(422,'Private and special network destinations are blocked.')
    return p.hostname

def plain_text(value):
    class TextParser(HTMLParser):
        def __init__(self):super().__init__();self.parts=[];self.skip=0
        def handle_starttag(self,tag,attrs):
            if tag in ('script','style'):self.skip+=1
            elif tag in ('p','br','div','li'):self.parts.append(' ')
        def handle_endtag(self,tag):
            if tag in ('script','style'):self.skip=max(0,self.skip-1)
            elif tag in ('p','div','li'):self.parts.append(' ')
        def handle_data(self,data):
            if not self.skip:self.parts.append(data)
    parser=TextParser();parser.feed(value)
    return re.sub(r'\s+',' ',html.unescape(''.join(parser.parts))).strip()

def safe_article_url(value):
    try:
        parsed=urlparse(value)
        if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password:return value
    except ValueError:pass
    return None

def publication_date(value):
    try:
        try:date=parsedate_to_datetime(value)
        except (ValueError,TypeError):date=datetime.fromisoformat(value.replace('Z','+00:00'))
        if date.tzinfo is None:raise ValueError('Timezone missing')
        return date.astimezone(timezone.utc).isoformat()
    except (ValueError,TypeError,AttributeError,OverflowError):return None
class RSSConnector:
    def __init__(self,config):self.config=config
    def validate_config(self):
        if not self.config.get('enabled') or not self.config.get('permission'):raise ValueError('Source is not enabled or permitted.')
        return validate_url(self.config['url'])
    def healthcheck(self):return {'state':'ready','host':self.validate_config()}
    def fetch_batch(self,cursor=None,since=None,limit=100):
        self.validate_config()
        # No redirects; fetched content is bounded and XML entities are rejected.
        with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
            with client.stream('GET',self.config['url'],headers={'User-Agent':'PNSI-PermittedRSS/0.1'}) as response:
                response.raise_for_status();chunks=[];size=0
                for chunk in response.iter_bytes():
                    size+=len(chunk)
                    if size>2_000_000:raise ValueError('Feed exceeds 2 MB limit.')
                    chunks.append(chunk)
        data=b''.join(chunks)
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('Unsafe XML declarations are not permitted.')
        return self.parse_feed(data,limit)

    def parse_feed(self,data,limit=100):
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('Unsafe XML declarations are not permitted.')
        root=ElementTree.fromstring(data);items=[]
        feed_language=root.findtext('channel/language') or root.attrib.get('{http://www.w3.org/XML/1998/namespace}lang') or self.config.get('language','unknown')
        language=feed_language.lower().split('-')[0]
        if language not in ('fr','en','ar','derja','derja-latin'):language='unknown'
        nodes=root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
        for node in nodes[:min(limit,100)]:
            def field(*names):
                for name in names:
                    e=node.find(name)
                    if e is not None:return ''.join(e.itertext())
                return ''
            title=field('title','{http://www.w3.org/2005/Atom}title')
            description=field('description','{http://www.w3.org/2005/Atom}summary','{http://www.w3.org/2005/Atom}content')
            title=plain_text(title)[:2000];description=plain_text(description)[:10000]
            text=(title+'\n'+description).strip()[:20000]
            if not text:continue
            date=publication_date(field('pubDate','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated'))
            link=field('link')
            atom_links=node.findall('{http://www.w3.org/2005/Atom}link')
            if not link:link=next((l.attrib.get('href','') for l in atom_links if l.attrib.get('rel','alternate')=='alternate'),'')
            link=safe_article_url(link.strip())
            items.append({'title':title,'summary':description,'text':text,'published_at':date,'publication_date_known':date is not None,'collected_at':now(),'source_url':link,'platform_item_id':field('guid','{http://www.w3.org/2005/Atom}id') or link or hashlib.sha256(text.encode()).hexdigest(),'language':language,'content_type':self.config.get('content_type','rss_publication'),'attribution':self.config.get('attribution',self.config.get('name','RSS')),'license_url':self.config.get('license_url'),'modifications':self.config.get('modifications','Texte RSS converti en texte brut.')})
        return {'records':items,'next_cursor':None,'watermark':now(),'partial_errors':[]}
    def normalize(self,item):return item
    def apply_deletions(self):return {'state':'requires_source_specific_policy','deleted':0}
