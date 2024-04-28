#!/usr/bin/python

import time
import threading
from datetime import datetime, timedelta

from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar

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

SCALE = 0.5
Window.size = (1024*SCALE, 1280*SCALE)


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
        for product in config.base_products:
            label = ProductLabel(
                text=product,
                font_size=self.font_size,
                padding=(self.padding_sides, 0, 0, 0)
            )
            #label.bind(size=label.setter('text_size'))
            self.add_widget(label)

            amount = AmountLabel(text='0', font_size=self.font_size, size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0))
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
            orders = billy.order_data(datetime.now()-timedelta(hours=8))
            ordered_products = billy.count_products(orders, config.base_products)
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


class StatusBar(BoxLayout):
    clock = StringProperty('xx:xx:xx')
    
    def set_time(self, dt=None):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        self.clock = current_time

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
        Clock.schedule_interval(status.set_time, 0.1)

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
