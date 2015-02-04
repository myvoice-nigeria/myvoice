from django.conf import settings
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import *
from reportlab.platypus.doctemplate import SimpleDocTemplate
from itertools import groupby
import os

fontPath = os.path.join(settings.PROJECT_ROOT,
                        'myvoice/static/lib/bootstrap-3.2.0/fonts/glyphicons-halflings-regular.ttf')
pdfmetrics.registerFont(TTFont('Glyphicons Halflings', fontPath))

barColors = [colors.black,
             colors.black.clone(alpha=0.5),
             colors.black.clone(alpha=0.2)]

styles = getSampleStyleSheet()
sectionHeadStyle = styles['Normal'].clone(
    'SectionHead',
    backColor=colors.black.clone(alpha=0.4),
    borderPadding=(6, 10, 8),
    fontSize=11,
    spaceBefore=35,
    spaceAfter=15)
bodyText9pt = styles['BodyText'].clone('BodyText9pt', fontSize=9)
styles.add(sectionHeadStyle)
styles.add(bodyText9pt)


def p(text, style=styles['BodyText9pt']):
    """Renders the supplied `text` as a paragraph, using the `style` specified."""
    return Paragraph(text, style)


def heading(text):
    """Renders the supplied `text` as a section heading."""
    return p('<font color=white>%s</font>' % text.upper(), styles['SectionHead'])


def page_break():
    """Renders a page break."""
    return PageBreak()


def add_page_number(canvas, doc):
    """Adds page numbers to the supplied document."""
    text = 'Page %s' % doc.page
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(100*mm, 10*mm, text)


class FacilityChart(Drawing):

    def __init__(self, width=480, height=480, *args, **kwargs):
        Drawing.__init__(self, width, height, *args, **kwargs)

        self.add(HorizontalBarChart(), name='chart')
        self.chart.width = self.width - 100
        self.chart.height = self.height - 80
        self.chart.x = 60
        self.chart.y = 60
        self.chart.barSpacing = 1
        self.chart.groupSpacing = 6
        self.chart.bars[0].fillColor = barColors[2]
        self.chart.bars[1].fillColor = barColors[1]
        self.chart.bars[2].fillColor = barColors[0]
        self.chart.bars.strokeWidth = 0
        self.chart.barLabelFormat = '%d'
        self.chart.barLabels.boxAnchor = 'w'
        self.chart.barLabels.fontSize = 8
        self.chart.barLabels.leftPadding = 3
        self.chart.barLabels.textAnchor = 'middle'
        self.chart.categoryAxis.strokeColor = barColors[1]
        self.chart.categoryAxis.labels.fontSize = 9
        self.chart.categoryAxis.labels.textAnchor = 'end'
        self.chart.valueAxis.valueMin = 0
        self.chart.valueAxis.strokeColor = barColors[1]
        self.chart.valueAxis.labels.fontSize = 9

        self.add(Legend(), name='legend')
        self.legend.alignment = 'right'
        self.legend.fontSize = 10
        self.legend.x = int(0.24 * self.width)
        self.legend.y = 25
        self.legend.boxAnchor = 'nw'
        self.legend.colorNamePairs = [
            (barColors[0], 'Surveys Sent'),
            (barColors[1], 'Surveys Started'),
            (barColors[2], 'Surveys Completed')
        ]
        self.legend.dxTextSpace = 5
        self.legend.dy = 6
        self.legend.dx = 6
        self.legend.deltay = 5
        self.legend.columnMaximum = 1
        self.legend.strokeWidth = 0


