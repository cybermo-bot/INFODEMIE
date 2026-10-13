"""Scoped, deterministic PDF rendering of an approved snapshot."""
import os,io,html,re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
def render_pdf(report):
    locale=report.get('locale','fr');rtl=locale in ('ar','derja')
    font_path=os.getenv('PDF_FONT_PATH','C:/Windows/Fonts/arial.ttf' if os.name=='nt' else '')
    font='Helvetica'
    if font_path and Path(font_path).is_file():
        font='PNSIReport';pdfmetrics.registerFont(TTFont(font,font_path))
    if (rtl or re.search(r'[\u0600-\u06ff]',str(report))) and font=='Helvetica':raise ValueError('Arabic PDF export requires PDF_FONT_PATH pointing to an approved Unicode font.')
    def text(value):
        value=str(value)
        if rtl or re.search(r'[\u0600-\u06ff]',value):
            import arabic_reshaper
            from bidi.algorithm import get_display
            value=get_display(arabic_reshaper.reshape(value),base_dir='R' if rtl else 'L')
        return html.escape(value).replace('\n','<br/>')
    styles=getSampleStyleSheet()
    for name in ['Title','Heading1','Heading2','BodyText','Normal']:
        styles[name].fontName=font;styles[name].textColor=colors.HexColor('#213c50')
        if rtl:styles[name].alignment=TA_RIGHT
    styles['Title'].fontSize=22;styles['Title'].leading=30
    styles['Heading2'].fontSize=12;styles['Heading2'].leading=18
    styles['BodyText'].fontSize=10;styles['BodyText'].leading=16
    muted=ParagraphStyle('Muted',parent=styles['BodyText'],textColor=colors.HexColor('#647f8f'),fontSize=8,leading=13)
    labels={'fr':['RAPPORT DE VEILLE','Couverture et limites','Synthèse des dossiers','Preuves et décisions','Actions enregistrées','Suivi des observations'],'en':['MONITORING REPORT','Coverage and limitations','Case summary','Evidence and decisions','Recorded actions','Observation follow-up'],'ar':['تقرير الرصد','التغطية والحدود','ملخص الملفات','الأدلة والقرارات','الإجراءات المسجلة','متابعة الملاحظات']}.get('ar' if rtl else locale,['MONITORING REPORT','Coverage and limitations','Case summary','Evidence and decisions','Recorded actions','Observation follow-up'])
    buffer=io.BytesIO();snapshot=report['snapshot'];story=[]
    p=lambda v,style='BodyText':Paragraph(text(v),styles[style])
    story.extend([Paragraph(text('PNSI · '+labels[0]),muted),Spacer(1,14),p(report.get('title','PNSI'),'Title'),Paragraph(text('SYNTHETIC DEMONSTRATION · NOT CLINICAL GUIDANCE' if report.get('synthetic') else 'SELECTED SOURCE COVERAGE · HUMAN REVIEW'),muted),Spacer(1,10),Paragraph(text('Snapshot UTC: '+report['cutoff']+' · Report version '+str(report['version'])),muted),Spacer(1,20),p(labels[1],'Heading2'),p(report['coverage']),p('Observed changes do not establish causality. Counts are collected items, not people reached.'),Spacer(1,16)])
    stats=[['Collected items','Cases','Pending review','Approved responses'],[str(snapshot['items']),str(snapshot['cases']),str(snapshot['needs_review']),str(snapshot['approved_responses'])]]
    table=Table([[Paragraph(text(x),muted) for x in row] for row in stats],colWidths=[118]*4)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf3f1')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#dce5e9')),('INNERGRID',(0,0),(-1,-1),.5,colors.HexColor('#e5ebee')),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]));story.extend([table,Spacer(1,22),p(labels[2],'Heading2')])
    for case in snapshot['queue']:
        story.extend([p(case['code']+' · '+case.get('topic','')+' · '+case['title'],'Heading2'),p('Evidence: '+case['evidence_status']+' · priority '+str(case.get('priority','unknown'))+' · completeness '+str(case.get('completeness','unknown'))+'%'),Paragraph(text(case.get('priority_rationale','Review rationale unavailable')),muted),Spacer(1,12)])
    story.extend([p(labels[3],'Heading2')])
    for assessment in snapshot.get('assessments',[]):
        story.extend([p(assessment['proposed_status']+' · '+assessment['review_status']),p(assessment['rationale']),Paragraph(text('Assessment '+assessment['id']+' v'+str(assessment['version'])),muted)])
        for link in assessment.get('evidence_links',[]):story.append(Paragraph(text('Passage '+link['passage_id']+' · document '+link['document_id']+' v'+str(link['document_version'])+' · '+link['relation']),muted))
        story.append(Spacer(1,10))
    story.append(p(labels[4],'Heading2'))
    if not snapshot.get('actions'):story.append(p('No completed action in this snapshot.'))
    for action in snapshot.get('actions',[]):story.extend([p(action['channel']+' · '+action['performed_at']),p(action['body']),Spacer(1,10)])
    story.append(p(labels[5],'Heading2'))
    if not snapshot.get('follow_ups'):story.append(p('No follow-up observations in this snapshot.'))
    for follow in snapshot.get('follow_ups',[]):story.extend([p(str(follow['window_hours'])+'h · '+follow['state']+' · '+follow['due_at']),p(follow.get('interpretation') or follow['limitations'])])
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont(font,8);canvas.setFillColor(colors.HexColor('#8a9daa'));canvas.drawString(55,32,'PNSI · versioned evidence snapshot');canvas.drawRightString(A4[0]-55,32,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(buffer,pagesize=A4,rightMargin=55,leftMargin=55,topMargin=45,bottomMargin=55,title=report.get('title','PNSI'),author='PNSI workspace').build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
