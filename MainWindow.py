import os

from mainForm_ui import Ui_MainWindow as MainWindowUI
from Game import CellContents, Game, GameState

from time import time, sleep

from PyQt5 import QtSvg, QtWidgets
from PyQt5.QtGui import QMouseEvent, QPainter, QStandardItemModel
from PyQt5.QtWidgets import QMainWindow, QItemDelegate, QStyleOptionViewItem, QInputDialog, QMessageBox
from PyQt5.QtCore import QModelIndex, QRectF, QTimer, Qt


class FieldSizeDialog(QtWidgets.QDialog):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
        self.main = root
        self.setWindowTitle("Размер поля и ячеек")

        size_label = QtWidgets.QLabel('Размер ячейки:')
        width_label = QtWidgets.QLabel('Ширина игрового поля:')
        height_label = QtWidgets.QLabel('Высота игрового поля:')
        chain_len_label = QtWidgets.QLabel('Минимальная длина цепочки:')
        
        self.size_spinbox = QtWidgets.QSpinBox()
        self.size_spinbox.setRange(10, 100)
        self.size_spinbox.setValue(self.main.cell_size)

        self.width_spinbox = QtWidgets.QSpinBox()
        self.width_spinbox.setRange(3, 100)
        self.width_spinbox.setValue(self.main.game.col_count)

        self.height_spinbox = QtWidgets.QSpinBox()
        self.height_spinbox.setRange(3, 100)
        self.height_spinbox.setValue(self.main.game.row_count)

        self.chain_len_spinbox = QtWidgets.QSpinBox()
        self.chain_len_spinbox.setRange(1, 10)
        self.chain_len_spinbox.setValue(self.main.game.min_chain_len)

        save_button = QtWidgets.QPushButton('Сохранить изменения')
        save_button.clicked.connect(self.save)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(size_label, 0, 0)
        layout.addWidget(self.size_spinbox, 0, 1)
        layout.addWidget(width_label, 1, 0)
        layout.addWidget(self.width_spinbox, 1, 1)
        layout.addWidget(height_label, 2, 0)
        layout.addWidget(self.height_spinbox, 2, 1)
        layout.addWidget(chain_len_label, 3, 0)
        layout.addWidget(self.chain_len_spinbox, 3, 1)
        layout.addWidget(save_button, 4, 0, 1, 2)
        self.setLayout(layout)

    def save(self):
        self.main.cell_size = self.size_spinbox.value()
        self.main.game.min_chain_len = self.chain_len_spinbox.value()
        self.main.game.row_count = self.height_spinbox.value()
        self.main.game.col_count = self.width_spinbox.value()
        self.close()


