from datetime import datetime

# starts with
base_products = [
    'Mosselen',
    'Balletjes',
    'Scoutsbootje',
    'Veganschuit',
    'Vegan Balletjes',
]

products = {
    'Mosselen': {

    },
    'Balletjes': {

    },
    'Scoutsbootje': {

    },
    'Veganschuit': {
        'display': 'Schuit',
    },
    'Vegan Balletjes': {
        'display': 'Vegan Bal',
    },
}

username = 'dorst_kassa@scoutswvb.be'
password = ''

vlms24 = [
    datetime(2024, 8, 13, 17, 0),   # error prevent
    datetime(2024, 8, 16, 17, 30),  # VR AV
    datetime(2024, 8, 17, 16, 30),  # ZA AV
    datetime(2024, 8, 18, 11, 0),   # ZO MI
    datetime(2024, 8, 18, 16, 30),  # ZO AV
]

mf24 = [
    datetime(2024, 11, 9, 8,0),
    datetime(2024, 11, 9, 16,0),
    datetime(2024, 11, 10, 9,0),
    datetime(2024, 11, 10, 16,0),
]

shift_starts = mf24