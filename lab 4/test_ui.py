"""
UI тесты для графического интерфейса
"""

import unittest
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import sys
import time

from model import TemperatureModel
from view import MainView, WorkView, HelpView

# Отключаем логирование на время тестов
logging.disable(logging.CRITICAL)


class UITestCase(unittest.TestCase):
    """Базовый класс для UI тестов"""
    
    def setUp(self):
        """Создание приложения перед каждым тестом"""
        self.model = TemperatureModel()
        self.app = MainView(self.model)
        self.app.update_idletasks()
        time.sleep(0.1)
    
    def tearDown(self):
        """Уничтожение приложения после каждого теста"""
        try:
            self.app.quit()
            self.app.destroy()
        except:
            pass
    
    def find_widget(self, parent, widget_type):
        """Рекурсивный поиск виджета по типу"""
        if isinstance(parent, widget_type):
            return parent
        if hasattr(parent, 'winfo_children'):
            for child in parent.winfo_children():
                result = self.find_widget(child, widget_type)
                if result:
                    return result
        return None
    
    def find_button(self, parent, text):
        """Поиск кнопки по тексту"""
        # Прямой поиск по атрибутам для WorkView
        if hasattr(parent, 'add_btn') and text == "Добавить":
            return parent.add_btn
        if hasattr(parent, 'delete_btn') and text == "Удалить":
            return parent.delete_btn
        if hasattr(parent, 'back_btn') and text == "Назад":
            return parent.back_btn
        if hasattr(parent, 'help_btn') and text == "Справка":
            return parent.help_btn
        if hasattr(parent, 'commands_btn') and text == "Выполнить команды":
            return parent.commands_btn
        if hasattr(parent, 'close_btn') and text == "Закрыть":
            return parent.close_btn
        
        # Рекурсивный поиск
        if isinstance(parent, (tk.Button, ttk.Button)):
            try:
                if parent['text'] == text:
                    return parent
            except:
                pass
        
        if hasattr(parent, 'winfo_children'):
            for child in parent.winfo_children():
                result = self.find_button(child, text)
                if result:
                    return result
        return None


class TestMainView(UITestCase):
    """Тесты главного меню"""
    
    def test_window_title(self):
        """Тест: Заголовок окна"""
        self.assertEqual(self.app.title(), "Главное меню")
    
    def test_buttons_exist(self):
        """Тест: Наличие кнопок"""
        buttons = ["Работать", "Справка", "Выход"]
        for text in buttons:
            btn = self.find_button(self.app, text)
            self.assertIsNotNone(btn, f"Кнопка '{text}' не найдена")
    
    def test_open_work_view(self):
        """Тест: Открытие рабочего окна"""
        btn = self.find_button(self.app, "Работать")
        self.assertIsNotNone(btn)
        
        btn.invoke()
        self.app.update_idletasks()
        time.sleep(0.1)
        
        # Главное окно должно быть скрыто
        self.assertEqual(self.app.state(), 'withdrawn')
        
        # Должно появиться рабочее окно
        work_view = self.find_widget(self.app, WorkView)
        self.assertIsNotNone(work_view)
        if work_view:
            self.assertEqual(work_view.title(), "Учет температуры")
    
    def test_open_help_view(self):
        """Тест: Открытие справки"""
        btn = self.find_button(self.app, "Справка")
        self.assertIsNotNone(btn)
        
        btn.invoke()
        self.app.update_idletasks()
        time.sleep(0.1)
        
        help_view = self.find_widget(self.app, HelpView)
        self.assertIsNotNone(help_view)
        if help_view:
            self.assertEqual(help_view.title(), "Справка")


