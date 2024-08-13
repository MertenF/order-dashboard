import sys

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from __feature__ import snake_case, true_property


height = 1280
width = 1024
scale = 0.5

def main():
    app = QApplication([])

    window = QWidget()
    window.resize(int(width * scale), int(height * scale))

    helloMsg = QLabel("<h1>Hello, World!</h1>", parent=window)

    window.show()
    app.exec()


if __name__ == '__main__':
    main()
