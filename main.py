#!/usr/bin/python
import os
import re
import socket
import time
import threading
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional, Tuple
from datetime import datetime, timedelta

import config


def start_of_shift() -> datetime:
    now = datetime.now()
    for shift_start in config.shift_starts[::-1]:
        if now > shift_start:
            return shift_start
    return config.shift_starts[0]


NETWORK_WAIT = 60  # seconds the first download keeps retrying while the network comes up


def download_first_orders():
    """First download, retrying until the network is up: at boot the dashboard starts well before it is."""
    # pandas (through billy) takes seconds to import on the Pi; importing it here overlaps that with Kivy's start
    import billy
    import requests
    give_up = time.monotonic() + NETWORK_WAIT
    while True:
        try:
            return billy.order_data(start_of_shift())
        except requests.ConnectionError:
            if time.monotonic() > give_up:
                raise
            time.sleep(1)


# The first download (login, report, Excel parse) takes seconds on the Pi, and so does starting Kivy.
# Start it before anything from Kivy is imported so both run at the same time and the first amounts
# show sooner after boot.
first_download: Optional[Future] = None
if __name__ == '__main__':
    first_download = ThreadPoolExecutor(max_workers=1).submit(download_first_orders)

from kivy.graphics import Color, Line, Rectangle
from kivy.lang import Builder
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput

import kivy
kivy.require('2.3.0')
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.actionbar import ActionBar
from kivy.clock import Clock, mainthread

from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel

import billy  # after Kivy: while the first download is still importing it, this waits for that

# 1 on the real 1080x1920 portrait screen (set by the Pi's service, see deploy/), 0.3 for a desktop preview
SCALE = float(os.environ.get('DASHBOARD_SCALE', 0.3))
Window.size = (1080*SCALE, 1920*SCALE)

order_id = None
since_time = None  # filter on a time instead of an order number (entered as e.g. 1830)
wait_time = None


class ProductLabel(Label):
    """Left-aligned name. With max_font_size set, a name too wide for its column gets a smaller font
    so it stays on one line; names that fit keep max_font_size."""
    max_font_size = NumericProperty(0)  # 0: keep font_size as given (headers)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(width=self.fit_font, text=self.fit_font, max_font_size=self.fit_font)
        self.fit_font()

    def fit_font(self, *args):
        if not self.max_font_size:
            return
        available = self.width - self.padding[0] - self.padding[2]
        needed = text_width(self.text, self.max_font_size)
        # a little margin, so rounding never wraps the last letter onto a second line
        scale = min(1, 0.97 * available / needed) if needed and available > 0 else 1
        self.font_size = self.max_font_size * scale


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
    shift_scale = 0.85  # shift totals are secondary, so a bit smaller than the "Na order" amounts
    cols = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.thread = None
        self.orders = None

        # Size the amount columns from the rendered width of 4 digits at the largest font used
        max_font = self.font_size * max([1] + [c.get('font_scale', 1) for c in config.products.values()])
        self.amount_width = digits_width(max_font) + self.padding_sides
        self.shift_width = digits_width(max_font * self.shift_scale) + self.padding_sides

        # Header row: amounts since the entered order number, and for the whole shift
        header = dict(font_size=self.header_font_size, color=self.header_color, size_hint_y=None, height=self.header_height)
        self.add_widget(ProductLabel(text='Product', padding=(self.padding_sides, 0, 0, 0), **header))
        # Shows the entered order ("Na #1234"); long numbers are cut from the left so the last digits stay visible
        self.order_header = AmountLabel(text='Na order', shorten=True, shorten_from='left', size_hint_x=None, width=self.amount_width, padding=(0, 0, self.padding_sides, 0), **header)
        self.add_widget(self.order_header)
        self.add_widget(ShiftLabel(text='Shift', size_hint_x=None, width=self.shift_width, padding=(0, 0, self.padding_sides, 0), **header))

        self.labels_current_amount = {}
        self.labels_total_amount = {}
        for product, product_config in config.products.items():
            font_size = self.font_size * product_config.get('font_scale', 1)
            self.add_row(product, product_config.get('display', product), font_size)
        self.add_row('Totaal', 'Totaal', self.font_size, size_hint_y=None, height=self.totals_height)

    def add_row(self, key, name, font_size, **row):
        # long names shrink to fit the column (see ProductLabel)
        self.add_widget(ProductLabel(text=name, max_font_size=font_size, padding=(self.padding_sides, 0, 0, 0), **row))
        columns = ((self.labels_current_amount, AmountLabel, font_size, self.amount_width),
                   (self.labels_total_amount, ShiftLabel, font_size * self.shift_scale, self.shift_width))
        for labels, label_cls, amount_font, width in columns:
            amount = label_cls(font_size=amount_font, size_hint_x=None, width=width, padding=(0, 0, self.padding_sides, 0), **row)
            labels[key] = amount
            self.add_widget(amount)

    def update_thread(self):
        global first_download
        if first_download is not None:
            # Use the download started at launch; if it failed, this raises and the next update retries
            download, first_download = first_download, None
            self.orders = download.result()
        else:
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


