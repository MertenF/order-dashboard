#!/usr/bin/python
import re
import time
import threading
import traceback
from datetime import datetime, timedelta

from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from pandas import DataFrame

import config
import billy

import kivy
kivy.require('2.3.0')
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.actionbar import ActionBar
from kivy.clock import Clock, mainthread

from kivy.core.window import Window

SCALE = 0.3
Window.size = (1080*SCALE, 1920*SCALE)

order_id = None
wait_time = None
last_updated = None


class ProductLabel(Label):
    pass


class AmountLabel(Label):
    pass


class OrderDashboard(GridLayout):
    font_size = sp(110*SCALE)
    amount_width = 290*SCALE
    padding_sides = int(40 * SCALE)
    totals_height = 400*SCALE
    cols = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.thread = None
        self.orders = None

        self.labels_current_amount = {}
        self.labels_total_amount = {}
        for product, product_config in config.products.items():
            label = ProductLabel(
                text=product_config.get('display', product),
                font_size=self.font_size * product_config.get('font_scale', 1),
                padding=(self.padding_sides, 0, 0, 0)
            )
            #label.bind(size=label.setter('text_size'))
            self.add_widget(label)

            curr_amount = AmountLabel(font_size=self.font_size*product_config.get('font_scale', 1), size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0))
            self.labels_current_amount[product] = curr_amount
            self.add_widget(curr_amount)

            tot_amount = AmountLabel()


        self.add_widget(ProductLabel(text='Totaal', font_size=self.font_size, padding=(self.padding_sides, 0, 0, 0), size_hint_y=None, height=self.totals_height))
        total = AmountLabel(text='0000', font_size=self.font_size, size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0), size_hint_y=None, height=self.totals_height)
        self.labels_current_amount['Totaal'] = total
        self.add_widget(total)

    def update_thread(self):
        self.orders = billy.order_data(start_of_shift())
        self.update_orders_display()

    def update_orders_display(self):
        """Recalculate the orders"""
        global wait_time, last_updated
        if self.orders is None:  # first download hasn't finished yet; it will apply order_id when it does
            return
        ordered_products, wait_time = billy.count_products(self.orders, config.products.keys(), order_id)
        last_updated = datetime.now()

        self.update_amounts(ordered_products)

    @mainthread
    def update_amounts(self, ordered_products):

        print(ordered_products)

        for product, amount in ordered_products.items():
            self.labels_current_amount[product].text = str(amount)
        self.labels_current_amount['Totaal'].text = str(sum(ordered_products.values()))


def start_of_shift() -> datetime:
    now = datetime.now()
    for shift_start in config.shift_starts[::-1]:
        if now > shift_start:
            return shift_start
    return config.shift_starts[0]


class StatusBar(BoxLayout):
    clock = StringProperty('xx:xx:xx')

    def __init__(self):
        super().__init__()
        self.ids.order_input.bind(on_text_validate=self.on_enter)


    def set_time(self, dt=None):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        self.clock = current_time

    def on_enter(self, value: TextInput):
        try:
            num = int(value.text)
        except Exception:
            num = None
        print(f'Order number input: {num}')
        global order_id
        order_id = num

        value.text = ''

        app = App.get_running_app()
        app.dashboard.update_orders_display()
        self.set_statistics()


    def set_statistics(self, dt=None):
        text = f'Order: #{order_id}\n'
        if wait_time:
            text += f'Wachtijd: {wait_time} min'
            ago = datetime.now() - last_updated
            ago_min = int(ago.total_seconds()/60)
            text += f'\nUpdate {ago_min} min geleden'

        self.ids.stat_label.text = text


class RefreshBar(ProgressBar):
    def update(self, dt):
        self.value += dt
        print(f'{self.value} {self.max}')



class DashboardApp(App):
    def __init__(self):
        super().__init__()

        Window.bind(on_resize=self.on_window_resize)
        self.thread = None
    
    def build(self):
        layout = BoxLayout(orientation='vertical')

        status = StatusBar()
        layout.add_widget(status)
        Clock.schedule_interval(status.set_time, 0.2)
        Clock.schedule_interval(status.set_statistics, 10)

        self.dashboard = OrderDashboard()
        layout.add_widget(self.dashboard)
        Clock.schedule_interval(self.start_update_thread, 7)

        self.progress = ProgressBar(max=10, size_hint_y=None, height=50*SCALE)
        layout.add_widget(self.progress)
        Clock.schedule_interval(self.update_progress, 1/60)

        self.start_update_thread()  # initialise values

        return layout


    def update_progress(self, dt):
        self.progress.value += dt


    def start_update_thread(self, dt=None):
        if self.thread and self.thread.is_alive():
            print('Previous thread is still running!')
            return
        # daemon, so a hanging request doesn't keep the process alive after the window is closed
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        try:
            self.dashboard.update_thread()
        except Exception:
            # Keep showing the last known amounts; the next scheduled update retries
            traceback.print_exc()
        finally:
            self.reset_progress()

    @mainthread
    def reset_progress(self):
        self.progress.value = 0

    def on_window_resize(self, window, width, height):
        print(window, width, height)


if __name__ == '__main__':
    DashboardApp().run()
