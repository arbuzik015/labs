"""
Представление (GUI) для учета температуры
Использует Tkinter
"""

import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import logging
from typing import Optional

# Попытка импорта PIL для изображений
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from model import TemperatureModel, InvalidDataError

class HelpView(tk.Toplevel):
    """Окно справки"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Справка")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        self._init_ui()
    
    def _init_ui(self):
        # Попытка загрузить изображение
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
        
        # Текст справки
        text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=10)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, "Формат данных:\nДД.ММ.ГГГГ,Место,Температура\n\n"
                          "Пример:\n15.03.2024,Москва,-5.5")
        text.config(state=tk.DISABLED)
        
        # Кнопка закрытия
        ttk.Button(self, text="Назад", command=self.destroy).pack(pady=10)

class WorkView(tk.Toplevel):
    """Рабочее окно с таблицей данных"""
    
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
        """Обновление таблицы"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in self.model.get_records():
            self.tree.insert("", tk.END, values=(r.date_str, r.location, f"{r.value:.1f}"))
        status = f"Файл: {os.path.basename(self.current_filename)} | " if self.current_filename else ""
        self.status_var.set(f"{status}Записей: {self.model.count()}")

    def _load_file(self):
        """Загрузка из файла"""
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
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
                filetypes=[("Text files", "*.txt")]
            )
            if not self.current_filename:
                return
        
        if self.model.save_to_file(self.current_filename):
            messagebox.showinfo("Успех", f"Сохранено в {os.path.basename(self.current_filename)}")
            self._refresh_table()
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить файл")

    def _add_dialog(self):
        """Диалог добавления записи"""
        dialog = tk.Toplevel(self)
        dialog.title("Добавить запись")
        dialog.geometry("350x180")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Поля ввода
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
                    self.model.add_record(record.date_str, record.location, record.value)
                    logging.info("Добавлена запись: %s, %s, %.1f", 
                               record.date_str, record.location, record.value)
                    dialog.destroy()
            except InvalidDataError as e:
                logging.error("Ошибка ввода данных: %s", e)
                messagebox.showerror("Ошибка ввода", str(e))

        ttk.Button(frame, text="Сохранить", command=save).grid(row=3, column=0, pady=20)
        ttk.Button(frame, text="Отмена", command=dialog.destroy).grid(row=3, column=1, pady=20)
        
        dialog.bind('<Return>', lambda e: save())
        date_entry.focus()

    def _delete_selected(self):
        """Удаление выбранных записей"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить {len(selected)} записей?"):
            for item in reversed(selected):
                index = self.tree.index(item)
                record = self.model.get_record(index)
                if record:
                    logging.info("Удалена запись: %s, %s, %.1f", 
                               record.date_str, record.location, record.value)
                self.model.delete_record(index)

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
        self.geometry("300x250")
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