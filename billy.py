from collections import Counter
import requests

import config


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
        for product in order['products']:
            products_count[product['name']] += product['amount']
    return products_count


def get_product_count():
    import time
    time.sleep(1)
    return Counter({'Mosselen': 99, 'Balletjes': 888, 'Goulash': 123, 'Scoutsbootje': 111})
    
    
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
