from django.conf import settings
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, PageBreak, Paragraph, KeepTogether, Table, TableStyle
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


class Bookmark(Flowable):

    def __init__(self, title):
        self.title = title
        Flowable.__init__(self)

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        self.canv.bookmarkPage(self.title)
        self.canv.addOutlineEntry(
            self.title, self.title, 0, 0)


class ReportPdfRenderer(object):

    def summary(self, clinic, sent, started, completed):
        """Renders the Facility Report Summary section."""
        p_started = ((float(started) / sent) * 100) if sent else 0
        p_completed = ((float(completed) / sent) * 100) if sent else 0
        summary_tbl = Table([
            (p('<b>SURVEY PARTICIPATION</b>'), '', ''),
            (p('%s' % sent),
             p('%s (%.0f%%)' % (started, p_started)),
             p('%s (%.0f%%)' % (completed, p_completed))),
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
            ('BACKGROUND', (-1, -1), (-1, -1), colors.grey.clone(alpha=0.1)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return tbl

    def facility_chart(self, clinic, stats, clinics):
        """Renders the Facility Participation Chart."""
        flowables = []
        flowables.append(heading('Participation By Facility'))
        flowables.append(p("""Number of patients who received, started,
                           and completed surveys across %s.""" % clinic.name))
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
        flowables.append(p("""<para spaceafter=12>Summary of patient feedback responses
                           compared to LGA-wide averages.</para>"""))
        rows = [('Patients from %s said:' % clinic.name, '', '',
                 'Patients from other facilities said:', '', '')]
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
        flowables.append(p("""<para spaceafter=12>Number of patients with this service,
                           who reported this feedback.</para>"""))
        if data:
            service, feedback = data[0]
            if min_date and max_date:
                rows = [['%s to %s' % (min_date.strftime('%B %d, %Y'),
                                       max_date.strftime('%B %d, %Y'))
                         ] + ['\n'.join(x[0].split()) for x in feedback]]
            else:
                rows = [[''] + ['\n'.join(x[0].split()) for x in feedback]]
            for service, feedback in data:
                row = [service] + ['%s (%s)' % ('0' if not x else x, 0 if y is None else y)
                                   for _, x, y in feedback[:-1]] + [
                    '%s (%s)' % ('N/A' if not x else x, 0 if y is None else y)
                    for _, x, y in feedback[-1:]]
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

    def detailed_comments(self, min_date, max_date, data):
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
        if min_date and max_date:
            # Filter out comments outside the displayed date range:
            data = (x for x in data if min_date <= x['datetime'] <= max_date)
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
        elements.append(Bookmark(str(ctx['clinic'])))
        elements.append(self.summary(
            ctx['clinic'], ctx['num_registered'], ctx['num_started'], ctx['num_completed']))
        elements.append(self.facility_chart(
            ctx['clinic'], ctx['feedback_stats'], ctx['feedback_clinics']))
        elements.append(self.feedback_responses(ctx['clinic'], ctx['response_stats']))
        elements.append(self.feedback_on_servies(
            ctx['min_date'], ctx['max_date'], ctx['feedback_by_service']))
        elements.extend(self.detailed_comments(
            ctx['min_date'], ctx['max_date'], ctx['detailed_comments']))
        elements.append(page_break())
        return elements

    def render_to_response(self, flowables, outfile):
        """Renders a list of flowables as a PDF to the specified `outfile`."""
        doc = SimpleDocTemplate(outfile)
        doc.build(flowables, onFirstPage=add_page_number, onLaterPages=add_page_number)
        return outfile