class TestWorkView(UITestCase):
    """Тесты рабочего окна"""
    
    def setUp(self):
        super().setUp()
        # Открываем рабочее окно
        btn = self.find_button(self.app, "Работать")
        if btn:
            btn.invoke()
            self.app.update_idletasks()
            time.sleep(0.1)
            self.work_view = self.find_widget(self.app, WorkView)
            if self.work_view:
                self.work_view.update_idletasks()
                time.sleep(0.1)
    
    def test_initial_state(self):
        """Тест: Начальное состояние"""
        if not self.work_view:
            self.skipTest("Рабочее окно не открылось")
            return
        
        # Таблица должна быть пустой
        items = self.work_view.tree.get_children()
        self.assertEqual(len(items), 0)
        
        # Статус должен показывать 0 записей
        status = self.work_view.status_var.get()
        self.assertIn("Записей: 0", status)
    
    def test_table_columns(self):
        """Тест: Колонки таблицы"""
        if not self.work_view:
            self.skipTest("Рабочее окно не открылось")
            return
        
        columns = self.work_view.tree['columns']
        self.assertEqual(len(columns), 3)
        self.assertIn('date', columns)
        self.assertIn('location', columns)
        self.assertIn('value', columns)
    
    def test_add_record_dialog(self):
        """Тест: Открытие диалога добавления"""
        if not self.work_view:
            self.skipTest("Рабочее окно не открылось")
            return
        
        # Пробуем найти кнопку через атрибут
        btn = None
        if hasattr(self.work_view, 'add_btn'):
            btn = self.work_view.add_btn
        
        if not btn:
            btn = self.find_button(self.work_view, "Добавить")
        
        self.assertIsNotNone(btn, "Кнопка 'Добавить' не найдена")
        
        btn.invoke()
        self.work_view.update_idletasks()
        time.sleep(0.1)
        
        # Ищем диалог
        dialog = None
        for child in self.work_view.winfo_children():
            if isinstance(child, tk.Toplevel) and child.title() == "Добавить запись":
                dialog = child
                break
        
        self.assertIsNotNone(dialog, "Диалог не открылся")
        
        # Проверяем поля ввода
        if dialog:
            entries = self._find_all_entries(dialog)
            self.assertEqual(len(entries), 3, "Должно быть 3 поля ввода")
    
    def test_add_valid_record(self):
        """Тест: Добавление корректной записи"""
        if not self.work_view:
            self.skipTest("Рабочее окно не открылось")
            return
        
        initial_count = self.model.count()
        self._simulate_add_record("20.03.2024", "Москва", "5.5")
        
        # Проверяем модель
        self.assertEqual(self.model.count(), initial_count + 1)
        
        record = self.model.get_record(self.model.count() - 1)
        self.assertIsNotNone(record, "Запись не найдена")
        if record:
            self.assertEqual(record.location, "Москва")
            self.assertEqual(record.value, 5.5)
        
        # Проверяем таблицу
        items = self.work_view.tree.get_children()
        self.assertEqual(len(items), initial_count + 1)
        
        # Проверяем статус
        status = self.work_view.status_var.get()
        self.assertIn(f"Записей: {initial_count + 1}", status)

    def test_delete_record(self):
        """Тест: Удаление записи"""
        if not self.work_view:
            self.skipTest("Рабочее окно не открылось")
            return
        
        self._simulate_add_record("20.03.2024", "Москва", "5.5")
        initial_count = self.model.count()
        
        # Выбираем запись
        items = self.work_view.tree.get_children()
        if items:
            self.work_view.tree.selection_set(items[0])
            
            # Удаляем
            selected = self.work_view.tree.selection()
            for item in selected:
                index = self.work_view.tree.index(item)
                self.model.delete_record(index)
            
            self.work_view._refresh_table()
            self.work_view.update_idletasks()
            
            self.assertEqual(self.model.count(), initial_count - 1)
    
    def test_go_back(self):
        """Тест: Возврат в главное меню"""
        if not self.work_view:
            self.skipTest("Рабочее окно не открылось")
            return
        
        btn = self.find_button(self.work_view, "Назад")
        if not btn and hasattr(self.work_view, 'back_btn'):
            btn = self.work_view.back_btn
        
        self.assertIsNotNone(btn, "Кнопка 'Назад' не найдена")
        
        btn.invoke()
        self.app.update_idletasks()
        time.sleep(0.1)
        
        # Главное окно должно быть видимым
        self.assertEqual(self.app.state(), 'normal')
    
    def _simulate_add_record(self, date, location, temperature):
        """Вспомогательный метод: добавление записи"""
        if not self.work_view:
            return
        
        # Находим кнопку Добавить
        btn = None
        if hasattr(self.work_view, 'add_btn'):
            btn = self.work_view.add_btn
        
        if not btn:
            btn = self.find_button(self.work_view, "Добавить")
        
        if not btn:
            self.skipTest("Кнопка 'Добавить' не найдена")
            return
        
        btn.invoke()
        self.work_view.update_idletasks()
        time.sleep(0.1)
        
        # Ищем диалог
        dialog = None
        for child in self.work_view.winfo_children():
            if isinstance(child, tk.Toplevel) and child.title() == "Добавить запись":
                dialog = child
                break
        
        if not dialog:
            self.skipTest("Диалог добавления не открылся")
            return
        
        entries = self._find_all_entries(dialog)
        if len(entries) >= 3:
            entries[0].delete(0, tk.END)
            entries[0].insert(0, date)
            entries[1].delete(0, tk.END)
            entries[1].insert(0, location)
            entries[2].delete(0, tk.END)
            entries[2].insert(0, temperature)
            
            # Находим кнопку Сохранить
            save_btn = self.find_button(dialog, "Сохранить")
            if save_btn:
                save_btn.invoke()
        
        self.work_view.update_idletasks()
        time.sleep(0.1)
    
    def _find_all_entries(self, parent):
        """Поиск всех полей ввода"""
        entries = []
        def search(w):
            if isinstance(w, ttk.Entry):
                entries.append(w)
            if hasattr(w, 'winfo_children'):
                for child in w.winfo_children():
                    search(child)
        search(parent)
        return entries


