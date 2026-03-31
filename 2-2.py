"""Программа для учета температуры.

Каждая строка файла содержит данные о температуре в формате:
ДД.ММ.ГГГГ,Место,Температура,Цвет

Интерфейс:
- Главное окно — меню с тремя кнопками: «Работать», «Справка», «Выход».
- «Работать» открывает окно с таблицей температур.
- «Справка» открывает окно с изображением foto.jpg.
- «Выход» завершает программу.
"""

import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from typing import List, Optional

# Попытка импорта PIL для работы с изображениями
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ------------------------------------------------------------
# Классы для работы с температурой
# ------------------------------------------------------------

class Temperature:
    def __init__(self, date="", location="", value=0.0, color=""):
        self.date = date
        self.location = location
        self.value = value
        self.color = color
    
    def __str__(self):
        return f"{self.date},{self.location},{self.value},{self.color}"
    
    @classmethod
    def from_string(cls, s: str) -> Optional['Temperature']:
        try:
            parts = [x.strip() for x in s.strip().split(',')]
            if len(parts) == 3:  
                d, l, v = parts
                color = ""
            elif len(parts) == 4:  # Новый формат с цветом
                d, l, v, color = parts
            else:
                return None
                
            if not valid_date(d):
                return None
            try:
                val = float(v)
            except:
                return None
            return cls(d, l, val, color)
        except:
            return None


def valid_date(d: str) -> bool:
    if len(d) != 10 or d[2] != '.' or d[5] != '.':
        return False
    for i in range(10):
        if i not in (2, 5) and not d[i].isdigit():
            return False
    try:
        day = int(d[0:2])
        month = int(d[3:5])
        year = int(d[6:10])
        if month < 1 or month > 12 or day < 1 or day > 31:
            return False
        days_in_month = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        return day <= days_in_month[month - 1]
    except:
        return False


class FileManager:
    @staticmethod
    def load(filename: str) -> List[Temperature]:
        data = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        temp = Temperature.from_string(line)
                        if temp:
                            data.append(temp)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
        return data
    
    @staticmethod
    def save(filename: str, data: List[Temperature]) -> bool:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(f"{item}\n")
            return True
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return False


# ------------------------------------------------------------
# Окно справки (точно как в примере)
# ------------------------------------------------------------

class HelpWindow(tk.Toplevel):
    def __init__(self, parent_menu):
        super().__init__(parent_menu)
        self.parent_menu = parent_menu
        self.title("Справка")
        self.geometry("600x500")
        self.transient(parent_menu)
        self.grab_set()

        # Добавляем изображение (как в примере)
        self._add_image()

        # Добавляем текстовую информацию
        self._add_info()

        # Кнопка назад
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="← Назад", command=self.go_back, width=20).pack()

        self.protocol("WM_DELETE_WINDOW", self.go_back)

    def _add_image(self) -> None:
        """Добавление изображения (как в примере)"""
        image_frame = ttk.Frame(self)
        image_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        image_path = os.path.join(os.path.dirname(__file__), "foto.jpg")
        
        if PIL_AVAILABLE and os.path.exists(image_path):
            try:
                # Открываем и масштабируем изображение
                pil_image = Image.open(image_path)
                pil_image.thumbnail((400, 300))
                photo = ImageTk.PhotoImage(pil_image)
                
                # Создаем метку с изображением
                label = ttk.Label(image_frame, image=photo)
                label.image = photo  # Сохраняем ссылку
                label.pack()
                
                # Добавляем название файла
                ttk.Label(image_frame, text="foto.jpg", font=('Arial', 9, 'italic')).pack(pady=5)
                
            except Exception as e:
                ttk.Label(image_frame, text=f"Не удалось загрузить изображение: {e}").pack()
        else:
            if not PIL_AVAILABLE:
                ttk.Label(image_frame, text="PIL не установлен, изображение не загружено", 
                         foreground='red').pack()
            else:
                ttk.Label(image_frame, text="Файл foto.jpg не найден в папке программы", 
                         foreground='red').pack()

    def _add_info(self) -> None:
        """Добавление текстовой информации"""
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Заголовок
        ttk.Label(info_frame, text="Программа учета температуры", 
                 font=('Arial', 14, 'bold')).pack(pady=10)

        # Информация о программе
        info_text = """
Формат данных:
ДД.ММ.ГГГГ,Место,Температура,Цвет

Пример:
15.03.2024,Москва,-5.5,Синий

Функции:
• Загрузка данных из файла
• Сохранение данных в файл
• Добавление новых записей
• Удаление записей
• Ручной ввод цвета для каждой записи (обязательное поле)
"""
        
        text_area = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=10, font=('Courier', 10))
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, info_text)
        text_area.config(state=tk.DISABLED)

    def go_back(self) -> None:
        self.destroy()
        self.parent_menu.focus_set()


# ------------------------------------------------------------
# Окно работы
# ------------------------------------------------------------