STALE_AFTER = timedelta(seconds=30)  # data older than this is flagged; updates run every 7s
WAIT_ORANGE = 30  # minutes of wait time shown in orange
WAIT_RED = 60  # minutes of wait time shown in red


WIRELESS_PATH = '/proc/net/wireless'  # Linux only (e.g. the Raspberry Pi)
ROUTE_PATH = '/proc/net/route'
SYS_NET_PATH = '/sys/class/net'


def default_interface(path: str = ROUTE_PATH) -> Optional[str]:
    """Name of the Linux network interface carrying the default route (e.g. 'wlan0', 'eth0'), or None.

    None on Windows (the file doesn't exist) or when there is no default route.
    """
    try:
        with open(path) as f:
            lines = f.readlines()[1:]  # skip the header line
    except OSError:
        return None
    # Iface  Destination  Gateway  Flags  RefCnt  Use  Metric ...; default routes have destination 0.0.0.0.
    # With several (cable and WiFi both up) the kernel uses the one with the lowest metric.
    defaults = [line.split() for line in lines]
    defaults = [fields for fields in defaults if len(fields) >= 7 and fields[1] == '00000000']
    if not defaults:
        return None
    return min(defaults, key=lambda fields: int(fields[6]))[0]


def is_wireless(interface: str, sys_path: str = SYS_NET_PATH) -> bool:
    """Linux exposes a 'wireless' directory only for WiFi interfaces"""
    return os.path.isdir(os.path.join(sys_path, interface, 'wireless'))


def wifi_signal(interface: str, path: str = WIRELESS_PATH) -> Optional[float]:
    """WiFi signal level in dBm of the given Linux interface, or None when unavailable.

    Reads /proc/net/wireless (no extra packages or root needed, works on a Raspberry Pi).
    """
    try:
        with open(path) as f:
            lines = f.readlines()[2:]  # skip the two header lines
    except OSError:
        return None
    for line in lines:
        # e.g. " wlan0: 0000   54.  -56.  -256        0      0      0      0     29        0"
        fields = line.split()
        if len(fields) >= 4 and fields[0].rstrip(':') == interface:
            try:
                level = float(fields[3].rstrip('.'))
            except ValueError:
                return None
            # a disconnected interface reports 0 (or a placeholder) instead of a dBm value
            return level if level < 0 else None
    return None


def wifi_bars(signal: Optional[float]) -> int:
    """Signal level in dBm to 1-4 bars (0 when unknown): above -67 dBm is solid, below -75 dBm expect dropped connections"""
    if signal is None:
        return 0
    if signal >= -55:
        return 4
    if signal >= -67:
        return 3
    if signal >= -75:
        return 2
    return 1


def connection_state(ip: Optional[str]) -> Tuple[str, int]:
    """(kind, wifi bars) of the current connection; kind is 'wifi', 'cable', 'offline' or 'unknown'.

    On Linux the default-route interface tells WiFi from cable. Elsewhere (Windows) only
    'offline' vs 'unknown' (connected, type unknown) can be told apart without extra permissions.
    """
    if ip is None:
        return 'offline', 0
    interface = default_interface()
    if interface is None:
        return 'unknown', 0
    if is_wireless(interface):
        return 'wifi', wifi_bars(wifi_signal(interface))
    return 'cable', 0


