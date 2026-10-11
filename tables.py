import urllib.parse
from multiprocessing.managers import Value
from pprint import pprint

import requests
from bs4 import BeautifulSoup

import billy
import config

table_path = 'https://manager.orderbilly.com/tables/accessandsorting_sorting_receive.php'
data = 'sortedTables%5B%5D=168582&sortedTables%5B%5D=168583&sortedTables%5B%5D=168584&sortedTables%5B%5D=168585&sortedTables%5B%5D=168586&sortedTables%5B%5D=168587&sortedTables%5B%5D=168588&sortedTables%5B%5D=168589&sortedTables%5B%5D=168590&sortedTables%5B%5D=168591&sortedTables%5B%5D=168592&sortedTables%5B%5D=168593&sortedTables%5B%5D=168594&sortedTables%5B%5D=168595&sortedTables%5B%5D=168596&sortedTables%5B%5D=168597&sortedTables%5B%5D=168598&sortedTables%5B%5D=168599&sortedTables%5B%5D=168600&sortedTables%5B%5D=168601&sortedTables%5B%5D=168602&sortedTables%5B%5D=168603&sortedTables%5B%5D=168604&sortedTables%5B%5D=168605&sortedTables%5B%5D=168606&sortedTables%5B%5D=168607&sortedTables%5B%5D=168608&sortedTables%5B%5D=168609&sortedTables%5B%5D=168610&sortedTables%5B%5D=168611&sortedTables%5B%5D=168612&sortedTables%5B%5D=168613&sortedTables%5B%5D=168614&sortedTables%5B%5D=168615&sortedTables%5B%5D=168616&sortedTables%5B%5D=168617&sortedTables%5B%5D=168618&sortedTables%5B%5D=168619&sortedTables%5B%5D=168620&sortedTables%5B%5D=168621&sortedTables%5B%5D=168622&sortedTables%5B%5D=168623&sortedTables%5B%5D=168624&sortedTables%5B%5D=168625&sortedTables%5B%5D=168626&sortedTables%5B%5D=168627&sortedTables%5B%5D=168628&sortedTables%5B%5D=168629&sortedTables%5B%5D=168630&sortedTables%5B%5D=168631&sortedTables%5B%5D=168632&sortedTables%5B%5D=168633&sortedTables%5B%5D=168634&sortedTables%5B%5D=168635&sortedTables%5B%5D=168636&sortedTables%5B%5D=168637&sortedTables%5B%5D=168638&sortedTables%5B%5D=168639&sortedTables%5B%5D=168640&sortedTables%5B%5D=168641&sortedTables%5B%5D=168642&sortedTables%5B%5D=168647&sortedTables%5B%5D=168648&sortedTables%5B%5D=168649&sortedTables%5B%5D=168650&sortedTables%5B%5D=168651&sortedTables%5B%5D=168652&sortedTables%5B%5D=168653&sortedTables%5B%5D=168654&sortedTables%5B%5D=168655&sortedTables%5B%5D=168656&sortedTables%5B%5D=168657&sortedTables%5B%5D=168658&sortedTables%5B%5D=168659&sortedTables%5B%5D=168660&sortedTables%5B%5D=168661&sortedTables%5B%5D=219831&sortedTables%5B%5D=219832&sortedTables%5B%5D=219841&sortedTables%5B%5D=219842&sortedTables%5B%5D=219851&sortedTables%5B%5D=219852&sortedTables%5B%5D=219861&sortedTables%5B%5D=219862&sortedTables%5B%5D=220665&sortedTables%5B%5D=220666&sortedTables%5B%5D=220667&sortedTables%5B%5D=220668&sortedTables%5B%5D=168645&sortedTables%5B%5D=168644'

def set_table_sorting(session: requests.Session, tid_sorted: list):
    payload = {
        'sortedTables[]': tid_sorted
    }
    r = session.post(
        url=table_path,
        data=payload,
        timeout=billy.TIMEOUT,
    )
    print('Setting table sorting: ', end='')
    r.raise_for_status()
    print(r)


def fetch_table(session: requests.Session):
    r = session.get(
        url='https://manager.orderbilly.com/tables/accessandsorting',
        timeout=billy.TIMEOUT,
    )
    print('Fetching current table list: ', end='')
    print(r)

    soup = BeautifulSoup(r.text, 'html.parser')
    table_list = soup.find_all('div', {'class': 'list-group-item'})
    tables = {}
    for table in table_list:
        tid = table['data-id']
        name = str(table.find(class_='col-4').contents[0])
        name = name.strip()

        tables[name] = tid

    return tables


def table_to_num(table: tuple):
    table_num = table[0].removeprefix('TAFEL').strip()
    try:
        return int(table_num)
    except ValueError:
        return 999


def main():
    # pprint(urllib.parse.unquote(data).split('&sortedTables[]='))

    with billy.billy_session(config.username, config.password) as s:
        tables = fetch_table(s)
        print(tables)
        tables_sorted = dict(sorted(tables.items(), key=table_to_num))
        print(tables_sorted)

        set_table_sorting(s, list(tables_sorted.values()))


if __name__ == '__main__':
    main()