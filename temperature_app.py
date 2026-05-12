"""
Программа для учета температуры.
Формат данных: ДД.ММ.ГГГГ,Место,Температура
"""

import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import logging
import unittest
import re
import sys
from typing import List, Optional

# Попытка импорта PIL
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ============================================================
# ИСКЛЮЧЕНИЯ И МОДЕЛЬ
# ============================================================

class InvalidDataError(Exception):
    pass

class Temperature:
    def __init__(self, date_str: str, location: str, value: float):
        self.date_str = date_str
        self.location = location
        self.value = value

class TemperatureModel:
    def __init__(self):
        self.records: List[Temperature] = []

    def parse_line(self, line: str) -> Optional[Temperature]:
        try:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 3:
                raise InvalidDataError(f"Неверное количество полей: {len(parts)}")
            
            date_str, location, value_str = parts
            
            if not re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", date_str):
                raise InvalidDataError(f"Неверный формат даты: {date_str}")
            
            day, month, year = map(int, date_str.split('.'))
            datetime.date(year, month, day)
            
            value = float(value_str.replace(',', '.'))
            
            if not location:
                raise InvalidDataError("Местоположение не может быть пустым")
            
            return Temperature(date_str, location, value)
        except InvalidDataError:
            raise
        except Exception as e:
            raise InvalidDataError(f"Ошибка парсинга: {e}")

    def load_from_file(self, filename: str):
        self.records = []
        with open(filename, "r", encoding="utf-8") as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = self.parse_line(line)
                    if record:
                        self.records.append(record)
                except InvalidDataError as error:
                    logging.error("[%s, строка %s] %s", filename, line_num, error)
        logging.info("Загружено %d записей из %s", len(self.records), filename)

    def save_to_file(self, filename: str) -> bool:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for r in self.records:
                    f.write(f"{r.date_str},{r.location},{r.value}\n")
            logging.info("Сохранено %d записей в %s", len(self.records), filename)
            return True
        except Exception as e:
            logging.error("Ошибка сохранения в %s: %s", filename, e)
            return False

    def add_record(self, date_str: str, location: str, value: float):
        self.records.append(Temperature(date_str, location, value))

    def delete_record(self, index: int):
        if 0 <= index < len(self.records):
            del self.records[index]

# ============================================================
# ОКНА ПРИЛОЖЕНИЯ
# ============================================================

class HelpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Справка")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        
        text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=10)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, "Формат данных:\nДД.ММ.ГГГГ,Место,Температура\n\nПример:\n15.03.2024,Москва,-5.5")
        text.config(state=tk.DISABLED)
        
        ttk.Button(self, text="Назад", command=self.destroy).pack(pady=10)

