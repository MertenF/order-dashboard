from datetime import datetime

# starts with
base_products = [
    'Mosselen',
    'Balletjes',
    'Vegan Balletjes',
    'Scoutsbootje',
    'Salade - Ham',
    'Salade - Geroosterde',
    'Salade - Tomaat',
]

products = {
    'Mosselen': {

    },
    'Balletjes': {

    },
    'Vegan Balletjes': {
        'display': 'Vegan Bal',
    },
    'Scoutsbootje': {

    },
    'Salade - Ham': {
        'display': 'SALAD Ham',
        'font_scale': 0.5,
    },
    'Salade - Geroosterde': {
        'display': 'SALAD Kikkererwt',
        'font_scale': 0.5,
    },
    'Salade - Tomaat': {
        'display': 'SALAD Tom-Moz',
        'font_scale': 0.5,
    },
}

username = 'dorst_kassa@scoutswvb.be'
password = ''

shift_starts = [
    datetime(2024, 8, 13, 17, 0),   # error prevent
    datetime(2024, 8, 16, 17, 30),  # VR AV
    datetime(2024, 8, 17, 16, 30),  # ZA AV
    datetime(2024, 8, 18, 11, 0),   # ZO MI
    datetime(2024, 8, 18, 16, 30),  # ZO AV
]
