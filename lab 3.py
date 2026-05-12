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
        try:
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
        except FileNotFoundError:
            logging.error("Файл не найден: %s", filename)
            raise
        except Exception as e:
            logging.error("Ошибка при загрузке файла %s: %s", filename, e)
            raise

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
        
        image_path = os.path.join(os.path.dirname(__file__), "foto.jpg")
        if PIL_AVAILABLE and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((300, 200))
                photo = ImageTk.PhotoImage(img)
                label = ttk.Label(self, image=photo)
                label.image = photo
                label.pack(pady=10)
            except Exception as e:
                logging.error("Ошибка загрузки изображения: %s", e)
        
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
        
        logging.info("Открыто окно работы с данными")
    
    def _init_ui(self):
        # Меню
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть", command=self._load_file)
        file_menu.add_command(label="Сохранить", command=self._save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Закрыть", command=self._go_back)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

        # Панель инструментов
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Загрузить", command=self._load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Сохранить", command=self._save_file).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)
        ttk.Button(toolbar, text="Добавить", command=self._add_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Удалить", command=self._delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Назад", command=self._go_back).pack(side=tk.RIGHT, padx=20)

        # Таблица
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=("date", "location", "value"), show="headings")
        self.tree.heading("date", text="Дата")
        self.tree.heading("location", text="Место")
        self.tree.heading("value", text="Температура (°C)")
        self.tree.column("date", width=120, anchor="center")
        self.tree.column("location", width=350, anchor="w")
        self.tree.column("value", width=150, anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_var = tk.StringVar(value="Готов к работе")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X)

    def _refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
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
            except FileNotFoundError:
                messagebox.showerror("Ошибка", "Файл не найден")
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
        
        ttk.Label(frame, text="Дата (ДД.ММ.ГГГГ):").grid(row=0, column=0, sticky=tk.W, pady=5)
        date_entry = ttk.Entry(frame, width=25)
        date_entry.insert(0, datetime.date.today().strftime("%d.%m.%Y"))
        date_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Место:").grid(row=1, column=0, sticky=tk.W, pady=5)
        location_entry = ttk.Entry(frame, width=25)
        location_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(frame, text="Температура:").grid(row=2, column=0, sticky=tk.W, pady=5)
        value_entry = ttk.Entry(frame, width=25)
        value_entry.grid(row=2, column=1, pady=5)

        def save():
            try:
                line = f"{date_entry.get()},{location_entry.get()},{value_entry.get()}"
                record = self.model.parse_line(line)
                if record:
                    self.model.records.append(record)
                    logging.info("Добавлена запись: %s, %s, %.1f", record.date_str, record.location, record.value)
                    self._refresh_table()
                    dialog.destroy()
            except InvalidDataError as e:
                logging.error("Ошибка ввода данных: %s", e)
                messagebox.showerror("Ошибка ввода", str(e))

        ttk.Button(frame, text="Сохранить", command=save).grid(row=3, column=0, pady=20)
        ttk.Button(frame, text="Отмена", command=dialog.destroy).grid(row=3, column=1, pady=20)
        
        dialog.bind('<Return>', lambda e: save())
        date_entry.focus()

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить {len(selected)} записей?"):
            for item in reversed(selected):
                index = self.tree.index(item)
                record = self.model.records[index]
                logging.info("Удалена запись: %s, %s, %.1f", record.date_str, record.location, record.value)
                self.model.delete_record(index)
            self._refresh_table()

    def _go_back(self):
        logging.info("Закрыто окно работы с данными")
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
        
        self.protocol("WM_DELETE_WINDOW", self.quit)
    
    def _open_work(self):
        self.withdraw()
        WorkWindow(self, self.model)
    
    def _open_help(self):
        HelpWindow(self)
    
    def quit(self):
        logging.info("Программа завершена")
        super().quit()

# ============================================================
# ТЕСТЫ
# ============================================================

class TestTemperatureModel(unittest.TestCase):
    def setUp(self):
        self.model = TemperatureModel()

    def test_1_valid_line(self):
        line = "15.03.2024,Москва,-5.5"
        record = self.model.parse_line(line)
        self.assertEqual(record.date_str, "15.03.2024")
        self.assertEqual(record.location, "Москва")
        self.assertEqual(record.value, -5.5)

    def test_2_invalid_date_format(self):
        line = "2024.03.15,Москва,-5.5"
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_3_invalid_date_value(self):
        line = "32.13.2024,Москва,-5.5"
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_4_missing_fields(self):
        line = "15.03.2024,Москва"
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_5_invalid_number(self):
        line = "15.03.2024,Москва,не_число"
        with self.assertRaises(InvalidDataError):
            self.model.parse_line(line)

    def test_6_empty_string(self):
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("")

    def test_7_add_record(self):
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.assertEqual(len(self.model.records), 1)
        self.assertEqual(self.model.records[0].location, "Москва")

    def test_8_delete_record(self):
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.delete_record(0)
        self.assertEqual(len(self.model.records), 0)

# ============================================================
# ЗАПУСК
# ============================================================

def main():
    if os.name == 'nt':
        os.system('chcp 1251 > nul')
    
    print("\n" + "=" * 40)
    print("ВЫПОЛНЕНИЕ ПРОВЕРОЧНЫХ ТЕСТОВ")
    
    # Отключаем логирование на время тестов
    logging.disable(logging.CRITICAL)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTemperatureModel)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Включаем логирование обратно
    logging.disable(logging.NOTSET)
    
    print("=" * 40 + "\n")
    
    if result.wasSuccessful():
        # Настраиваем логирование только после тестов
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler('app.log', encoding='utf-8', mode='w'),  # mode='w' перезаписывает файл
                logging.StreamHandler()
            ]
        )
        
        app = MainMenu()
        app.mainloop()
    else:
        print("ОШИБКА: Тесты не пройдены. Исправьте модель перед запуском интерфейса.")

if __name__ == "__main__":
    main()