class WorkWindow(tk.Toplevel):
    def __init__(self, parent, model: TemperatureModel):
        super().__init__(parent)
        self.parent = parent
        self.model = model
        self.current_filename: Optional[str] = None
        
        self.title("Учет температуры")
        self.geometry("800x500")
        
        self._init_ui()
        self._refresh_table()
        self.protocol("WM_DELETE_WINDOW", self._go_back)
    
    def _init_ui(self):
        # Панель инструментов
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        for text, cmd in [("Загрузить", self._load_file), ("Сохранить", self._save_file)]:
            ttk.Button(toolbar, text=text, command=cmd).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)
        
        for text, cmd in [("Добавить", self._add_dialog), ("Удалить", self._delete_selected)]:
            ttk.Button(toolbar, text=text, command=cmd).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(toolbar, text="Назад", command=self._go_back).pack(side=tk.RIGHT, padx=20)

        # Таблица
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=("date", "location", "value"), show="headings")
        for col, text, width in [("date", "Дата", 120), ("location", "Место", 350), ("value", "Температура (°C)", 150)]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center" if col != "location" else "w")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_var = tk.StringVar(value="Готов к работе")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X)

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.model.records:
            self.tree.insert("", tk.END, values=(r.date_str, r.location, f"{r.value:.1f}"))
        status = f"Файл: {os.path.basename(self.current_filename)} | " if self.current_filename else ""
        self.status_var.set(f"{status}Записей: {len(self.model.records)}")

    def _load_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                self.model.load_from_file(filename)
                self.current_filename = filename
                self._refresh_table()
                messagebox.showinfo("Успех", f"Загружено {len(self.model.records)} записей")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")

    def _save_file(self):
        if not self.model.records:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return
        
        if not self.current_filename:
            self.current_filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
            if not self.current_filename:
                return
        
        if self.model.save_to_file(self.current_filename):
            messagebox.showinfo("Успех", f"Сохранено в {os.path.basename(self.current_filename)}")
            self._refresh_table()
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить файл")

    def _add_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Добавить запись")
        dialog.geometry("350x180")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        entries = {}
        for i, (label, default) in enumerate([
            ("Дата (ДД.ММ.ГГГГ):", datetime.date.today().strftime("%d.%m.%Y")),
            ("Место:", ""), ("Температура:", "")
        ]):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = ttk.Entry(frame, width=25)
            entry.insert(0, default)
            entry.grid(row=i, column=1, pady=5)
            entries[label] = entry

        def save():
            try:
                line = f"{entries['Дата (ДД.ММ.ГГГГ):'].get()},{entries['Место:'].get()},{entries['Температура:'].get()}"
                record = self.model.parse_line(line)
                if record:
                    self.model.records.append(record)
                    self._refresh_table()
                    dialog.destroy()
            except InvalidDataError as e:
                messagebox.showerror("Ошибка ввода", str(e))

        ttk.Button(frame, text="Сохранить", command=save).grid(row=3, column=0, pady=20)
        ttk.Button(frame, text="Отмена", command=dialog.destroy).grid(row=3, column=1, pady=20)
        dialog.bind('<Return>', lambda e: save())

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить {len(selected)} записей?"):
            for item in reversed(selected):
                self.model.delete_record(self.tree.index(item))
            self._refresh_table()

    def _go_back(self):
        self.parent.deiconify()
        self.destroy()

class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Главное меню")
        self.geometry("300x250")
        self.resizable(False, False)
        self.model = TemperatureModel()
        
        tk.Label(self, text="Учет температуры", font=('Arial', 14, 'bold')).pack(pady=20)
        
        frame = tk.Frame(self)
        frame.pack(expand=True)
        
        for text, cmd, color in [("Работать", self._open_work, '#4CAF50'), 
                                  ("Справка", self._open_help, '#2196F3'), 
                                  ("Выход", self.quit, '#f44336')]:
            tk.Button(frame, text=text, command=cmd, bg=color, fg='white',
                     font=('Arial', 11, 'bold'), width=15).pack(pady=5)
    
    def _open_work(self):
        self.withdraw()
        WorkWindow(self, self.model)
    
    def _open_help(self):
        HelpWindow(self)

# ============================================================
# ТЕСТЫ
# ============================================================

class TestTemperatureModel(unittest.TestCase):
    def setUp(self):
        self.model = TemperatureModel()

    def test_valid_line(self):
        record = self.model.parse_line("15.03.2024,Москва,-5.5")
        self.assertEqual(record.date_str, "15.03.2024")
        self.assertEqual(record.location, "Москва")
        self.assertEqual(record.value, -5.5)

    def test_invalid_date(self):
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("2024.03.15,Москва,-5.5")

    def test_add_delete_record(self):
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.assertEqual(len(self.model.records), 1)
        self.model.delete_record(0)
        self.assertEqual(len(self.model.records), 0)

class UITestCase(unittest.TestCase):
    """Базовый класс для UI тестов"""
    
    def setUp(self):
        self.app = MainMenu()
        self.app.update_idletasks()
    
    def tearDown(self):
        try:
            self.app.quit()
            self.app.destroy()
        except:
            pass
    
    def find_widget(self, parent, widget_type):
        """Рекурсивный поиск виджета по типу"""
        def search(w):
            if isinstance(w, widget_type):
                return w
            if hasattr(w, 'winfo_children'):
                for child in w.winfo_children():
                    result = search(child)
                    if result:
                        return result
            return None
        return search(parent)
    
    def find_button(self, parent, text):
        """Поиск кнопки по тексту"""
        def search(w):
            if isinstance(w, (tk.Button, ttk.Button)):
                try:
                    if w['text'] == text:
                        return w
                except:
                    pass
            if hasattr(w, 'winfo_children'):
                for child in w.winfo_children():
                    result = search(child)
                    if result:
                        return result
            return None
        return search(parent)