class WorkWindow(tk.Toplevel):
    COLUMNS = ["Дата", "Место", "Температура (°C)", "Цвет"]
    
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.title("Учет температуры")
        self.geometry("850x500")
        
        self.data: List[Temperature] = []
        self.filename = "temperatures.txt"
        
        # Меню "Файл"
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть файл", command=self.open_file)
        file_menu.add_command(label="Сохранить", command=self.save)
        file_menu.add_command(label="Сохранить как...", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Закрыть окно", command=self.go_back)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)
        
        # Панель кнопок
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Добавить", command=self.add_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        
        # Кнопка "Назад" для возврата в меню
        ttk.Button(btn_frame, text="← Назад", command=self.go_back).pack(side=tk.LEFT, padx=20)
        

        # Таблица
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(frame, show="headings", columns=self.COLUMNS)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        for i, col in enumerate(self.COLUMNS):
            self.tree.heading(col, text=col)
            widths = [120, 250, 120, 100]
            anchors = ['center', 'w', 'center', 'center']
            self.tree.column(col, width=widths[i], anchor=anchors[i])
        
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        
        # Статус
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.load_default()
        self.protocol("WM_DELETE_WINDOW", self.go_back)
        self.lift()
        self.focus_force()
    

    def load_default(self):
        if os.path.exists(self.filename):
            self.data = FileManager.load(self.filename)
            self.refresh()
            self.status_var.set(f"Загружено из {self.filename}")
    
    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in self.data:
            color_display = item.color if item.color else "—"
            values = (item.date, item.location, f"{item.value:.1f}", color_display)
            self.tree.insert("", tk.END, values=values)
        self.status_var.set(f"Всего: {len(self.data)}")
    
    def go_back(self):
        self.parent_menu.show_menu()
        self.destroy()
    
    def open_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл с данными",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if filename:
            self.data = FileManager.load(filename)
            self.filename = filename
            self.refresh()
            self.status_var.set(f"Загружено: {os.path.basename(filename)}")
    
    def save(self):
        if FileManager.save(self.filename, self.data):
            messagebox.showinfo("", "Данные сохранены")
            self.status_var.set("Сохранено")
    
    def save_as(self):
        filename = filedialog.asksaveasfilename(
            title="Сохранить файл",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt")]
        )
        if filename:
            self.filename = filename
            self.save()
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("", "Ничего не выбрано")
            return
        for item in reversed(selected):
            index = self.tree.index(item)
            del self.data[index]
        self.refresh()
        self.status_var.set(f"Удалено: {len(selected)}")
    
    def add_dialog(self):
        AddDialog(self)
    
    def add(self, date, location, value, color):
        self.data.append(Temperature(date, location, value, color))
        self.refresh()
        self.status_var.set(f"Добавлено: {date}")


class AddDialog:
    def __init__(self, parent):
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title("Добавить запись")
        self.win.geometry("400x260")
        self.win.transient(parent)
        self.win.grab_set()
        
        f = ttk.Frame(self.win, padding="20")
        f.pack(fill=tk.BOTH, expand=True)
        
        labels = ["Дата (ДД.ММ.ГГГГ):", "Место:", "Температура:", "Цвет:"]
        self.entries = []
        
        for i, txt in enumerate(labels):
            ttk.Label(f, text=txt).grid(row=i, column=0, sticky=tk.W, pady=5)
            e = ttk.Entry(f, width=25)
            e.grid(row=i, column=1, pady=5, padx=10)
            self.entries.append(e)
        
        bf = ttk.Frame(f)
        bf.grid(row=4, column=0, columnspan=2, pady=20)
        ttk.Button(bf, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(bf, text="Отмена", command=self.win.destroy).pack(side=tk.LEFT, padx=10)
        
        self.win.bind('<Return>', lambda e: self.ok())
        
        # Центрирование
        self.win.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.win.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.win.winfo_height()) // 2
        self.win.geometry(f'+{x}+{y}')
        self.entries[0].focus()
    
    def ok(self):
        vals = [e.get().strip() for e in self.entries]
        
        # Проверка заполнения всех полей
        if not all(vals):
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены!")
            return
        
        if not valid_date(vals[0]):
            messagebox.showerror("Ошибка", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        
        try:
            temperature = float(vals[2].replace(',', '.'))
        except ValueError:
            messagebox.showerror("Ошибка", "Температура должна быть числом")
            return
        
        # Цвет уже проверен на пустоту через all(vals)
        color = vals[3]
        
        self.parent.add(vals[0], vals[1], temperature, color)
        self.win.destroy()


# ------------------------------------------------------------
# Главное окно меню
# ------------------------------------------------------------

class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Главное меню")
        self.geometry("300x250")
        self.resizable(False, False)
        
        # Заголовок
        title_label = tk.Label(
            self,
            text="Учет температуры",
            font=('Arial', 14, 'bold'),
            pady=20
        )
        title_label.pack()
        
        # Кнопки
        btn_frame = tk.Frame(self)
        btn_frame.pack(expand=True)
        
        buttons = [
            ("Работать", self.open_work, '#4CAF50'),
            ("Справка", self.open_help, '#2196F3'),
            ("Выход", self.quit_app, '#f44336')
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(
                btn_frame,
                text=text,
                command=command,
                bg=color,
                fg='white',
                font=('Arial', 11, 'bold'),
                width=15,
                height=1,
                relief=tk.RAISED,
                bd=2
            )
            btn.pack(pady=5)
        
        # Статус фото
        foto_path = os.path.join(os.path.dirname(__file__), "foto.jpg")
        foto_exists = os.path.exists(foto_path)
        pil_status = "PIL OK" if PIL_AVAILABLE else "PIL нет"
        foto_status = " foto.jpg" if foto_exists else " foto.jpg"
        
        status_text = f"{pil_status} | {foto_status}"
        status_label = tk.Label(
            self,
            text=status_text,
            font=('Arial', 8),
            fg='#4CAF50' if (PIL_AVAILABLE and foto_exists) else '#f44336'
        )
        status_label.pack(side=tk.BOTTOM, pady=5)
        
        self.work_window = None
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
    
    def open_work(self):
        self.withdraw()
        self.work_window = WorkWindow(self)
    
    def open_help(self):
        HelpWindow(self)
    
    def show_menu(self):
        self.deiconify()
        self.work_window = None
        self.focus_force()
    
    def quit_app(self):
        """Выход из программы без подтверждения"""
        self.quit()
        self.destroy()


def main():
    if os.name == 'nt':
        os.system('chcp 1251 > nul')
    
    app = MainMenu()
    app.mainloop()


if __name__ == "__main__":
    main()