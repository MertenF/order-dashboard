import os
from datetime import datetime


def _load_env_file(path='.env'):
    """Load KEY=VALUE lines from a .env file next to this module into os.environ (existing vars win)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


_load_env_file()

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

# Billy manager credentials, set in the environment or in .env (see .env.example)
username = os.environ.get('BILLY_USERNAME')
password = os.environ.get('BILLY_PASSWORD')

vlms24 = [
    datetime(2024, 8, 13, 17, 0),   # error prevent
    datetime(2024, 8, 16, 17, 30),  # VR AV
    datetime(2024, 8, 17, 16, 30),  # ZA AV
    datetime(2024, 8, 18, 11, 0),   # ZO MI
    datetime(2024, 8, 18, 16, 30),  # ZO AV
]

mf25 = [
    datetime(2025, 11, 8, 8,0),
    datetime(2025, 11, 8, 16,0),
    datetime(2025, 11, 9, 9,0),
    datetime(2025, 11, 9, 16,0),
]

vlms25 = [
    datetime(2026, 8, 21, 16, 0),
#    datetime(2026, 8, 22, 9, 0),
#    datetime(2026, 8, 23, 9, 0),
#    datetime(2026, 8, 24, 16, 0),
]

shift_starts = vlms25