class NetworkIcon(Widget):
    """Drawn connection icon: WiFi bars, a network plug for cable, or a red cross when offline.
    Drawn on the canvas, so no icon font is needed."""
    kind = StringProperty('unknown')  # see connection_state()
    bars = NumericProperty(0)
    grey = (0.7, 0.7, 0.7, 1)
    dim = (0.3, 0.3, 0.3, 1)
    red = (1, 0.33, 0.33, 1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw, kind=self.redraw, bars=self.redraw)

    def bar_color(self):
        if self.bars == 1:
            return self.red
        if self.bars == 2:
            return 1, 0.67, 0.2, 1  # orange
        return self.grey

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            if self.kind in ('wifi', 'offline'):
                self.draw_bars()
            elif self.kind == 'cable':
                self.draw_plug()
            if self.kind == 'offline':
                Color(*self.red)
                Line(points=[self.x, self.top, self.right, self.y], width=1.5)
                Line(points=[self.x, self.y, self.right, self.top], width=1.5)

    def draw_bars(self):
        count = 4
        gap = self.width * 0.1
        bar_width = (self.width - gap * (count - 1)) / count
        for i in range(count):
            filled = self.kind == 'wifi' and i < self.bars
            Color(*(self.bar_color() if filled else self.dim))
            Rectangle(pos=(self.x + i * (bar_width + gap), self.y), size=(bar_width, self.height * (i + 1) / count))

    def draw_plug(self):
        # Front view of a network plug: body, the latch tab below it and the contacts on top
        Color(*self.grey)
        body_width = self.width * 0.7
        body_x = self.center_x - body_width / 2
        body_y = self.y + self.height * 0.25
        body_height = self.height * 0.75
        Line(rectangle=(body_x, body_y, body_width, body_height), width=1.2)
        tab_width = body_width * 0.4
        Rectangle(pos=(self.center_x - tab_width / 2, self.y), size=(tab_width, self.height * 0.25))
        for i in range(4):
            x = body_x + body_width * (i + 1) / 5
            Line(points=[x, self.top - body_height * 0.15, x, self.top - body_height * 0.45], width=1)


def device_ip() -> Optional[str]:
    """IP address of the interface with the default route, or None when there is no network.

    Connecting a UDP socket only selects a route and sends nothing. Works on Windows and Linux,
    unlike gethostbyname(gethostname()), which often returns 127.0.1.1 on Linux.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        return None


def text_width(text: str, font_size: float) -> float:
    """Pixel width needed to render text on one line at font_size (sp already applied)."""
    label = CoreLabel(text=text, font_size=font_size)
    label.refresh()
    return label.texture.size[0]


def digits_width(font_size: float, digits: int = 4) -> float:
    """Pixel width needed to render `digits` digits at font_size (sp already applied)."""
    return text_width('0' * digits, font_size)


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
        self.last_download = None  # time of the last successful download from Billy

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

        # Info line for the headless screen: shift in use, data freshness and the device's IP
        info_font = sp(40*SCALE)
        info_row = BoxLayout(size_hint_y=None, height=info_font*1.8, padding=(0, 0, self.dashboard.padding_sides, 0))
        self.info = Label(markup=True, font_size=info_font, color=(0.7, 0.7, 0.7, 1))
        info_row.add_widget(self.info)
        self.network_icon = NetworkIcon(size_hint=(None, None), size=(info_font*1.6, info_font*1.3), pos_hint={'center_y': 0.5})
        info_row.add_widget(self.network_icon)
        layout.add_widget(info_row)
        Clock.schedule_interval(self.update_info, 1)

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
            self.last_download = datetime.now()
        except Exception:
            # Keep showing the last known amounts; the next scheduled update retries
            traceback.print_exc()
        finally:
            self.reset_progress()

    @mainthread
    def reset_progress(self):
        self.progress.value = 0

    def update_info(self, dt=None):
        parts = []
        if self.last_download is None:
            parts.append('[color=ff5555]Nog geen data[/color]')
        elif datetime.now() - self.last_download > STALE_AFTER:
            parts.append(f'[color=ff5555]Offline sinds {self.last_download:%H:%M}[/color]')
        else:
            parts.append(f'Update {self.last_download:%H:%M:%S}')

        ip = device_ip()
        self.network_icon.kind, self.network_icon.bars = connection_state(ip)
        if ip:
            parts.append(ip)
        self.info.text = ' · '.join(parts)

    def on_window_resize(self, window, width, height):
        print(window, width, height)


if __name__ == '__main__':
    DashboardApp().run()