class FacilityReportPdf(object):
    
    def summary(self, clinic, sent, started, completed):
        """Renders the Facility Report Summary section."""
        p_started = (float(started) / sent) * 100
        p_completed = (float(completed) / sent) * 100
        summary_tbl = Table([
            (p('<b>SURVEY PARTICIPATION</b>'), '', ''),
            (p('<font color=0x8AC43F><b>%s</b></font>' % sent),
             p('<font color=0x8AC43F><b>%s</b> (%.0f%%)</font>' % (started, p_started)),
             p('<font color=0x8AC43F><b>%s</b> (%.0f%%)</font>' % (completed, p_completed))),
            ('Sent', 'Started', 'Completed')
        ], colWidths=[0.8*inch, 0.8*inch, 0.8*inch])
        summary_tbl.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)),
            ('TOPPADDING', (0, 1), (-1, 1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
            ('LINEBELOW', (0, 1), (-1, 1), 0.4, colors.black),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('FONTSIZE', (0, -1), (-1, -1), 8),
        ]))
        tbl = Table([
            (p('<font size=14><b>%s</b> Facility Report</font>' % clinic.name), ''),
            (p("""The following document was generated through the
    ICT4SA program, intended to provide trial period 
    reporting to selected %s Clinic Staff. The following 
    data was collected through SMS surveys of patients at 
    %s.""" % (clinic.lga, clinic.name)), summary_tbl)
        ], colWidths=[3.8*inch, 2.6*inch])
        tbl.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('RIGHTPADDING', (0, -1), (0, -1), 10),
            ('RIGHTPADDING', (-1, -1), (-1, -1), 10),
            ('LEFTPADDING', (-1, -1), (-1, -1), 10),
            ('BACKGROUND', (-1, -1), (-1, -1), colors.grey.clone(alpha=0.2)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return tbl
    
    def facility_chart(self, clinic, stats, clinics):
        """Renders the Facility Participation Chart."""
        flowables = []
        flowables.append(heading('Participation By Facility'))
        flowables.append(p('Number of patients who received, started, and completed surveys across %s.' % clinic.name))
        d = FacilityChart()
        # categories = ['\n'.join(x.split()) for x in clinics]
        data = [stats['completed'], stats['started'], stats['sent']]
        d.chart.data = data
        d.chart.categoryAxis.categoryNames = clinics
        flowables.append(d)
        return KeepTogether(flowables)

    def feedback_responses(self, clinic, responses):
        """Renders the Feedback Responses section."""
        cellBgColor = colors.grey.clone(alpha=0.2)
        flowables = []
        flowables.append(heading('Patient Feedback Responses'))
        flowables.append(p('<para spaceafter=12>Summary of patient feedback responses compared to LGA-wide averages.</para>'))
        rows = [('Patients from %s said:' % clinic.name, '', '', 'Patients from other facilities said:', '', '')]
        for r in responses:
            if r[3] >= 10:
                symbol = u'\ue013'
            elif r[3] <= -10:
                symbol = u'\ue014'
            else:
                symbol = u''
            rows.append((
                '%d (%.0f%%)' % r[1], r[0], u'\ue107' if r[1][1] < 30.0 else '  ',
                '%d (%.0f%%)' % r[2], r[0], symbol
            ))
        tbl = Table(rows, colWidths=[0.9*inch, 2*inch, 0.3*inch] * 2)
        tbl.setStyle(TableStyle([
            ('SPAN', (0, 0), (2, 0)),
            ('SPAN', (3, 0), (5, 0)),
            ('BACKGROUND', (0, 1), (0, -1), cellBgColor),
            ('BACKGROUND', (3, 1), (3, -1), cellBgColor),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTSIZE', (0, 0), (0, -1), 10),
            ('FONTSIZE', (3, 0), (3, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, 0), 2),
            ('RIGHTPADDING', (0, 0), (-1, 0), 2),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (2, 0), (2, -1), 'Glyphicons Halflings'),
            ('FONT', (5, 0), (5, -1), 'Glyphicons Halflings'),
            ('GRID', (0, 0), (-1, -1), 3, colors.white),
        ]))
        flowables.append(tbl)

        legend = Table([
            ('KEY', '', '', '', '', ''),
            (u'\ue107', 'Problem area;\nrequires attention',
             u'\ue014', '%s performed worse\nthan the LGA average' % clinic.name,
             u'\ue013', '%s performed better\nthan the LGA average' % clinic.name)
        ])
        legend.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)),
            ('TOPPADDING', (0, 0), (-1, 0), 15),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, 0), 1, cellBgColor),
            ('FONT', (0, 1), (0, 1), 'Glyphicons Halflings'),
            ('FONT', (2, 1), (2, 1), 'Glyphicons Halflings'),
            ('FONT', (4, 1), (4, 1), 'Glyphicons Halflings'),
            ('FONTSIZE', (1, 1), (1, 1), 7),
            ('FONTSIZE', (3, 1), (3, 1), 7),
            ('FONTSIZE', (5, 1), (5, 1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        flowables.append(legend)
        return KeepTogether(flowables)

    def feedback_on_servies(self, min_date, max_date, data):
        """Renders the Feedback on Services section."""
        flowables = []
        flowables.append(heading('Feedback On Services'))
        flowables.append(p('<para spaceafter=12>Number of patients with this service, who reported this feedback.</para>'))
        if data:
            service, feedback = data[0]
            rows = [['%s to %s' % (min_date.strftime('%B %d, %Y'), max_date.strftime('%B %d, %Y'))
                     ] + ['\n'.join(x[0].split()) for x in feedback]]
            for service, feedback in data:
                row = [service] + ['%s (%s)' % ('N/A' if not x else x, 0 if y is None else y)
                                   for _, x, y in feedback]
                rows.append(row)
            width = 4.6 / (len(rows[0]) - 1)
            tbl = Table(rows, colWidths=[1.8*inch] + [width*inch] * (len(rows[0]) - 1))
            tbl.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), (0xF9F9F9, None)),
                ('BACKGROUND', (0, 0), (0, 0), 0xE5E6E7),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            flowables.append(tbl)
        return KeepTogether(flowables)

    def detailed_comments(self, data):
        """Renders the Detailed Comments section."""
        flowables = []
        flowables.append(heading('Detailed Comments'))
        tblStyle = TableStyle([
            ('SPAN', (0, 0), (-1, 0)),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTSIZE', (0, 0), (-1, 0), 5),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), (0xF9F9F9, None)),
            ('BACKGROUND', (0, 0), (-1, 0), colors.black.clone(alpha=0.4)),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 1), (-1, 0), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])
        tbl = Table([('Date', 'Comments')], colWidths=[0.8*inch, 5.6*inch])
        tbl.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        flowables.append(tbl)
        grouped_comments = groupby(data, lambda x: x['question'])
        for question, comments in grouped_comments:
            tbl = Table([(p('<font color=white>%s</font>' % question.upper()), '')] + [
                (x['datetime'].strftime('%d/%m/%Y'), p(x['response'])) for x in comments
            ], colWidths=[0.8*inch, 5.6*inch])
            tbl.setStyle(tblStyle)
            flowables.append(tbl)
        return flowables

    def render_to_list(self, ctx):
        """Renders all report sections, returning them as a list of flowables."""
        elements = []
        elements.append(self.summary(ctx['clinic'], ctx['num_registered'], ctx['num_started'], ctx['num_completed']))
        elements.append(self.facility_chart(ctx['clinic'], ctx['feedback_stats'], ctx['feedback_clinics']))
        elements.append(self.feedback_responses(ctx['clinic'], ctx['response_stats']))
        elements.append(self.feedback_on_servies(ctx['min_date'], ctx['max_date'], ctx['feedback_by_service']))
        elements.extend(self.detailed_comments(ctx['detailed_comments']))
        elements.append(page_break())
        return elements

    def render_to_response(self, flowables, outfile):
        """Renders a list of flowables as a PDF to the specified `outfile`."""
        doc = SimpleDocTemplate(outfile)
        doc.build(flowables, onFirstPage=add_page_number, onLaterPages=add_page_number)


