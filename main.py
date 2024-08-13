#!/usr/bin/python
import re
import time
import threading
from datetime import datetime, timedelta

from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput

import config
import billy

import kivy
kivy.require('2.1.0')
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.actionbar import ActionBar
from kivy.clock import Clock, mainthread

from kivy.core.window import Window

SCALE = 1
Window.size = (1080*SCALE, 1920*SCALE)

order_id = None
wait_time = None


class ProductLabel(Label):
    pass


class AmountLabel(Label):
    pass


class OrderDashboard(GridLayout):
    font_size = 110*SCALE
    amount_width = 290*SCALE
    padding_sides = int(40 * SCALE)
    totals_height = 400*SCALE
    cols = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.thread = None

        self.labels_amount = {}
        for product, product_config in config.products.items():
            label = ProductLabel(
                text=product_config.get('display', product),
                font_size=self.font_size * product_config.get('font_scale', 1),
                padding=(self.padding_sides, 0, 0, 0)
            )
            #label.bind(size=label.setter('text_size'))
            self.add_widget(label)

            amount = AmountLabel(text='0', font_size=self.font_size*product_config.get('font_scale', 1), size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0))
            self.labels_amount[product] = amount
            self.add_widget(amount)

        self.add_widget(ProductLabel(text='Totaal', font_size=self.font_size, padding=(self.padding_sides, 0, 0, 0), size_hint_y=None, height=self.totals_height))
        total = AmountLabel(text='0', font_size=self.font_size, size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0), size_hint_y=None, height=self.totals_height)
        self.labels_amount['Totaal'] = total
        self.add_widget(total)

        self.start_update_thread()  # initialise values

    def start_update_thread(self, dt=None):
        threading.Thread(target=self.update_thread).start()

    def update_thread(self):
        try:
            orders = billy.order_data(start_of_shift())
            global wait_time
            ordered_products, wait_time = billy.count_products(orders, config.products.keys(), order_id)
        except Exception as e:
            print(e)
            return
        self.update_amounts(ordered_products)

    @mainthread
    def update_amounts(self, ordered_products):

        print(ordered_products)

        for product, amount in ordered_products.items():
            self.labels_amount[product].text = str(amount)
        self.labels_amount['Totaal'].text = str(sum(ordered_products.values()))


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

    def set_statistics(self, dt=None):
        text = f'Order: #{order_id}\n'
        if wait_time:
            w = int(wait_time.total_seconds/60)
        else: w = 0
        text += f'Wachtijd: {w} min'

        self.ids.stat_label.text = text


class RefreshBar(ProgressBar):
    def update(self, dt):
        self.value += dt
        print(f'{self.value} {self.max}')



class DashboardApp(App):
    thread = None
    
    def build(self):
        layout = BoxLayout(orientation='vertical')

        status = StatusBar()
        layout.add_widget(status)
        Clock.schedule_interval(status.set_time, 0.2)
        Clock.schedule_interval(status.set_statistics, 1)

        self.dashboard = OrderDashboard()
        layout.add_widget(self.dashboard)
        Clock.schedule_interval(self.start_update_thread, 7)

        self.progress = ProgressBar(max=10, size_hint_y=None, height=50*SCALE)
        layout.add_widget(self.progress)
        Clock.schedule_interval(self.update_progress, 1/60)

        return layout


    def update_progress(self, dt):
        self.progress.value += dt


    def start_update_thread(self, dt=None):
        if self.thread and self.thread.is_alive():
            print('Previous thread is still running!')
            return
        self.thread = threading.Thread(target=self.update)
        self.thread.start()

    def update(self):
        self.dashboard.update_thread()
        self.progress.value = 0

if __name__ == '__main__':
    DashboardApp().run()
