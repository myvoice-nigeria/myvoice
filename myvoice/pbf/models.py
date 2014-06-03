

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
        'progress': [
            ('Performance Summary', [
                ('Income', '722,652', 4),
                ('Quality Score', '96.6%', 1),
                ('Patient Satisfaction', '87%', 1),
            ]),
            ('Patients', [
                ('Total Patients seen', None, 4),
                ('Outreach', 320, 1),
                ('In Facility', None, 3),
                ('Indigents', 35, 3),
            ]),
            ('Services', [
                ('New Out Patient', 'x', 1),
                ('Normal Delivery', 'x', 1),
                ('Child Immunization / Vaccination', 'x', 1),
                ('Immunization or vaccination', 'x', 1),
                ('Tests', 'x', 1),
                ('Other\n(Including Antenatal Care)', 'x', 1),
            ]),
            ('Feedback', [
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
                ('income', '938,238', 2),
                ('Quality Score', '94.0%', 2),
                ('Patient Satisfaction', '87%', 1),
            ]),
            ('Patients', [
                ('Total Patients seen', None, 4),
                ('Outreach', 320, 1),
                ('In Facility', None, 3),
                ('Indigents', 35, 3),
            ]),
            ('Services', [
                ('New Out Patient', None, None),
                ('Normal Delivery', None, None),
                ('Child Immunization / Vaccination', None, None),
                ('Immunization or vaccination', None, None),
                ('Tests', None, None),
                ('Other\n(Including Antenatal Care)', None, None),
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
