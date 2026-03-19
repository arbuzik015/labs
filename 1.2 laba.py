import os

class Temperature:
    def __init__(self, date="", location="", value=0.0, color=""):
        self.date = date
        self.location = location
        self.value = value
        self.color = color  


def valid_date(date):
    if len(date) != 10:
        return False
    if date[2] != '.' or date[5] != '.':
        return False
    
    for i in range(10):
        if i == 2 or i == 5:
            continue
        if not date[i].isdigit():
            return False
    
    day = int(date[0:2])
    if day < 1 or day > 31:
        return False
    
    month = int(date[3:5])
    if month < 1 or month > 12:
        return False
    
    return True


def valid_color(color):
    
    allowed_colors = ['красный', 'синий', 'зеленый', 'желтый', 'оранжевый', 'фиолетовый', 'белый', 'черный']
    return color.lower() in allowed_colors

def input_measurement():
    m = Temperature()
    
    
    while True:
        m.date = input("Введите дату измерения (в формате ДД.ММ.ГГГГ): ")
        if valid_date(m.date):
            break
        print("Ошибка: неверный формат! Используйте ДД.ММ.ГГГГ.")
    
   
    m.location = input("Введите место: ")
    
    
    while True:
        try:
            m.value = float(input("Введите значение температуры: "))
            break
        except ValueError:
            print("Ошибка: введите число!")
    
    # Ввод цвета
    while True:
        m.color = input("Введите цвет (красный, синий, зеленый, желтый, оранжевый, фиолетовый, белый, черный): ")
        if valid_color(m.color):
            break
        print("Ошибка, недопустимый цвет")
    
    return m

def show(measurements):
    if not measurements:
        print("Список измерений пуст!")
        return
    
    print("\n=== Список всех измерений температуры ===")
    print(f"{'Дата':<12} | {'Место':<15} | {'Температура':<10} | {'Цвет':<10}")
    print("-" * 55)
    
    for m in measurements:
        print(f"{m.date:<12} | {m.location:<15} | {m.value:>8.1f}°C   | {m.color:<10}")

def search_place(measurements, place):
    found = False
    print(f"\n=== Результаты поиска по месту '{place}' ===")
    
    for m in measurements:
        if m.location.lower() == place.lower():  # поиск без учета регистра
            print(f"Дата: {m.date}, Температура: {m.value:.1f}°C, Цвет: {m.color}")
            found = True
    
    if not found:
        print(f"Измерений для места '{place}' не найдено.")

def main():
    if os.name == 'nt':
        os.system('chcp 1251 > nul')
    
    measurements = []
    print("=== Программа для измерений температуры ===")
    
    while True:
        print("\nМеню:")
        print("1. Добавить новое измерение")
        print("2. Показать все измерения")
        print("3. Поиск по месту измерения")
        print("4. Выход")
        
        try:
            choice = int(input("Выберите действие (1-4): "))
        except ValueError:
            print("Ошибка: введите число!")
            continue
        
        if choice == 1:
            print("\n--- Добавление нового измерения ---")
            measurements.append(input_measurement())
            print("Измерение добавлено!")
        
        elif choice == 2:
            show(measurements)
        
        elif choice == 3:
            if not measurements:
                print("Добавьте хотя бы одно измерение!")
                continue
            place = input("Введите место для поиска: ")
            search_place(measurements, place)
        
        elif choice == 4:
            print("Программа завершена.")
            break
        
        else:
            print("Неверный выбор! Выберите от 1 до 4.")

if __name__ == "__main__":
    main()