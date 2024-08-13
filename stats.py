from datetime import datetime

import pandas
import seaborn as sns
import matplotlib.pyplot as plt

import billy

sns.set_theme()


def main():
    orders = billy.order_data(
        start=datetime(2023, 11, 4, 17, 0),
        end=datetime(2023, 11, 4, 22, 0),
    )
    pandas.options.display.width = 0
    orders['Product Name'] = orders['Product Name'].replace(
        regex=True,
        to_replace=['Balletjes.*', 'Mosselen.*', 'Scoutsbootje.*', 'Goulash.*'],
        value=['Balletjes', 'Mosselen', 'Scoutsbootje', 'Goulash'],
    )
    orders = orders[orders['Product Name'].isin(['Balletjes', 'Mosselen', 'Scoutsbootje', 'Goulash'])]
    orders = orders[['Ordered at', 'Product Name', 'Product Amount']]
    orders = orders.sort_values(by=['Ordered at'])
    print(orders.resample('30m', on='Ordered at').mean())


    df = orders
    df['cumsum'] = df.groupby('Product Name')['Product Amount'].transform(pandas.Series.cumsum)
    print(df)

    #print(orders[orders['Product Name'] == 'Pils'].cumsum("Product Amount"))

    sns.relplot(data=df, y="cumsum", x="Ordered at", hue="Product Name", kind='line')




if __name__ == '__main__':
    main()
    plt.show()