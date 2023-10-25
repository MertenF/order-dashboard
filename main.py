import time

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar

import config
import billy

import kivy
kivy.require('2.2.1')
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.actionbar import ActionBar
from kivy.clock import Clock


class OrderDashboard(GridLayout):
    font_size = 60
    cols = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.labels_amount = {}
        for product in config.base_products:
            self.add_widget(Label(text=product, font_size=self.font_size))
            amount = Label(text='0', font_size=self.font_size)
            self.labels_amount[product] = amount
            self.add_widget(amount)

        self.add_widget(Label(text='Totaal', font_size=self.font_size+10))
        total = Label(text='0', font_size=self.font_size+10)
        self.labels_amount['Totaal'] = total
        self.add_widget(total)

        self.update_amounts()  # initialise values

    def update(self, dt):
        print(f'Update! {dt}')
        self.update_amounts()

    def update_amounts(self):
        ordered_products = billy.get_product_count()
        time.sleep(1)

        for product, amount in ordered_products.items():
            self.labels_amount[product].text = str(amount)
        self.labels_amount['Totaal'].text = str(sum(ordered_products.values()))


class StatusBar(BoxLayout):
    def __int__(self):
        super().__init__()
        self.orientation = 'horizonal'


class RefreshBar(ProgressBar):

    def __int__(self):
        self.max = 10
        super().__init__()
        
    def update(self, dt):
        self.value += dt
        print(f'{self.value} {self.max}')

class DashboardApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        
        status = StatusBar()
        layout.add_widget(status)
        
        dashboard = OrderDashboard()
        layout.add_widget(dashboard)
        Clock.schedule_interval(dashboard.update, 5)
        
        self.progress = ProgressBar(max=10)
        layout.add_widget(self.progress)
        Clock.schedule_interval(self.update_progress, 0.1)
                
        return layout
    
    
    def update_progress(self, dt):
        self.progress.value += dt


if __name__ == '__main__':
    DashboardApp().run()
