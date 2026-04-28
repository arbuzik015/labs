"""
Представление (GUI) для учета температуры
Использует Tkinter
"""

import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import logging
from typing import Optional

from model import TemperatureModel, InvalidDataError


class HelpView(tk.Toplevel):
    """Окно справки"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Справка")
        self.geometry("550x450")
        self.transient(parent)
        self.grab_set()
        self._init_ui()
    
    def _init_ui(self):
        # Заголовок
        title_label = tk.Label(
            self, 
            text="Инструкция по работе с программой", 
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=10)
        
        # Текст справки с прокруткой
        text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15, width=60)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_text = """
=== ФОРМАТ ДАННЫХ ===
Каждая запись имеет формат: ДД.ММ.ГГГГ,Место,Температура

Пример:
15.03.2024,Москва,-5.5
20.03.2024,Санкт-Петербург,10.2

=== ФОРМАТ КОМАНДНОГО ФАЙЛА ===
Файл с командами может содержать следующие команды:

1. ADD <данные> - добавление записи
   Формат: ADD ДД.ММ.ГГГГ;Место;Температура
   Пример: ADD 28.03.2024;Москва;12.5
   
2. REM <условие> - удаление записей по условию
   Поддерживаемые поля: date, location, value
   Операторы: ==, !=, <, >, <=, >=, contains (только для location)
   
   Примеры:
   REM value < 0
   REM location == Москва
   REM date > 15.03.2024
   REM location contains петер

3. SAVE <filename> - сохранение данных в файл
   Пример: SAVE result.txt

Комментарии начинаются с символа #

=== ПРИМЕР КОМАНДНОГО ФАЙЛА ===
# Добавляем записи
ADD 20.03.2024;Москва;5.5
ADD 21.03.2024;Санкт-Петербург;3.2
ADD 22.03.2024;Казань;-2.0

# Удаляем записи с отрицательной температурой
REM value < 0