def render_test_pdf():
    """Renders a sample PDF report."""
    from datetime import datetime
    from pytz import UTC
    
    stats = {'completed': [8, 20, 8, 2, 7, 6, 55, 24, 8, 22, 0],
             'sent': [256, 329, 84, 210, 115, 94, 1653, 934, 135, 108, 39],
             'started': [37, 33, 13, 17, 15, 14, 128, 56, 20, 43, 0]}
    categories = [
        'Arum Chugbu PHC',
        'Gwagi PHC',
        'Kwabe PHC',
        'Kwarra PHC',
        'Mararaba Gongon PHC',
        'Nakere PHC',
        'Wamba General Hospital',
        'Wamba Model Clinic',
        'Wayo Matti PHC',
        'Yashi Madaki PHC',
        'Zalli PHC']
    responses = [
        ('Open Facility',
        (29, 88.0),
        (294, 86.0),
        2.0),
       ('Respectful Staff Treatment',
        (22, 92.0),
        (200, 82.0),
        10.0),
       ('Clean Hospital Materials',
        (23, 100.0),
        (169, 91.0),
        9.0),
       ('Charged Fairly',
        (17, 77.0),
        (104, 62.0),
        15.0),
       ('Wait Time',
        (20, 100.0),
        (128, 91.0),
        9.0)]
    svc_feedback = [
       ('ANC',
        [(u'Open Facility', 2, '100.0%'),
         (u'Respectful Staff Treatment', 1, '100.0%'),
         (u'Treatment Explanation', 1, '100.0%'),
         (u'Charged Fairly', 1, '100.0%'),
         ('Wait Time', u'<1 hr', 1)]),
       ('Normal Delivery',
        [(u'Open Facility', 0, None),
         (u'Respectful Staff Treatment', 0, None),
         (u'Treatment Explanation', 0, None),
         (u'Charged Fairly', 0, None),
         ('Wait Time', None, 0)]),
       ('Immunization/Vaccination',
        [(u'Open Facility', 1, '100.0%'),
         (u'Respectful Staff Treatment', 0, None),
         (u'Treatment Explanation', 0, None),
         (u'Charged Fairly', 0, None),
         ('Wait Time', None, 0)]),
       ('OPD',
        [(u'Open Facility', 25, '86.0%'),
         (u'Respectful Staff Treatment', 20, '91.0%'),
         (u'Treatment Explanation', 21, '100.0%'),
         (u'Charged Fairly', 15, '75.0%'),
         ('Wait Time', u'<1 hr', 4)]),
       ('Family Planning',
        [(u'Open Facility', 1, '100.0%'),
         (u'Respectful Staff Treatment', 1, '100.0%'),
         (u'Treatment Explanation', 1, '100.0%'),
         (u'Charged Fairly', 1, '100.0%'),
         ('Wait Time', None, 0)])]

    max_date = datetime(2015, 2, 2, 0, 16, 47, 52361, tzinfo=UTC)
    min_date = datetime(2014, 7, 7, 0, 0, tzinfo=UTC)

    comments = [
        {'datetime': datetime(2014, 7, 24, 16, 33, 18, 32000, tzinfo=UTC),
        'question': u'Charge for Services',
        'response': u'Ipaid for malaria drugs'},
       {'datetime': datetime(2014, 9, 2, 2, 38, 5, 782000, tzinfo=UTC),
        'question': u'Charge for Services',
        'response': u'I PAY  FOR DELIVERING  500N'},
       {'datetime': datetime(2014, 10, 31, 15, 49, 29, 597000, tzinfo=UTC),
        'question': u'Charge for Services',
        'response': u'700'},
       {'datetime': datetime(2014, 10, 2, 11, 15, 35, 216000, tzinfo=UTC),
        'question': u'Facility Availability',
        'response': u'Sorry i mean 1'},
       {'datetime': datetime(2014, 7, 31, 12, 17, 30, 991000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'The improvement in the hospital is beyond expectation. '},
       {'datetime': datetime(2014, 8, 16, 10, 43, 23, 676000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'They staff in the hospital are trying their best. But i am  appealing to goverment should upgrade gwagi PHC. May God see us through nd i really appreciate this focus by the health organization. '},
       {'datetime': datetime(2014, 8, 20, 21, 47, 48, 215640, tzinfo=UTC),
        'question': 'General Feedback',
        'response': u'THE H0SP ARE DOING WILL T0 US, IN WAMBA WEST'},
       {'datetime': datetime(2014, 8, 22, 13, 50, 41, 547273, tzinfo=UTC),
        'question': 'General Feedback',
        'response': u'Effective  activities  is  on  in  the  clinic. The imminazation exercise was well orgainase by the clinic staff.'},
       {'datetime': datetime(2014, 8, 26, 9, 54, 0, 848560, tzinfo=UTC),
        'question': 'General Feedback',
        'response': u'The hospital has now change  because the staffs are always available unlike before .Tank you for hearing my voice'},
       {'datetime': datetime(2014, 8, 27, 5, 22, 36, 596000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'The staff are seriously doing their best nd i wish to solicit to u My voice should provide all hospital and PHC with all health equipments.'},
       {'datetime': datetime(2014, 8, 28, 8, 47, 47, 669000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'Infact we reconment d service dat d hospital give to us'},
       {'datetime': datetime(2014, 8, 29, 16, 48, 43, 661081, tzinfo=UTC),
        'question': 'General Feedback',
        'response': u'The comment about gwagi phc  the  should  try & be punctual on there duties  specially night duty, the bee eccouragy  pregnt women with some gift if the are their for check up, the are trying but the should put more effort. I wish  them well, & may God help them!'},
       {'datetime': datetime(2014, 8, 30, 20, 0, 17, 267000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'infact d hospital are trying there b est'},
       {'datetime': datetime(2014, 8, 31, 11, 34, 13, 143000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'Very excellent nd well to do hospital.'},
       {'datetime': datetime(2014, 9, 1, 21, 45, 29, 168916, tzinfo=UTC),
        'question': 'General Feedback',
        'response': u'gwagi hospital are doing gud and the did not have a problem seriously.  they are trying there best. Tnx '},
       {'datetime': datetime(2014, 9, 2, 3, 40, 57, 947000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'COMPALEN SOME OFTHE STAFFS AER NOT ALLWAST FURND ON SONDAY IN  PHC     PRAIST THE  INCAEG SHE ALLWAYS BUESY  AND THE  PHC IT IS ALLWAYS  CAELING .'},
       {'datetime': datetime(2014, 9, 10, 8, 54, 32, 607000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'did have trai no eny complain'},
       {'datetime': datetime(2014, 10, 2, 11, 32, 36, 197000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'D hospital was quite okey and i think u should add more hospital materials.'},
       {'datetime': datetime(2014, 10, 6, 15, 8, 22, 646000, tzinfo=UTC),
        'question': u'General Feedback',
        'response': u'D hospital was well organised,clean n healthy'},
       {'datetime': datetime(2014, 10, 20, 8, 34, 41, 551583, tzinfo=UTC),
        'question': 'General Feedback',
        'response': u'PHC NAKERE WAMBA LGC 2 For NO'}]

    class Clinic(object):
        def __init__(self):
            self.name = 'Gwagi PHC'
            self.lga = 'Wamba'
    
    context = {
        'clinic': Clinic(),
        'response_stats': responses,
        'feedback_by_service': svc_feedback,
        'detailed_comments': comments,
        'feedback_stats': stats,
        'feedback_clinics': categories,
        'num_registered': 329,
        'num_started': 33,
        'num_completed': 20,
        'min_date': min_date,
        'max_date': max_date,
    }

    report = FacilityReportPdf()
    flowables = report.render_to_list(context)
    with open('sample.pdf', 'w') as outfile:
        report.render(flowables, outfile)