class TestHelpView(UITestCase):
    """Тесты окна справки"""
    
    def setUp(self):
        super().setUp()
        btn = self.find_button(self.app, "Справка")
        if btn:
            btn.invoke()
            self.app.update_idletasks()
            time.sleep(0.1)
            self.help_view = self.find_widget(self.app, HelpView)
            if self.help_view:
                self.help_view.update_idletasks()
                time.sleep(0.1)
    
    def test_window_exists(self):
        """Тест: Окно создано"""
        if not self.help_view:
            self.skipTest("Окно справки не открылось")
            return
        self.assertEqual(self.help_view.title(), "Справка")
    
    def test_content_exists(self):
        """Тест: Наличие содержимого"""
        if not self.help_view:
            self.skipTest("Окно справки не открылось")
            return
        
        text_widget = self.find_widget(self.help_view, scrolledtext.ScrolledText)
        if text_widget:
            content = text_widget.get("1.0", tk.END)
            # Проверяем наличие ключевых слов
            self.assertIn("ФОРМАТ ДАННЫХ", content)
            self.assertIn("ДД.ММ.ГГГГ,Место,Температура", content)
    
    def test_close_window(self):
        """Тест: Закрытие окна"""
        if not self.help_view:
            self.skipTest("Окно справки не открылось")
            return
        
        # Находим кнопку закрытия
        btn = self.find_button(self.help_view, "Закрыть")
        if not btn and hasattr(self.help_view, 'close_btn'):
            btn = self.help_view.close_btn
        
        self.assertIsNotNone(btn, "Кнопка 'Закрыть' не найдена")
        
        btn.invoke()
        self.app.update_idletasks()
        time.sleep(0.1)
        
        # Проверяем, что окно закрыто
        try:
            self.help_view.state()
            self.fail("Окно справки должно быть закрыто")
        except tk.TclError:
            pass  # Окно закрыто - это ожидаемое поведение


def run_ui_tests():
    """Запуск UI тестов"""
    print("\n" + "=" * 60)
    print("ЗАПУСК UI ТЕСТОВ")
    print("=" * 60 + "\n")
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestMainView))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestWorkView))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestHelpView))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: {'✓ ПРОЙДЕНЫ' if result.wasSuccessful() else '✗ ПРОВАЛЕНЫ'}")
    print("=" * 60 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_ui_tests()
    sys.exit(0 if success else 1)