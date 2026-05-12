"""
Программа для учета температуры с поддержкой командного файла
Формат данных: ДД.ММ.ГГГГ,Место,Температура
Формат команд: ADD ДД.ММ.ГГГГ; Место; Температура
"""

import logging
import os
import re
import tempfile
import tkinter as tk
import unittest
from datetime import datetime
from tkinter import filedialog, messagebox, ttk, scrolledtext


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class InvalidDataError(Exception):
    """Ошибка валидации данных"""
    pass


class TemperatureReading:
    """Запись о температуре"""
    def __init__(self, date_str: str, location: str, value: float):
        self.date_str = date_str      # ДД.ММ.ГГГГ
        self.location = location       # Местоположение
        self.value = value             # Температура


class TemperatureModel:
    """Модель для работы с данными температуры"""
    
    def __init__(self):
        self.readings = []  # Список записей
    
    def parse_line(self, line: str) -> TemperatureReading:
        """
        Парсинг строки в запись
        Формат: ДД.ММ.ГГГГ,Место,Температура
        """
        line = line.strip()
        if not line:
            raise InvalidDataError("Пустая строка")
        
        # Поддерживаем разделители , и ;
        if ';' in line:
            parts = [p.strip() for p in line.split(';')]
        else:
            parts = [p.strip() for p in line.split(',')]
        
        if len(parts) != 3:
            raise InvalidDataError(
                f'Строка должна быть в формате: "ДД.ММ.ГГГГ,Место,Температура" или '
                f'"ДД.ММ.ГГГГ; Место; Температура". Получено полей: {len(parts)}'
            )
        
        date_str, location, value_str = parts
        
        # Проверка формата даты ДД.ММ.ГГГГ
        if not re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", date_str):
            raise InvalidDataError(f"Неверный формат даты: {date_str}. Ожидается ДД.ММ.ГГГГ")
        
        # Проверка корректности даты
        try:
            day, month, year = map(int, date_str.split('.'))
            datetime(year, month, day)
        except ValueError as e:
            raise InvalidDataError(f"Некорректная дата: {date_str} - {e}")
        
        # Проверка температуры
        try:
            value = float(value_str.replace(',', '.'))
        except ValueError:
            raise InvalidDataError(f"Некорректное значение температуры: {value_str}")
        
        if not location:
            raise InvalidDataError("Местоположение не может быть пустым")
        
        return TemperatureReading(date_str, location, value)
    
    def load_from_file(self, filename: str):
        """Загрузка данных из файла"""
        self.readings = []
        
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        reading = self.parse_line(line)
                        self.readings.append(reading)
                    except InvalidDataError as e:
                        logging.error("[Файл: %s, Строка: %s] %s", filename, line_num, e)
        except FileNotFoundError:
            logging.warning("Файл %s не найден.", filename)
    
    def save_to_file(self, filename: str):
        """Сохранение данных в файл"""
        with open(filename, "w", encoding="utf-8") as file:
            for reading in self.readings:
                file.write(f"{reading.date_str},{reading.location},{reading.value}\n")
        logging.info("Сохранено %d записей в %s", len(self.readings), filename)
    
    def add_from_csv(self, csv_data: str):
        """
        Добавление записи из CSV строки для команды ADD
        Формат: ДД.ММ.ГГГГ; Место; Температура
        """
        parts = [part.strip() for part in csv_data.split(";")]
        if len(parts) != 3:
            raise InvalidDataError(
                "ADD: нужно 3 поля: дата; место; температура"
            )
        
        date_str, location, value_str = parts
        raw_line = f"{date_str},{location},{value_str}"
        reading = self.parse_line(raw_line)
        self.readings.append(reading)
        logging.info("ADD: добавлена запись %s, %s, %s", date_str, location, value_str)
    
    def remove_by_condition(self, condition: str):
        """
        Удаление записей по условию для команды REM
        Поддерживаемые поля: date, location, value
        Операторы: ==, !=, <, >, <=, >=, contains (только для location)
        """
        condition = condition.strip()
        
        match = re.fullmatch(
            r'(date|location|value)\s*(==|!=|<=|>=|<|>|contains)\s*(.+)',
            condition
        )
        if not match:
            raise InvalidDataError(
                "REM: неверное условие. Примеры:\n"
                "  value < 100\n"
                "  location == Москва\n"
                "  date > 15.03.2024\n"
                "  location contains петер"
            )
        
        field_name, operator, raw_value = match.groups()
        raw_value = raw_value.strip()
        
        # Убираем кавычки, если есть
        if (raw_value.startswith('"') and raw_value.endswith('"')) or \
           (raw_value.startswith("'") and raw_value.endswith("'")):
            raw_value = raw_value[1:-1]
        
        def check(reading: TemperatureReading) -> bool:
            if field_name == "value":
                try:
                    left = reading.value
                    right = float(raw_value.replace(',', '.'))
                except ValueError:
                    raise InvalidDataError("REM: значение для поля value должно быть числом")
                
                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "<":
                    return left < right
                if operator == ">":
                    return left > right
                if operator == "<=":
                    return left <= right
                if operator == ">=":
                    return left >= right
                raise InvalidDataError(f"REM: неподдерживаемый оператор {operator} для value")
            
            elif field_name == "date":
                try:
                    left = reading.date_str
                    right = raw_value
                    
                    # Проверка формата даты
                    if not re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", right):
                        raise InvalidDataError("REM: дата должна быть в формате ДД.ММ.ГГГГ")
                    
                    if operator == "==":
                        return left == right
                    if operator == "!=":
                        return left != right
                    if operator == "<":
                        return left < right
                    if operator == ">":
                        return left > right
                    if operator == "<=":
                        return left <= right
                    if operator == ">=":
                        return left >= right
                except Exception:
                    raise InvalidDataError(f"REM: ошибка при сравнении дат")
            
            elif field_name == "location":
                left = reading.location.lower()
                right = raw_value.lower()
                
                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "contains":
                    return right in left
                raise InvalidDataError(f"REM: для location поддерживаются только ==, !=, contains")
            
            return False
        
        old_count = len(self.readings)
        self.readings = [r for r in self.readings if not check(r)]
        removed = old_count - len(self.readings)
        logging.info("REM: удалено %d записей по условию '%s'", removed, condition)
    
    def execute_command(self, command_line: str):
        """Выполнение одной команды"""
        command_line = command_line.strip()
        if not command_line or command_line.startswith('#'):
            return
        
        parts = command_line.split(maxsplit=1)
        command = parts[0].upper()
        argument = parts[1].strip() if len(parts) > 1 else ""
        
        if command == "ADD":
            if not argument:
                raise InvalidDataError("ADD: не указаны данные")
            self.add_from_csv(argument)
        elif command == "REM":
            if not argument:
                raise InvalidDataError("REM: не указано условие")
            self.remove_by_condition(argument)
        elif command == "SAVE":
            if not argument:
                raise InvalidDataError("SAVE: не указано имя файла")
            self.save_to_file(argument)
        else:
            raise InvalidDataError(f"Неизвестная команда: {command}")
    
    def apply_commands_file(self, filename: str):
        """Применение файла с командами"""
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        self.execute_command(line)
                    except InvalidDataError as e:
                        logging.error("[Файл команд: %s, Строка: %s] %s", filename, line_num, e)
        except FileNotFoundError:
            logging.warning("Файл команд %s не найден.", filename)
            raise