class TestUIMainMenu(UITestCase):
    def test_title(self):
        self.assertEqual(self.app.title(), "Главное меню")
    
    def test_open_work_window(self):
        btn = self.find_button(self.app, "Работать")
        self.assertIsNotNone(btn)
        btn.invoke()
        self.app.update_idletasks()
        self.assertEqual(self.app.state(), 'withdrawn')
        self.assertIsNotNone(self.find_widget(self.app, WorkWindow))
    
    def test_open_help_window(self):
        btn = self.find_button(self.app, "Справка")
        self.assertIsNotNone(btn)
        btn.invoke()
        self.app.update_idletasks()
        self.assertIsNotNone(self.find_widget(self.app, HelpWindow))

class TestUIWorkWindow(UITestCase):
    def setUp(self):
        super().setUp()
        self.find_button(self.app, "Работать").invoke()
        self.app.update_idletasks()
        self.work_window = self.find_widget(self.app, WorkWindow)
        self.assertIsNotNone(self.work_window)
    
    def test_initial_state(self):
        self.assertEqual(len(self.work_window.tree.get_children()), 0)
        self.assertIn("Записей: 0", self.work_window.status_var.get())
    
    def test_add_record(self):
        initial_count = len(self.work_window.model.records)
        self.find_button(self.work_window, "Добавить").invoke()
        self.work_window.update_idletasks()
        
        dialog = None
        for child in self.work_window.winfo_children():
            if isinstance(child, tk.Toplevel):
                dialog = child
                break
        
        if dialog:
            entries = [w for w in self._get_all_children(dialog) if isinstance(w, ttk.Entry)]
            if len(entries) >= 3:
                entries[0].delete(0, tk.END)
                entries[0].insert(0, "20.03.2024")
                entries[1].insert(0, "Москва")
                entries[2].insert(0, "5.5")
                self.find_button(dialog, "Сохранить").invoke()
        
        self.work_window.update_idletasks()
        self.assertEqual(len(self.work_window.model.records), initial_count + 1)
    
    def test_go_back(self):
        self.find_button(self.work_window, "Назад").invoke()
        self.app.update_idletasks()
        self.assertEqual(self.app.state(), 'normal')
    
    def _get_all_children(self, widget):
        children = []
        for child in widget.winfo_children():
            children.append(child)
            children.extend(self._get_all_children(child))
        return children

class TestUIHelpWindow(UITestCase):
    def setUp(self):
        super().setUp()
        self.find_button(self.app, "Справка").invoke()
        self.app.update_idletasks()
        self.help_window = self.find_widget(self.app, HelpWindow)
        self.assertIsNotNone(self.help_window)
    
    def test_content(self):
        text_widget = self.find_widget(self.help_window, scrolledtext.ScrolledText)
        if text_widget:
            self.assertIn("Формат данных", text_widget.get("1.0", tk.END))
    
    def test_close(self):
        self.find_button(self.help_window, "Назад").invoke()
        self.app.update_idletasks()
        try:
            self.help_window.state()
            self.fail("Окно должно быть закрыто")
        except tk.TclError:
            pass

# ============================================================
# ЗАПУСК
# ============================================================

def run_tests():
    """Запуск всех тестов"""
    logging.disable(logging.CRITICAL)
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestTemperatureModel))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUIMainMenu))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUIWorkWindow))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUIHelpWindow))
    
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    logging.disable(logging.NOTSET)
    
    print(f"\n{'='*40}\nРезультат: {'✓ ПРОЙДЕНЫ' if result.wasSuccessful() else '✗ ПРОВАЛЕНЫ'}\n{'='*40}\n")
    return result.wasSuccessful()

def main():
    if os.name == 'nt':
        os.system('chcp 1251 > nul')
    
    if not run_tests():
        if input("Тесты не пройдены. Продолжить? (y/n): ").lower() != 'y':
            sys.exit(1)
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                       handlers=[logging.FileHandler('app.log', encoding='utf-8', mode='w'), logging.StreamHandler()])
    
    MainMenu().mainloop()

if __name__ == "__main__":
    main()