class MainWindow(QMainWindow, MainWindowUI):
    GAME_RULE_FILE = "game_rule.txt"
    SLEEP_TIME = 0.300

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)

        self._cell_size = 50
        self._sleep_time = self.SLEEP_TIME

        self._time = 0
        self._timer = QTimer(parent)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_time_tick)

        images_dir = os.path.join(os.path.dirname(__file__), 'images')
        self._images = {
            os.path.splitext(f)[0]: QtSvg.QSvgRenderer(os.path.join(images_dir, f))
            for f in os.listdir(images_dir)
        }

        self._game = Game()
        self._game_resize(self._game)

        class MyDelegate(QItemDelegate):
            def __init__(self, parent=None, *args):
                QItemDelegate.__init__(self, parent, *args)

            def paint(self, painter: QPainter, option: QStyleOptionViewItem, idx: QModelIndex):
                painter.save()
                self.parent().on_item_paint(idx, painter, option)
                painter.restore()

        self.tableView.setItemDelegate(MyDelegate(self))
        self.tableView.setShowGrid(False)

        def new_mouse_press_event(e: QMouseEvent) -> None:
            idx = self.tableView.indexAt(e.pos())
            print('press row = {}, column = {}'.format(idx.row(), idx.column()))
            self._game.on_mouse_press((idx.row(), idx.column()))
            self._update_view()

        def new_mouse_release_event(e: QMouseEvent) -> None:
            idx = self.tableView.indexAt(e.pos())
            print('release row = {}, column = {}'.format(idx.row(), idx.column()))

            for _ in self._game.step_down_generator():
                self._update_view()
                sleep(self.sleep_time)
            self._game.update_past_mouse_release()
            self._update_view()

        def new_mouse_move_event(e: QMouseEvent) -> None:
            idx = self.tableView.indexAt(e.pos())
            print('move row = {}, column = {}'.format(idx.row(), idx.column()))
            if self._game.on_mouse_move((idx.row(), idx.column())):
                self._update_view()

        self.tableView.mousePressEvent = new_mouse_press_event
        self.tableView.mouseMoveEvent = new_mouse_move_event
        self.tableView.mouseReleaseEvent = new_mouse_release_event

        # обработка нажатий на кнопки и меню бар

        self.start_game_button.clicked.connect(self._on_new_game)

        self.exit.triggered.connect(self.on_quit)
        self.sleep_menu_item.triggered.connect(self.on_sleep_menu_item)
        self.game_field_size.triggered.connect(self.on_game_field_size)
        self.game_rule.triggered.connect(self.on_game_rule)

        self._new_game()

    def get_cell_size(self) -> int:
        return self._cell_size

    def set_cell_size(self, size):
        self._cell_size = size

    cell_size = property(get_cell_size, set_cell_size)

    @property
    def game(self):
        return self._game

    def get_sleep_time(self):
        return self._sleep_time

    def set_sleep_time(self, time):
        self._sleep_time = time

    sleep_time = property(get_sleep_time, set_sleep_time)

    def _resize_table(self):
        self.tableView.horizontalHeader().setDefaultSectionSize(self.cell_size)
        self.tableView.verticalHeader().setDefaultSectionSize(self.cell_size)

    def _game_resize(self, game: Game) -> None:
        model = QStandardItemModel(game.row_count, game.col_count)
        self.tableView.setModel(model)
        self._update_view()

    def _update_view(self):
        self.tableView.viewport().update()
        self.tableView.update()
        self.lcdNumber.display(self._time)
        if self._game.state != GameState.PLAYING:
            self._timer.stop()
            self._end_game()
        self.repaint()

    def _end_game(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Вы победили за {}c, начать заново?".format(self._time))
        msg_box.setWindowTitle("Конец игры")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg_box.exec() == QMessageBox.Yes:
            self._new_game()
        else:
            self.close()

    def _new_game(self):
        self._game.new_game()
        self._game_resize(self._game)
        self._time = 0
        self._update_view()
        self._timer.start()

    def _on_new_game(self):
        self._new_game()

    def _on_time_tick(self):
        self._time += 1
        self.lcdNumber.display(min(self._time, 999))

    def on_item_paint(self, e: QModelIndex, painter: QPainter, option: QStyleOptionViewItem) -> None:
        item = self._game[e.row(), e.column()]
        if item.contents == CellContents.PRINCESS:
            img = self._images['princess']
        elif item.contents == CellContents.KNIGHT:
            img = self._images['knight']
        elif item.contents == CellContents.CIRCLE:
            name = 'circle' if not item.is_active else 'active_circle'
            img = self._images[name]
        elif item.contents == CellContents.SQUARE:
            name = 'square' if not item.is_active else 'active_square'
            img = self._images[name]
        elif item.contents == CellContents.TRIANGLE:
            name = 'triangle' if not item.is_active else 'active_triangle'
            img = self._images[name]
        else:
            img = self._images['closed']
        img.render(painter, QRectF(option.rect))

    def on_quit(self) -> None:
        self.close()

    def on_game_field_size(self) -> None:
        dialog = FieldSizeDialog(self)
        dialog.exec()
        self._resize_table()
        self._new_game()

    def on_sleep_menu_item(self) -> None:
        d, okPressed = QInputDialog.getDouble(self, "Настройки",
                                              "Время задержки анимации:", self.sleep_time, 0.001, 5.0, 3)
        if okPressed:
            self.sleep_time = d

    @staticmethod
    def on_game_rule() -> None:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Правила игры")
        msg_box.setStandardButtons(QMessageBox.Ok)

        def get_text(file_name):
            with open(file_name, encoding="UTF-8") as file:
                return file.read()

        msg_box.setText(get_text(MainWindow.GAME_RULE_FILE))
        msg_box.exec()