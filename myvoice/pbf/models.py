

# Reference for clinic data until we set up a model structure.
CLINIC_DATA = {
    'arum-chugbu-phc': {
        'name': 'Arum Chugbu PHC',
        'slug': 'arum-chugbu-phc',
    },
    'gwagi-phc': {
        'name': 'Gwagi PHC',
        'slug': 'gwagi-phc',
    },
    'kwabe-phc': {
        'name': 'Kwabe PHC',
        'slug': 'kwabe-phc',
    },
    'kwarra-phc': {
        'name': 'Kwarra PHC',
        'slug': 'kwarra-phc',
    },
    'maraba-gongon-phc': {
        'name': 'Maraba Gongon PHC',
        'slug': 'maraba-gongon-phc',
    },
    'nakere-phc': {
        'name': 'Nakere PHC',
        'slug': 'nakere-phc',
    },
    'wamba-general-hospital': {
        'name': 'Wamba General Hospital',
        'slug': 'wamba-general-hospital',
    },
    'wayo-matti-phc': {
        'name': 'Wayo Matti PHC',
        'slug': 'wayo-matti-phc',
        'year_founded': '2011',
        'show_feedback': False,
        'incharge': {
            'name': 'DPHC, Ezekiel Jagga',
            'years_at_clinic': '5',
            'contact_numbers': '0814 339 9384\n 0808 711 2929',
        },
        'progress': [  # Q4 2013
            ('Performance Summary', [
                ('Income', '59,959', 3),
                ('Quality Score', '96.8', 1),
                ('Patient Satisfaction', None, None),
            ]),
            ('Patients', [
                ('Total Patients seen', None, 4),
                ('Outreach', 320, 1),
                ('In Facility', None, 3),
                ('Indigents', 35, 3),
            ]),
            ('Services', [
                ('Normal Delivery', '24.5%', None),
                ('New Outpatient Consultation', '18.2%', None),
                ('Family Planning', '13.8%', None),
                ('Completely Vaccinated Child', '7.7%', None),
                ('VCT/PMTCT/PIT tests', '7.6%', None),
                ('Other Services', '28.2%', None),
            ]),
            ('Feedback', [  # to be collected from TextIt
                ('Staff Treatment', '74%', 2),
                ('Affordable Drugs', '89%', 3),
                ('Avg. Wait Time', '1 hr.', 3),
            ]),
        ],
    },
    'wamba-phc-model-clinic': {
        'name': 'Wamba PHC Model Clinic',
        'slug': 'wamba-phc-model-clinic',
        'incharge': {
            'name': 'Juliana',
            'years_at_clinic': '5',
            'contact_numbers': '0814 339 9384\n0808 711 2929',
        },
        'year_founded': '2008',
        'facility_staff': [
            ('CHEW', 4),
            ('LAB Tech', 1),
            ('Attendants', 3),
            ('Midwives', 2),
            ('Volunteers', 16),
        ],
        'total_positions': 26,
        'show_feedback': True,
        'progress': [
            ('Performance Summary', [
                ('Income', '79,387', 2),
                ('Quality Score', '94.4%', 2),
                ('Patient Satisfaction', None, None),
            ]),
            ('Patients', [
                ('Total Patients seen', None, 4),
                ('Outreach', 320, 1),
                ('In Facility', None, 3),
                ('Indigents', 35, 3),
            ]),
            ('Services', [
                ('Normal Delivery', '21.7%', None),
                ('New Outpatient Consultation', '14.7%', None),
                ('Family Planning', '13.6%', None),
                ('VCT/PMTCT/PIT Tests', '9.4%', None),
                ('STD Treatment', '8.3%', None),
                ('Other Services', '32.3%', None),
            ]),
            ('Feedback', [
                ('Staff Treatment', '74%', 2),
                ('Affordable Drugs', '89%', 3),
                ('Avg. Wait Time', '1 hr.', 3),
            ]),
        ],
    },
    'yashi-madaki-phc': {
        'name': 'Yashi Madaki PHC',
        'slug': 'yashi-madaki-phc',
    },
    'zalli-phc': {
        'name': 'Zalli PHC',
        'slug': 'zalli-phc',
    },
}