class HelpView(tk.Toplevel):
    """Окно справки"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Справка")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        self._init_ui()
    
    def _init_ui(self):
        # Заголовок
        title = tk.Label(self, text="Инструкция по работе с программой", 
                        font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Текст справки с прокруткой
        text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=18, width=70)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_text = """
╔══════════════════════════════════════════════════════════════════════╗
║                        ФОРМАТ ДАННЫХ                                 ║
╚══════════════════════════════════════════════════════════════════════╝

Каждая запись имеет формат: ДД.ММ.ГГГГ,Место,Температура

Примеры:
  15.03.2024,Москва,-5.5
  20.03.2024,Санкт-Петербург,10.2
  25.03.2024,Казань,0.0

╔══════════════════════════════════════════════════════════════════════╗
║                        КОМАНДНЫЙ ФАЙЛ                                ║
╚══════════════════════════════════════════════════════════════════════╝

Файл с командами может содержать следующие команды:

1. ADD <данные> - добавление записи
   Формат: ADD ДД.ММ.ГГГГ; Место; Температура
   Пример: ADD 28.03.2024; Москва; 12.5
   
2. REM <условие> - удаление записей по условию
   Поля: date, location, value
   Операторы: ==, !=, <, >, <=, >=, contains (только для location)
   
   Примеры:
   REM value < 0              # отрицательная температура
   REM location == Москва     # точное совпадение
   REM location contains петер # частичное совпадение
   REM date > 20.03.2024      # после указанной даты
   REM value >= 10            # температура от 10 и выше

3. SAVE <filename> - сохранение данных в файл
   Пример: SAVE result.txt

