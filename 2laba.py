import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

class Temperature:
    def __init__(self, date="", location="", value=0.0):
        self.date, self.location, self.value = date, location, value
    
    def __str__(self):
        return f"{self.date},{self.location},{self.value}"
    
    @classmethod
    def from_string(cls, s: str) -> Optional['Temperature']:
        try:
            d, l, v = [x.strip() for x in s.strip().split(',')]
            return cls(d, l, float(v)) if valid_date(d) else None
        except: return None

def valid_date(d: str) -> bool:
    if len(d)!=10 or d[2]!='.' or d[5]!='.': return False
    for i in range(10):
        if i not in (2,5) and not d[i].isdigit(): return False
    return 1<=int(d[0:2])<=31 and 1<=int(d[3:5])<=12

class FileManager:
    @staticmethod
    def load(fn: str) -> List[Temperature]:
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                return [m for line in f if (m:=Temperature.from_string(line))]
        except: return []
    
    @staticmethod
    def save(fn: str, data: List[Temperature]) -> bool:
        try:
            with open(fn, 'w', encoding='utf-8') as f:
                f.writelines(f"{m}\n" for m in data)
            return True
        except: return False

class App:
    def __init__(self, root, fn="temperatures.txt"):
        self.root, self.fn, self.data = root, fn, []
        self.root.title("Учет температуры")
        self.root.geometry("800x500")
        
        # Кнопки
        f = ttk.Frame(root, padding="5")
        f.pack(fill=tk.X)
        for t,c in [("Загрузить",self.load),("Сохранить",self.save),("Добавить",self.add_dlg),
                   ("Поиск",self.show_search),("Обновить",self.refresh)]:
            ttk.Button(f, text=t, command=c).pack(side=tk.LEFT, padx=5)
        
        # Поиск
        self.sf = ttk.Frame(root, padding="5")
        ttk.Label(self.sf, text="Место:").pack(side=tk.LEFT, padx=5)
        self.se = ttk.Entry(self.sf, width=30)
        self.se.pack(side=tk.LEFT, padx=5)
        self.se.bind('<Return>', lambda e: self.search())
        ttk.Button(self.sf, text="Найти", command=self.search).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.sf, text="✕", width=3, command=self.hide_search).pack(side=tk.LEFT)
        
        # Таблица
        tf = ttk.Frame(root, padding="5")
        tf.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tf, columns=('d','l','v'), show='headings', height=15)
        for col,text,w in [('d','Дата',120),('l','Место',200),('v','°C',120)]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor='center' if col!='l' else 'w')
        self.tree.grid(row=0, column=0, sticky='nsew')
        ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.tree.yview).grid(row=0, column=1, sticky='ns')
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)
        
        # Статус
        self.sv = tk.StringVar(value="Готов")
        ttk.Label(root, textvariable=self.sv, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)
        
        self.load()
    
    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for m in self.data:
            self.tree.insert('', tk.END, values=(m.date, m.location, f"{m.value:.1f}"))
        self.status(f"Всего: {len(self.data)}")
    
    def status(self, s): self.sv.set(s); self.root.update_idletasks()
    def load(self): self.data = FileManager.load(self.fn); self.refresh()
    def save(self): 
        if FileManager.save(self.fn, self.data): 
            messagebox.showinfo("", "Сохранено"); self.status("Сохранено")
    def add_dlg(self): AddDialog(self)
    def show_search(self): 
        self.sf.pack(fill=tk.X, pady=5, after=self.root.winfo_children()[0]); self.se.focus()
    def hide_search(self): self.sf.pack_forget(); self.refresh()
    
    def search(self):
        txt = self.se.get().strip().lower()
        if not txt: return messagebox.showwarning("", "Введите текст")
        for i in self.tree.get_children(): self.tree.delete(i)
        found = [m for m in self.data if txt in m.location.lower()]
        for m in found: self.tree.insert('', tk.END, values=(m.date, m.location, f"{m.value:.1f}"))
        self.status(f"Найдено: {len(found)}")
        if not found: messagebox.showinfo("", f"Ничего не найдено")
    
    def add(self, d, l, v):
        self.data.append(Temperature(d, l, v))
        self.refresh(); self.status(f"Добавлено: {d}")

class AddDialog:
    def __init__(self, app):
        self.app, self.win = app, tk.Toplevel(app.root)
        self.win.title("Добавить"); self.win.geometry("350x200")
        self.win.transient(app.root); self.win.grab_set()
        
        f = ttk.Frame(self.win, padding="20")
        f.pack(fill=tk.BOTH, expand=True)
        
        lbls = ["Дата (ДД.ММ.ГГГГ):", "Место:", "Температура:"]
        self.entries = []
        for i, txt in enumerate(lbls):
            ttk.Label(f, text=txt).grid(row=i, column=0, sticky=tk.W, pady=5)
            e = ttk.Entry(f, width=25)
            e.grid(row=i, column=1, pady=5, padx=10)
            self.entries.append(e)
        
        bf = ttk.Frame(f)
        bf.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(bf, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Отмена", command=self.win.destroy).pack(side=tk.LEFT, padx=5)
        self.win.bind('<Return>', lambda e: self.ok())
        
        # Центрирование
        self.win.update_idletasks()
        x = app.root.winfo_x() + (app.root.winfo_width()-self.win.winfo_width())//2
        y = app.root.winfo_y() + (app.root.winfo_height()-self.win.winfo_height())//2
        self.win.geometry(f'+{x}+{y}')
    
    def ok(self):
        vals = [e.get().strip() for e in self.entries]
        if not all(vals): return messagebox.showerror("", "Все поля обязательны")
        if not valid_date(vals[0]): return messagebox.showerror("", "Неверный формат даты")
        try: val = float(vals[2])
        except: return messagebox.showerror("", "Число!")
        self.app.add(vals[0], vals[1], val)
        self.win.destroy()

def main():
    if os.name == 'nt': os.system('chcp 1251 > nul')
    root = tk.Tk()
    app = App(root)
    def on_close():
        if messagebox.askokcancel("Выход", "Сохранить?"): app.save()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()