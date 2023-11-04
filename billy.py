from collections import Counter
import requests
from datetime import datetime

import config


zat_start = datetime(2023, 11, 4, 14, 0)
zon_mi = datetime(2023, 11, 5, 10, 0)
zon_av = datetime(2023, 11, 5, 15, 30)

def get_billy_data_json():
    headers = {'Authorization': config.auth_key}

    res = requests.get(
        config.api_url,
        headers=headers,
    )
    return res.json()


def orders_sum(data):
    products_count = Counter()
    for order in data['data']:
        print(f'{order=}')
        # 2023-10-22T23:15:45+02:00
        order_time = datetime.strptime(order['created_at'], '%Y-%m-%dT%H:%M:%S+01:00')
        print(f'{order_time=}')
        current_time = datetime.now()

        if current_time > zon_av > order_time:
            print('zon av')
            continue
        elif current_time > zon_mi > order_time:
            print('zon mi')
            continue
        elif current_time > zat_start > order_time:
            print('zaterdag')
            continue

        for product in order['products']:
            products_count[product['name']] += product['amount']
    return products_count


def get_product_count():
    import time
    #time.sleep(1)
    #return Counter({'Mosselen': 99, 'Balletjes': 888, 'Goulash': 123, 'Scoutsbootje': 111})
    
    
    ret_dict = Counter()

    billy_data = get_billy_data_json()
    product_count = orders_sum(billy_data)
    print(product_count)

    for product, amount in product_count.items():
        for base_product in config.base_products:
            if base_product.lower() in product.lower():
                ret_dict[base_product] += amount
                continue
    return ret_dict


if __name__ == '__main__':
    print(get_product_count())