Комментарии начинаются с символа #

╔══════════════════════════════════════════════════════════════════════╗
║                        ПРИМЕР КОМАНДНОГО ФАЙЛА                       ║
╚══════════════════════════════════════════════════════════════════════╝

# Добавляем записи
ADD 20.03.2024; Москва; 5.5
ADD 21.03.2024; Санкт-Петербург; 3.2
ADD 22.03.2024; Казань; -2.0
ADD 23.03.2024; Новосибирск; -15.5

# Удаляем записи с отрицательной температурой
REM value < 0

# Сохраняем результат
SAFE filtered_data.txt

╔══════════════════════════════════════════════════════════════════════╗
║                        УПРАВЛЕНИЕ ПРОГРАММОЙ                         ║
╚══════════════════════════════════════════════════════════════════════╝

• Открыть данные - загрузить данные из текстового файла
• Сохранить данные - сохранить текущие данные в файл
• Добавить - добавить новую запись через диалоговое окно
• Удалить - удалить выбранные записи из таблицы
• Выполнить команды - загрузить и выполнить файл с командами
• Двойной клик по записи - редактирование записи
"""
        
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        # Кнопка закрытия
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Закрыть", command=self.destroy, 
                 bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                 width=15).pack()


class TemperatureView:
    """Главное окно приложения"""
    
    def __init__(self, window, model: TemperatureModel):
        self.root = window
        self.model = model
        self.root.title("Учет температуры")
        self.root.geometry("850x500")
        
        self._init_ui()
        self.refresh_table()
    
    def _init_ui(self):
        # Панель инструментов
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        buttons = [
            ("📂 Открыть данные", self.open_data_file, '#4CAF50'),
            ("💾 Сохранить данные", self.save_data_file, '#2196F3'),
            ("➕ Добавить", self.add_item_dialog, '#FF9800'),
            ("✖ Удалить", self.delete_item, '#f44336'),
            ("⚙ Выполнить команды", self.open_commands_file, '#9C27B0'),
            ("❓ Справка", self.open_help, '#607D8B'),
        ]
        
        for text, cmd, color in buttons:
            btn = tk.Button(toolbar, text=text, command=cmd, bg=color, 
                           fg='white', font=('Arial', 9, 'bold'),
                           padx=10, pady=3)
            btn.pack(side=tk.LEFT, padx=3)
        
        # Таблица для отображения данных
        columns_frame = tk.Frame(self.root)
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(
            columns_frame,
            columns=("date", "location", "value"),
            show="headings",
            selectmode="extended"
        )
        
        # Настройка колонок
        self.tree.heading("date", text="Дата (ДД.ММ.ГГГГ)")
        self.tree.heading("location", text="Местоположение")
        self.tree.heading("value", text="Температура (°C)")
        
        self.tree.column("date", width=130, anchor="center")
        self.tree.column("location", width=350, anchor="w")
        self.tree.column("value", width=150, anchor="center")
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(columns_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Двойной клик для редактирования
        self.tree.bind('<Double-1>', self.edit_item_dialog)
        
        # Строка статуса
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W, padx=5)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def refresh_table(self):
        """Обновление таблицы"""
        self.tree.delete(*self.tree.get_children())
        
        for reading in self.model.readings:
            # Форматирование значения температуры
            if reading.value == int(reading.value):
                value_str = f"{int(reading.value)}"
            else:
                value_str = f"{reading.value:.1f}"
            
            self.tree.insert("", tk.END, values=(
                reading.date_str,
                reading.location,
                value_str
            ))
        
        self.status_var.set(f"Записей: {len(self.model.readings)}")
    
    def add_item_dialog(self):
        """Диалог добавления записи"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить запись")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Поле даты
        tk.Label(main_frame, text="Дата (ДД.ММ.ГГГГ):", font=('Arial', 10)).grid(row=0, column=0, sticky='w', pady=5)
        date_entry = tk.Entry(main_frame, width=25, font=('Arial', 10))
        date_entry.insert(0, datetime.now().strftime("%d.%m.%Y"))
        date_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # Поле местоположения
        tk.Label(main_frame, text="Местоположение:", font=('Arial', 10)).grid(row=1, column=0, sticky='w', pady=5)
        location_entry = tk.Entry(main_frame, width=25, font=('Arial', 10))
        location_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Поле температуры
        tk.Label(main_frame, text="Температура:", font=('Arial', 10)).grid(row=2, column=0, sticky='w', pady=5)
        value_entry = tk.Entry(main_frame, width=25, font=('Arial', 10))
        value_entry.grid(row=2, column=1, pady=5, padx=10)
        
        def save():
            try:
                line = f"{date_entry.get()},{location_entry.get()},{value_entry.get()}"
                reading = self.model.parse_line(line)
                self.model.readings.append(reading)
                self.refresh_table()
                dialog.destroy()
                logging.info("Добавлена запись: %s, %s, %.1f", 
                           reading.date_str, reading.location, reading.value)
            except InvalidDataError as e:
                messagebox.showerror("Ошибка ввода", str(e), parent=dialog)
        
        # Кнопки
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="Сохранить", command=save, bg='#4CAF50', 
                 fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy, bg='#f44336',
                 fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        
        dialog.bind('<Return>', lambda e: save())
        date_entry.focus()
    
    def edit_item_dialog(self, event):
        """Диалог редактирования записи"""
        selected = self.tree.selection()
        if not selected:
            return
        
        index = self.tree.index(selected[0])
        reading = self.model.readings[index]
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактировать запись")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Дата (ДД.ММ.ГГГГ):", font=('Arial', 10)).grid(row=0, column=0, sticky='w', pady=5)
        date_entry = tk.Entry(main_frame, width=25, font=('Arial', 10))
        date_entry.insert(0, reading.date_str)
        date_entry.grid(row=0, column=1, pady=5, padx=10)
        
        tk.Label(main_frame, text="Местоположение:", font=('Arial', 10)).grid(row=1, column=0, sticky='w', pady=5)
        location_entry = tk.Entry(main_frame, width=25, font=('Arial', 10))
        location_entry.insert(0, reading.location)
        location_entry.grid(row=1, column=1, pady=5, padx=10)
        
        tk.Label(main_frame, text="Температура:", font=('Arial', 10)).grid(row=2, column=0, sticky='w', pady=5)
        value_entry = tk.Entry(main_frame, width=25, font=('Arial', 10))
        value_entry.insert(0, str(reading.value))
        value_entry.grid(row=2, column=1, pady=5, padx=10)
        
        def save():
            try:
                line = f"{date_entry.get()},{location_entry.get()},{value_entry.get()}"
                new_reading = self.model.parse_line(line)
                self.model.readings[index] = new_reading
                self.refresh_table()
                dialog.destroy()
                logging.info("Отредактирована запись: %s, %s, %.1f", 
                           new_reading.date_str, new_reading.location, new_reading.value)
            except InvalidDataError as e:
                messagebox.showerror("Ошибка ввода", str(e), parent=dialog)
        
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="Сохранить", command=save, bg='#4CAF50',
                 fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy, bg='#f44336',
                 fg='white', padx=20).pack(side=tk.LEFT, padx=5)
    
    def delete_item(self):
        """Удаление выбранных записей"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить {len(selected)} записей?"):
            # Удаляем с конца, чтобы не сбивать индексы
            indices = [self.tree.index(item) for item in selected]
            for index in sorted(indices, reverse=True):
                deleted = self.model.readings.pop(index)
                logging.info("Удалена запись: %s, %s, %.1f", 
                           deleted.date_str, deleted.location, deleted.value)
            self.refresh_table()
    
    def open_data_file(self):
        """Открытие файла с данными"""
        filename = filedialog.askopenfilename(
            title="Выберите файл данных",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        self.model.load_from_file(filename)
        self.refresh_table()
        messagebox.showinfo("Успех", f"Загружено {len(self.model.readings)} записей")
    
    def open_commands_file(self):
        """Открытие и выполнение файла с командами"""
        filename = filedialog.askopenfilename(
            title="Выберите файл команд",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            self.model.apply_commands_file(filename)
            self.refresh_table()
            messagebox.showinfo("Готово", "Команды применены")
        except FileNotFoundError:
            messagebox.showerror("Ошибка", f"Файл не найден: {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при выполнении команд:\n{e}")
    
    def save_data_file(self):
        """Сохранение данных в файл"""
        if not self.model.readings:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Сохранить данные",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        self.model.save_to_file(filename)
        messagebox.showinfo("Успех", f"Сохранено {len(self.model.readings)} записей")
    
    def open_help(self):
        """Открыть справку"""
        HelpView(self.root)


# ==================== МОДУЛЬНЫЕ ТЕСТЫ ====================

class TestTemperatureModel(unittest.TestCase):
    """Тесты модели данных температуры"""
    
    def setUp(self):
        self.model = TemperatureModel()
    
    def test_1_valid_line(self):
        """Тест: корректная строка с запятой"""
        reading = self.model.parse_line("15.03.2024,Москва,-5.5")
        self.assertEqual(reading.date_str, "15.03.2024")
        self.assertEqual(reading.location, "Москва")
        self.assertEqual(reading.value, -5.5)
    
    def test_2_valid_line_with_semicolon(self):
        """Тест: корректная строка с точкой с запятой"""
        reading = self.model.parse_line("15.03.2024;Москва;-5.5")
        self.assertEqual(reading.value, -5.5)
    
    def test_3_invalid_date_format(self):
        """Тест: неверный формат даты"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("2024.03.15,Москва,-5.5")
    
    def test_4_invalid_date_value(self):
        """Тест: несуществующая дата"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("32.13.2024,Москва,-5.5")
    
    def test_5_missing_fields(self):
        """Тест: не хватает полей"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("15.03.2024,Москва")
    
    def test_6_invalid_number(self):
        """Тест: неверный формат числа"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("15.03.2024,Москва,не_число")
    
    def test_7_empty_line(self):
        """Тест: пустая строка"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("")
    
    def test_8_add_command(self):
        """Тест: команда ADD"""
        self.model.execute_command("ADD 20.03.2024; Москва; 10.5")
        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].location, "Москва")
        self.assertEqual(self.model.readings[0].value, 10.5)
    
    def test_9_rem_command_for_value(self):
        """Тест: REM по значению температуры"""
        self.model.execute_command("ADD 20.03.2024; Москва; 10.5")
        self.model.execute_command("ADD 21.03.2024; Киев; -2.0")
        self.model.execute_command("REM value < 0")
        
        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].location, "Москва")
    
    def test_10_rem_command_for_location(self):
        """Тест: REM по местоположению"""
        self.model.execute_command("ADD 20.03.2024; Москва; 10.5")
        self.model.execute_command("ADD 21.03.2024; Киев; 5.0")
        self.model.execute_command("REM location == Москва")
        
        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].location, "Киев")
    
    def test_11_rem_command_contains(self):
        """Тест: REM с contains"""
        self.model.execute_command("ADD 20.03.2024; Санкт-Петербург; 10.5")
        self.model.execute_command("ADD 21.03.2024; Киев; 5.0")
        self.model.execute_command("REM location contains петер")
        
        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].location, "Киев")
    
    def test_12_rem_command_for_date(self):
        """Тест: REM по дате"""
        self.model.execute_command("ADD 15.03.2024; Москва; 10.5")
        self.model.execute_command("ADD 20.03.2024; Киев; 5.0")
        self.model.execute_command("REM date > 18.03.2024")
        
        self.assertEqual(len(self.model.readings), 1)
        self.assertEqual(self.model.readings[0].date_str, "15.03.2024")
    
    def test_13_save_to_file(self):
        """Тест: сохранение в файл"""
        self.model.execute_command("ADD 20.03.2024; Москва; 10.5")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = os.path.join(temp_dir, "result.txt")
            self.model.save_to_file(filename)
            
            with open(filename, "r", encoding="utf-8") as file:
                content = file.read()
            
            self.assertIn("20.03.2024,Москва,10.5", content)
    
    def test_14_apply_commands_file(self):
        """Тест: применение файла команд"""
        with tempfile.TemporaryDirectory() as temp_dir:
            commands_filename = os.path.join(temp_dir, "commands.txt")
            result_filename = os.path.join(temp_dir, "saved.txt")
            
            with open(commands_filename, "w", encoding="utf-8") as file:
                file.write("ADD 20.03.2024; Москва; 10.5\n")
                file.write("ADD 21.03.2024; Киев; -2.0\n")
                file.write("REM value < 0\n")
                file.write(f"SAVE {result_filename}\n")
            
            self.model.apply_commands_file(commands_filename)
            
            self.assertEqual(len(self.model.readings), 1)
            self.assertEqual(self.model.readings[0].location, "Москва")
            self.assertTrue(os.path.exists(result_filename))


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ВЫПОЛНЕНИЕ ПРОВЕРОЧНЫХ ТЕСТОВ")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTemperatureModel)
    test_result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    print("=" * 60 + "\n")
    
    if test_result.wasSuccessful():
        # Запуск GUI приложения
        root = tk.Tk()
        model = TemperatureModel()
        
        # Попытка загрузить данные из файла по умолчанию
        if os.path.exists("data.txt"):
            model.load_from_file("data.txt")
        
        app = TemperatureView(root, model)
        root.mainloop()
    else:
        print("ОШИБКА: Тесты не пройдены. Исправьте модель перед запуском интерфейса.")