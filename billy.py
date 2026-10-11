import zipfile
import xml.etree.ElementTree as ElementTree
from collections import Counter
from io import BytesIO
from typing import Dict, Iterator, List, NamedTuple, Optional, Sequence, Tuple
from datetime import datetime, timedelta

import requests

import config

# Seconds to connect and to wait for an answer before a Billy request is abandoned, so a hung connection
# can't stall the dashboard. Connecting takes well under a second; a short connect timeout means an
# attempt stuck on a network that is still coming up (at boot) is retried soon instead of after 30 s.
TIMEOUT = (3, 30)

# Logged-in session reused between order_data() calls
_session = None


def fetch_data(session: requests.Session, report_type: str, start: datetime, end: datetime) -> bytes:
    valid_types = ('orders', 'orders_products', 'day', 'day_products', 'products', 'takeout')

    if report_type not in valid_types:
        raise ValueError(f'{report_type=} is not a valid value!')
    if start > end:
        raise ValueError(f'start should happen before end! {start=} {end=}')

    r = session.post(
        url='https://manager.orderbilly.com/reports/report_download',
        params={
            'type': report_type,
            'from': start.strftime('%y-%m-%d %H:%M:%S'),
            'till': end.strftime('%y-%m-%d %H:%M:%S'),
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    print('Data downloaded')

    return r.content


def billy_session(username: str, password: str) -> requests.Session:
    if not username or not password:
        raise RuntimeError('Billy credentials missing: set BILLY_USERNAME and BILLY_PASSWORD in the environment or .env')

    session = requests.Session()

    r = session.post(
        url='https://manager.orderbilly.com/index_receive.php',
        data={
            'manager_email': username,
            'manager_password': password
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    # Billy gives status code 200 when failing an authentication request.
    # By checking the redirection url, it is possible to detect if the login failed.
    # Success: https://manager.orderbilly.com/dashboard/start
    # Failed: https://manager.orderbilly.com/?pass=no
    if 'dashboard' not in r.url:
        raise requests.exceptions.HTTPError("Login has failed")

    print("Session created")

    return session


class OrderLine(NamedTuple):
    """One product line of an order in the orders_products report"""
    order_id: int
    ordered_at: datetime
    product_name: str
    amount: int


# Report columns used, in OrderLine order
COLUMNS = ('Order ID', 'Ordered at', 'Product Name', 'Product Amount')

XLSX_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
EXCEL_EPOCH = datetime(1899, 12, 30)  # Excel stores date-times as days since this date


def xlsx_rows(data: bytes) -> Iterator[Dict[str, str]]:
    """Rows of the first sheet of an xlsx file as {column letter: text}; shared strings are resolved,
    numbers and dates are left as their text (dates as Excel day numbers).

    Reads the XML directly instead of using pandas/openpyxl: on the Raspberry Pi that is several times
    faster and avoids loading pandas and numpy (seconds at boot from the SD card)."""
    with zipfile.ZipFile(BytesIO(data)) as xlsx:
        shared = []
        if 'xl/sharedStrings.xml' in xlsx.namelist():
            for item in ElementTree.fromstring(xlsx.read('xl/sharedStrings.xml')).iter(f'{XLSX_NS}si'):
                shared.append(''.join(t.text or '' for t in item.iter(f'{XLSX_NS}t')))
        with xlsx.open('xl/worksheets/sheet1.xml') as sheet:
            for _, row in ElementTree.iterparse(sheet):
                if row.tag != f'{XLSX_NS}row':
                    continue
                values = {}
                for cell in row.iter(f'{XLSX_NS}c'):
                    column = cell.get('r').rstrip('0123456789')
                    kind = cell.get('t')
                    if kind == 'inlineStr':
                        values[column] = ''.join(t.text or '' for t in cell.iter(f'{XLSX_NS}t'))
                        continue
                    value = cell.find(f'{XLSX_NS}v')
                    if value is None or value.text is None:
                        continue
                    values[column] = shared[int(value.text)] if kind == 's' else value.text
                yield values
                row.clear()  # keep memory flat on long reports


def parse_orders(data: bytes) -> List[OrderLine]:
    """Order lines from an orders_products report: a title row, a header row, then one row per product line"""
    rows = xlsx_rows(data)
    next(rows, None)  # title ("Report for orders with products ...")
    header = next(rows, {})
    columns = {name: letter for letter, name in header.items()}
    missing = [name for name in COLUMNS if name not in columns]
    if missing:
        raise ValueError(f'Billy report without columns {missing}')
    id_col, at_col, name_col, amount_col = (columns[name] for name in COLUMNS)

    lines = []
    for row in rows:
        if id_col not in row or at_col not in row or name_col not in row:
            continue
        lines.append(OrderLine(
            order_id=int(float(row[id_col])),
            ordered_at=EXCEL_EPOCH + timedelta(days=float(row[at_col])),
            product_name=row[name_col],
            amount=int(float(row.get(amount_col, 0))),
        ))
    return lines


def order_data(start: datetime, end: datetime = None) -> List[OrderLine]:
    if not end:
        end = datetime.now() + timedelta(days=1)

    global _session

    for attempt in range(2):
        if _session is None:
            _session = billy_session(config.username, config.password)
        try:
            data = fetch_data(_session, 'orders_products', start, end)
            return parse_orders(data)
        except Exception:
            # The session may have expired, in which case Billy serves a page instead of the report.
            # Drop it and log in again once before giving up.
            _session.close()
            _session = None
            if attempt:
                raise


def has_order(orders: List[OrderLine], order_id: int) -> bool:
    return any(line.order_id == order_id for line in orders)


def count_products(orders: List[OrderLine], filters: Sequence, order_id: int = None, since: datetime = None) -> Tuple[Counter, Optional[int]]:
    """Count ordered products per filter prefix. With order_id (or since) only orders placed after that
    order (or time) are counted, and the wait time is the minutes since then."""
    wait_time_min = None

    if order_id:
        since = next((line.ordered_at for line in orders if line.order_id == order_id), since)

    if since is not None:
        wait_time = datetime.now() - since
        wait_time_min = int(wait_time.total_seconds()/60)
        print(f"Showing orders after {since}. Wait time: {wait_time_min}min")

        orders = [line for line in orders if line.ordered_at > since]

    # Sum of product amount for each product name
    summed = Counter()
    for line in orders:
        summed[line.product_name] += line.amount

    product_counter = Counter()
    for product in filters:
        # prefix match, so variants like "Mosselen natuur" count as "Mosselen"
        product_counter[product] = sum(amount for name, amount in summed.items() if name.startswith(product))

    return product_counter, wait_time_min


def main():
    orders = order_data(
        start=datetime(2023, 11, 1),
        end=datetime(2023, 11, 10),
    )
    print(count_products(orders, config.base_products))


if __name__ == '__main__':
    main()
