#!/usr/bin/python
import re
import time
import threading
import traceback
from typing import Optional
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
from kivy.core.text import Label as CoreLabel

SCALE = 0.3
Window.size = (1080*SCALE, 1920*SCALE)

order_id = None
since_time = None  # filter on a time instead of an order number (entered as e.g. 1830)
wait_time = None


class ProductLabel(Label):
    pass


class AmountLabel(Label):
    pass


class ShiftLabel(AmountLabel):
    """Amount in the shift-total column, on a tinted background band (see dashboard.kv)"""
    pass


class OrderDashboard(GridLayout):
    font_size = sp(110*SCALE)
    padding_sides = int(40 * SCALE)
    totals_height = 400*SCALE
    header_font_size = font_size * 0.55  # largest that keeps "Na order" on one line in a 4-digit column
    header_height = header_font_size * 2
    header_color = (0.7, 0.7, 0.7, 1)
    cols = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.thread = None
        self.orders = None

        # Size the amount columns from the rendered width of 4 digits at the largest font used
        max_font = self.font_size * max([1] + [c.get('font_scale', 1) for c in config.products.values()])
        self.amount_width = digits_width(max_font) + self.padding_sides

        # Header row: amounts since the entered order number, and for the whole shift
        header = dict(font_size=self.header_font_size, color=self.header_color, size_hint_y=None, height=self.header_height)
        self.add_widget(ProductLabel(text='Product', padding=(self.padding_sides, 0, 0, 0), **header))
        # Shows the entered order ("Na #1234"); long numbers are cut from the left so the last digits stay visible
        self.order_header = AmountLabel(text='Na order', shorten=True, shorten_from='left', size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0), **header)
        self.add_widget(self.order_header)
        self.add_widget(ShiftLabel(text='Shift', size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0), **header))

        self.labels_current_amount = {}
        self.labels_total_amount = {}
        for product, product_config in config.products.items():
            font_size = self.font_size * product_config.get('font_scale', 1)
            label = ProductLabel(
                text=product_config.get('display', product),
                font_size=font_size,
                padding=(self.padding_sides, 0, 0, 0)
            )
            self.add_widget(label)

            for labels, label_cls in ((self.labels_current_amount, AmountLabel), (self.labels_total_amount, ShiftLabel)):
                amount = label_cls(font_size=font_size, size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0))
                labels[product] = amount
                self.add_widget(amount)

        self.add_widget(ProductLabel(text='Totaal', font_size=self.font_size, padding=(self.padding_sides, 0, 0, 0), size_hint_y=None, height=self.totals_height))
        for labels, label_cls in ((self.labels_current_amount, AmountLabel), (self.labels_total_amount, ShiftLabel)):
            total = label_cls(text='0000', font_size=self.font_size, size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0), size_hint_y=None, height=self.totals_height)
            labels['Totaal'] = total
            self.add_widget(total)

    def update_thread(self):
        self.orders = billy.order_data(start_of_shift())
        self.update_orders_display()

    def update_orders_display(self):
        """Recalculate the orders"""
        global wait_time
        if self.orders is None:  # first download hasn't finished yet; it will apply order_id when it does
            return
        ordered_products, wait_time = billy.count_products(self.orders, config.products.keys(), order_id, since_time)
        shift_products, _ = billy.count_products(self.orders, config.products.keys())  # never filtered

        self.update_amounts(ordered_products, shift_products)

    @mainthread
    def update_amounts(self, ordered_products, shift_products):

        print(ordered_products)

        for labels, counts in ((self.labels_current_amount, ordered_products), (self.labels_total_amount, shift_products)):
            for product, amount in counts.items():
                labels[product].text = str(amount)
            labels['Totaal'].text = str(sum(counts.values()))


WAIT_ORANGE = 30  # minutes of wait time shown in orange
WAIT_RED = 60  # minutes of wait time shown in red


def digits_width(font_size: float, digits: int = 4) -> float:
    """Pixel width needed to render `digits` digits at font_size (sp already applied)."""
    label = CoreLabel(text='0' * digits, font_size=font_size)
    label.refresh()
    return label.texture.size[0]


# Billy order IDs are 8 digits, so up to 4 digits (or with a colon) is a time: 1830, 18:30, 930
TIME_INPUT = re.compile(r'^(\d{1,2}):?(\d{2})$')


def parse_time(text: str, now: datetime) -> Optional[datetime]:
    """Entered time as the most recent moment it occurred, or None when the text isn't a time.

    A time later than now means yesterday, so 2330 entered at 00:15 is last evening.
    Raises ValueError for time-shaped input that isn't a valid time, like 2575.
    """
    match = TIME_INPUT.match(text)
    if not match:
        return None
    time = now.replace(hour=int(match[1]), minute=int(match[2]), second=0, microsecond=0)
    if time > now:
        time -= timedelta(days=1)
    return time


def start_of_shift() -> datetime:
    now = datetime.now()
    for shift_start in config.shift_starts[::-1]:
        if now > shift_start:
            return shift_start
    return config.shift_starts[0]


class StatusBar(BoxLayout):
    clock = StringProperty('xx:xx:xx')
    error_shown = timedelta(seconds=30)

    def __init__(self):
        super().__init__()
        self.error = None  # message about the last rejected input, shown for error_shown
        self.error_at = None
        self.ids.order_input.bind(on_text_validate=self.on_enter)


    def set_time(self, dt=None):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        self.clock = current_time

    def on_enter(self, value: TextInput):
        """Filter on an order number or a time (see TIME_INPUT); empty input clears the filter.
        Invalid input shows an error and keeps the current filter."""
        global order_id, since_time
        text = value.text.strip()
        value.text = ''
        print(f'Order input: {text!r}')

        app = App.get_running_app()
        try:
            entered_time = parse_time(text, datetime.now())
        except ValueError:
            self.show_error(f'{text}\nongeldige tijd')
            return

        if entered_time is not None:
            order_id, since_time = None, entered_time
        elif not text:
            order_id, since_time = None, None
        else:
            try:
                num = int(text)
            except ValueError:
                self.show_error(f'{text}\nongeldig')
                return
            orders = app.dashboard.orders
            # Reject numbers that aren't in this shift's orders.
            # Before the first download there is nothing to check against, so accept it.
            if orders is not None and num not in orders['Order ID'].values:
                print(f'Order {num} not found in this shift')
                self.show_error(f'#{num}\nniet gevonden')
                return
            order_id, since_time = num, None

        self.error = None
        app.dashboard.update_orders_display()
        self.set_statistics()

    def show_error(self, message: str):
        self.error = message
        self.error_at = datetime.now()
        self.set_statistics()

    def set_statistics(self, dt=None):
        label = self.ids.stat_label
        if self.error and datetime.now() - self.error_at < self.error_shown:
            small = int(label.font_size * 0.45)
            label.text = f'[size={small}][color=ff5555]{self.error}[/color][/size]'
        elif (order_id is not None or since_time is not None) and wait_time is not None:
            colour = 'ff5555' if wait_time >= WAIT_RED else 'ffaa33' if wait_time >= WAIT_ORANGE else None
            text = f'{wait_time} min'
            label.text = f'[color={colour}]{text}[/color]' if colour else text
        else:
            label.text = ''

        header = App.get_running_app().dashboard.order_header
        if since_time is not None:
            header.text = f'Na {since_time:%H:%M}'
        elif order_id is not None:
            header.text = f'Na #{order_id}'
        else:
            header.text = 'Na order'


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
        Clock.schedule_once(status.set_statistics)  # fill the status box right away instead of after 10s
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
