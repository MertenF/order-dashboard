from collections import Counter
from typing import Sequence, Tuple
from datetime import datetime, timedelta

import requests
import numpy as np
import pandas

import config


def fetch_data(session: requests.Session, report_type: str, start: datetime, end: datetime) -> bytes:
    valid_types = ('orders', 'orders_products', 'day', 'day_products', 'products', 'takeout')

    if report_type not in valid_types:
        raise ValueError(f'{report_type=} is not a valid value!')
    if start > end:
        raise ValueError('start should happen before end!')

    r = session.post(
        url='https://manager.orderbilly.com/reports/report_download',
        params={
            'type': report_type,
            'from': start.strftime('%y-%m-%d %H:%M:%S'),
            'till': end.strftime('%y-%m-%d %H:%M:%S'),
        },
    )
    r.raise_for_status()
    print('Data downloaded')

    return r.content


def billy_session(username: str, password: str) -> requests.Session:
    session = requests.Session()

    r = session.post(
        url='https://manager.orderbilly.com/index_receive.php',
        data={
            'manager_email': username,
            'manager_password': password
        },
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


def order_data(start: datetime, end: datetime = None) -> pandas.DataFrame:
    if not end:
        end = datetime.now() + timedelta(days=1)

    with billy_session(config.username, config.password) as s:
        data = fetch_data(s, 'orders_products', start, end)

    cols = ['Menu', 'Prep Location', 'Order ID', 'Ordered at', 'Total Price', 'Table Number', 'User', 'PSP', 'Payment',
            'Product Amount', 'Product Name', 'Additions']
    orders = pandas.read_excel(data, header=1, usecols=cols)

    return orders


def count_products(orders: pandas.DataFrame, filters: Sequence, order_id: int = None) -> Tuple[Counter, datetime]:
    wait_time = None
    if order_id and order_id in orders['Order ID'].values:
        order_time = orders[orders['Order ID'] == order_id]['Ordered at'].values[0]
        wait_time = datetime.now() - order_time
        print(f"Got order ID {order_id}. Only showing orders after {np.datetime_as_string(order_time, unit='s')}")
        orders = orders[orders['Ordered at'] > order_time]

    # Sum of product amount for each product name
    summed = orders.groupby('Product Name')['Product Amount'].sum()

    product_counter = Counter()
    for product in filters:
        product_count = summed.filter(regex=f'^{product}').sum()
        #print(f"Product '{product}' has been ordered {product_count} times")
        product_counter[product] = int(product_count)

    return product_counter, wait_time


def main():
    orders = order_data(
        start=datetime(2023, 11, 1),
        end=datetime(2023, 11, 10),
    )
    print(count_products(orders, config.base_products))


if __name__ == '__main__':
    main()