# Сохраняем результат
SAVE filtered_data.txt
"""
        
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        # Кнопка закрытия
        ttk.Button(self, text="Закрыть", command=self.destroy).pack(pady=10)


class WorkView(tk.Toplevel):
    """Рабочее окно с таблицей данных"""
    
    def __init__(self, parent, model: TemperatureModel):
        super().__init__(parent)
        self.parent = parent
        self.model = model
        self.current_filename: Optional[str] = None
        
        self.title("Учет температуры")
        self.geometry("900x550")
        
        self._init_ui()
        self._refresh_table()
        self.protocol("WM_DELETE_WINDOW", self._go_back)
        
        # Подписываемся на изменения модели
        self.model.add_observer(self._refresh_table)
        
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
        
        ttk.Button(toolbar, text=" Открыть данные", command=self._load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=" Сохранить данные", command=self._save_file).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(toolbar, text=" Добавить", command=self._add_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=" Удалить", command=self._delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(toolbar, text=" Выполнить команды", command=self._execute_commands).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=" Справка", command=self._open_help).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Назад", command=self._go_back).pack(side=tk.RIGHT, padx=20)
        
        # Таблица
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(
            tree_frame, 
            columns=("date", "location", "value"), 
            show="headings",
            selectmode="extended"
        )
        
        self.tree.heading("date", text="Дата")
        self.tree.heading("location", text="Местоположение")
        self.tree.heading("value", text="Температура (°C)")
        
        self.tree.column("date", width=120, anchor="center")
        self.tree.column("location", width=350, anchor="w")
        self.tree.column("value", width=150, anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Двойной клик для редактирования
        self.tree.bind('<Double-1>', self._edit_item_dialog)
        
        # Статусная строка
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _refresh_table(self):
        """Обновление таблицы"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for record in self.model.get_records():
            # Форматирование значения
            if record.value == int(record.value):
                value_str = f"{int(record.value)}"
            else:
                value_str = f"{record.value:.2f}".rstrip('0').rstrip('.')
            
            self.tree.insert("", tk.END, values=(record.date_str, record.location, value_str))
        
        status = f"Файл: {self.current_filename or 'не выбран'} | " if self.current_filename else ""
        self.status_var.set(f"{status}Записей: {self.model.count()}")
    
    def _load_file(self):
        """Загрузка из файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл данных",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                count = self.model.load_from_file(filename)
                self.current_filename = filename
                messagebox.showinfo("Успех", f"Загружено {count} записей")
            except FileNotFoundError:
                messagebox.showerror("Ошибка", "Файл не найден")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")
    
    def _save_file(self):
        """Сохранение в файл"""
        if self.model.count() == 0:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return
        
        if not self.current_filename:
            self.current_filename = filedialog.asksaveasfilename(
                defaultextension=".txt", 
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not self.current_filename:
                return
        
        if self.model.save_to_file(self.current_filename):
            messagebox.showinfo("Успех", f"Сохранено в {self.current_filename}")
            self._refresh_table()
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить файл")
    
    def _add_dialog(self):
        """Диалог добавления записи"""
        dialog = tk.Toplevel(self)
        dialog.title("Добавить запись")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Дата (ДД.ММ.ГГГГ):").grid(row=0, column=0, sticky=tk.W, pady=5)
        date_entry = ttk.Entry(frame, width=25)
        date_entry.insert(0, datetime.datetime.now().strftime("%d.%m.%Y"))
        date_entry.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(frame, text="Местоположение:").grid(row=1, column=0, sticky=tk.W, pady=5)
        location_entry = ttk.Entry(frame, width=25)
        location_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(frame, text="Температура:").grid(row=2, column=0, sticky=tk.W, pady=5)
        value_entry = ttk.Entry(frame, width=25)
        value_entry.grid(row=2, column=1, pady=5, padx=10)
        
        def save():
            try:
                line = f"{date_entry.get()},{location_entry.get()},{value_entry.get()}"
                record = self.model.parse_line(line)
                self.model.add_record(record.date_str, record.location, record.value)
                logging.info("Добавлена запись: %s, %s, %.1f", 
                           record.date_str, record.location, record.value)
                dialog.destroy()
            except InvalidDataError as e:
                messagebox.showerror("Ошибка ввода", str(e), parent=dialog)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Сохранить", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.bind('<Return>', lambda e: save())
        date_entry.focus()
    
    def _edit_item_dialog(self, event):
        """Диалог редактирования записи"""
        selected = self.tree.selection()
        if not selected:
            return
        
        index = self.tree.index(selected[0])
        record = self.model.get_record(index)
        if not record:
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("Редактировать запись")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Дата (ДД.ММ.ГГГГ):").grid(row=0, column=0, sticky=tk.W, pady=5)
        date_entry = ttk.Entry(frame, width=25)
        date_entry.insert(0, record.date_str)
        date_entry.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(frame, text="Местоположение:").grid(row=1, column=0, sticky=tk.W, pady=5)
        location_entry = ttk.Entry(frame, width=25)
        location_entry.insert(0, record.location)
        location_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(frame, text="Температура:").grid(row=2, column=0, sticky=tk.W, pady=5)
        value_entry = ttk.Entry(frame, width=25)
        value_entry.insert(0, str(record.value))
        value_entry.grid(row=2, column=1, pady=5, padx=10)
        
        def save():
            try:
                line = f"{date_entry.get()},{location_entry.get()},{value_entry.get()}"
                new_record = self.model.parse_line(line)
                self.model.delete_record(index)
                self.model.add_record(new_record.date_str, new_record.location, new_record.value)
                dialog.destroy()
            except InvalidDataError as e:
                messagebox.showerror("Ошибка", str(e), parent=dialog)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Сохранить", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _delete_selected(self):
        """Удаление выбранных записей"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить {len(selected)} записей?"):
            indices = [self.tree.index(item) for item in selected]
            for index in sorted(indices, reverse=True):
                record = self.model.get_record(index)
                if record:
                    logging.info("Удалена запись: %s, %s, %.1f", 
                               record.date_str, record.location, record.value)
                self.model.delete_record(index)
    
    def _execute_commands(self):
        """Выполнение команд из файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл команд",
            filetypes=[("Command files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            errors = self.model.apply_commands_file(filename)
            
            if errors:
                result_msg = f"⚠ Выполнено с ошибками:\n\n" + "\n".join(errors[:15])
                if len(errors) > 15:
                    result_msg += f"\n... и еще {len(errors) - 15} ошибок"
                messagebox.showwarning("Результат выполнения команд", result_msg)
            else:
                messagebox.showinfo("Результат выполнения команд", " Все команды выполнены успешно")
            
            self._refresh_table()
            
        except FileNotFoundError:
            messagebox.showerror("Ошибка", f"Файл не найден: {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обработать команды:\n{e}")
    
    def _open_help(self):
        """Открыть окно справки"""
        HelpView(self)
    
    def _go_back(self):
        """Возврат в главное меню"""
        logging.info("Закрыто окно работы с данными")
        self.parent.deiconify()
        self.destroy()


class MainView(tk.Tk):
    """Главное меню приложения"""
    
    def __init__(self, model: TemperatureModel):
        super().__init__()
        self.model = model
        
        self.title("Главное меню")
        self.geometry("300x280")
        self.resizable(False, False)
        
        self._init_ui()
        self.protocol("WM_DELETE_WINDOW", self.quit)
    
    def _init_ui(self):
        tk.Label(self, text="Учет температуры", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        frame = tk.Frame(self)
        frame.pack(expand=True)
        
        buttons = [
            ("Работать", self._open_work, '#4CAF50'),
            ("Справка", self._open_help, '#2196F3'),
            ("Выход", self.quit, '#f44336')
        ]
        
        for text, cmd, color in buttons:
            tk.Button(frame, text=text, command=cmd, bg=color, fg='white',
                     font=('Arial', 11, 'bold'), width=15).pack(pady=5)
    
    def _open_work(self):
        """Открыть рабочее окно"""
        self.withdraw()
        WorkView(self, self.model)
    
    def _open_help(self):
        """Открыть справку"""
        HelpView(self)
    
    def quit(self):
        """Выход из приложения"""
        logging.info("Программа завершена")
        super().quit()