"""
Модель данных для учета температуры и качества воздуха
Формат данных: ДД.ММ.ГГГГ,Место,Температура,Качество_воздуха
Качество воздуха: Хорошее, Удовлетворительное, Плохое, Опасное
"""

import datetime
import re
import logging
from typing import List, Optional, Callable

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class InvalidDataError(Exception):
    """Ошибка валидации данных"""
    pass


class Temperature:
    """Запись о температуре и качестве воздуха"""
    def __init__(self, date_str: str, location: str, value: float, air_quality: str = "Хорошее"):
        self.date_str = date_str
        self.location = location
        self.value = value
        self.air_quality = air_quality
    
    def __repr__(self):
        return f"Temperature({self.date_str}, {self.location}, {self.value}, {self.air_quality})"


class TemperatureModel:
    """Модель для работы с данными температуры и качества воздуха"""
    
    # Допустимые значения качества воздуха
    VALID_AIR_QUALITY = ["Хорошее", "Удовлетворительное", "Плохое", "Опасное"]
    
    def __init__(self):
        self.records: List[Temperature] = []
        self.observers: List[Callable] = []
    
    def add_observer(self, observer: Callable):
        """Добавить наблюдателя за изменениями модели"""
        self.observers.append(observer)
    
    def _notify_observers(self):
        """Уведомить наблюдателей об изменении данных"""
        for observer in self.observers:
            observer()
    
    def validate_air_quality(self, air_quality: str) -> bool:
        """Проверка качества воздуха"""
        return air_quality in self.VALID_AIR_QUALITY
    
    def parse_line(self, line: str) -> Temperature:
        """
        Парсинг строки в запись
        Формат: ДД.ММ.ГГГГ,Место,Температура,Качество_воздуха
        """
        line = line.strip()
        if not line:
            raise InvalidDataError("Пустая строка")
        
        # Поддерживаем разделители , и ;
        if ';' in line:
            parts = [p.strip() for p in line.split(';')]
        else:
            # Разбиваем по запятой, но учитываем, что в числе может быть запятая
            raw_parts = line.split(',')
            
            # Если получилось больше 4 частей, возможно запятая в числе
            if len(raw_parts) > 4:
                # Первая часть - дата
                date_part = raw_parts[0].strip()
                # Предпоследняя часть - температура
                temp_part = raw_parts[-2].strip()
                # Последняя часть - качество воздуха
                quality_part = raw_parts[-1].strip()
                # Все остальное - место (объединяем через запятую)
                location_part = ','.join(raw_parts[1:-2]).strip()
                parts = [date_part, location_part, temp_part, quality_part]
            else:
                parts = [p.strip() for p in raw_parts]
        
        # Удаляем пустые части
        parts = [p for p in parts if p]
        
        # Поддерживаем старый формат (3 поля) и новый (4 поля)
        if len(parts) == 3:
            # Старый формат: дата, место, температура (качество по умолчанию "Хорошее")
            date_str, location, value_str = parts
            air_quality = "Хорошее"
        elif len(parts) == 4:
            # Новый формат: дата, место, температура, качество
            date_str, location, value_str, air_quality = parts
        else:
            raise InvalidDataError(
                f"Неверный формат: нужно 3 или 4 поля (дата, место, температура, [качество]), получено {len(parts)}"
            )
        
        # Проверка формата даты ДД.ММ.ГГГГ
        if not re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", date_str):
            raise InvalidDataError(f"Неверный формат даты: {date_str}. Ожидается ДД.ММ.ГГГГ")
        
        # Проверка корректности даты
        try:
            day, month, year = map(int, date_str.split('.'))
            datetime.datetime(year, month, day)
        except ValueError as e:
            raise InvalidDataError(f"Некорректная дата: {date_str} - {e}")
        
        # Проверка температуры (поддержка точки и запятой)
        try:
            # Заменяем запятую на точку
            value_str = value_str.replace(',', '.')
            # Удаляем возможные пробелы
            value_str = value_str.strip()
            value = float(value_str)
        except ValueError:
            raise InvalidDataError(f"Некорректное значение температуры: {value_str}")
        
        if not location:
            raise InvalidDataError("Местоположение не может быть пустым")
        
        # Проверка качества воздуха
        if not self.validate_air_quality(air_quality):
            raise InvalidDataError(
                f"Некорректное качество воздуха: {air_quality}. "
                f"Допустимые значения: {', '.join(self.VALID_AIR_QUALITY)}"
            )
        
        return Temperature(date_str, location, value, air_quality)
    
    def load_from_file(self, filename: str) -> int:
        """Загрузка данных из файла"""
        self.records = []
        errors = 0
        
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = self.parse_line(line)
                        self.records.append(record)
                    except InvalidDataError as e:
                        logging.error("[%s, строка %d] %s", filename, line_num, e)
                        errors += 1
        except FileNotFoundError:
            logging.warning("Файл %s не найден.", filename)
            raise
        
        logging.info("Загружено %d записей из %s (ошибок: %d)", len(self.records), filename, errors)
        self._notify_observers()
        return len(self.records)
    
    def save_to_file(self, filename: str) -> bool:
        """Сохранение данных в файл"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for r in self.records:
                    f.write(f"{r.date_str},{r.location},{r.value},{r.air_quality}\n")
            logging.info("Сохранено %d записей в %s", len(self.records), filename)
            self._notify_observers()
            return True
        except Exception as e:
            logging.error("Ошибка сохранения в %s: %s", filename, e)
            return False
    
    def add_record(self, date_str: str, location: str, value: float, air_quality: str = "Хорошее"):
        """Добавление записи"""
        # Базовая валидация
        if not date_str or not location:
            raise InvalidDataError("Дата и местоположение не могут быть пустыми")
        
        if not isinstance(value, (int, float)):
            raise InvalidDataError(f"Температура должна быть числом, получено: {value}")
        
        if not self.validate_air_quality(air_quality):
            raise InvalidDataError(
                f"Некорректное качество воздуха: {air_quality}. "
                f"Допустимые значения: {', '.join(self.VALID_AIR_QUALITY)}"
            )
        
        self.records.append(Temperature(date_str, location, value, air_quality))
        self._notify_observers()
    
    def add_from_csv(self, csv_data: str):
        """
        Добавление записи из CSV строки для команды ADD
        Формат: дата; место; температура; качество или дата,место,температура,качество
        """
        # Очищаем строку
        csv_data = csv_data.strip()
        
        # Определяем разделитель
        if ';' in csv_data:
            parts = [p.strip() for p in csv_data.split(';')]
        else:
            parts = [p.strip() for p in csv_data.split(',')]
        
        # Удаляем пустые части
        parts = [p for p in parts if p]
        
        # Поддерживаем 3 или 4 поля
        if len(parts) == 3:
            date_str, location, value_str = parts
            air_quality = "Хорошее"
        elif len(parts) == 4:
            date_str, location, value_str, air_quality = parts
        else:
            raise InvalidDataError(
                f"ADD: нужно 3 или 4 поля (дата, место, температура, [качество]), получено {len(parts)}: {parts}"
            )
        
        # Преобразуем температуру в число
        try:
            value = float(value_str.replace(',', '.'))
        except ValueError:
            raise InvalidDataError(f"ADD: некорректное значение температуры: {value_str}")
        
        # Валидация даты
        if not re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", date_str):
            raise InvalidDataError(f"ADD: неверный формат даты: {date_str}. Ожидается ДД.ММ.ГГГГ")
        
        try:
            day, month, year = map(int, date_str.split('.'))
            datetime.datetime(year, month, day)
        except ValueError as e:
            raise InvalidDataError(f"ADD: некорректная дата: {date_str} - {e}")
        
        if not location:
            raise InvalidDataError("ADD: местоположение не может быть пустым")
        
        if not self.validate_air_quality(air_quality):
            raise InvalidDataError(
                f"ADD: некорректное качество воздуха: {air_quality}. "
                f"Допустимые значения: {', '.join(self.VALID_AIR_QUALITY)}"
            )
        
        # Добавляем запись
        self.add_record(date_str, location, value, air_quality)
    
    def remove_by_condition(self, condition: str):
        """
        Удаление записей по условию для команды REM
        Поддерживаемые поля: date, location, value, quality/air_quality
        """
        condition = condition.strip()
        
        # Обновленный паттерн для поддержки разных форматов
        pattern = r'(date|date_str|location|place|value|temperature|temp|quality|air_quality|air)\s*(==|!=|<=|>=|<|>|contains)\s*(.+)'
        match = re.fullmatch(pattern, condition, re.IGNORECASE)
        
        if not match:
            raise InvalidDataError(
                "REM: неверное условие. Примеры:\n"
                "  value < 100\n"
                "  location == Москва\n"
                "  date > 15.03.2024\n"
                "  location contains пет\n"
                "  quality == Хорошее\n"
                "  air_quality != Плохое"
            )
        
        field_name, operator, raw_value = match.groups()
        field_name = field_name.lower()
        raw_value = raw_value.strip()
        
        # Убираем кавычки
        if (raw_value.startswith('"') and raw_value.endswith('"')) or \
           (raw_value.startswith("'") and raw_value.endswith("'")):
            raw_value = raw_value[1:-1]
        
        def check(record: Temperature) -> bool:
            # Поле value
            if field_name in ('value', 'temperature', 'temp'):
                left = record.value
                try:
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
            
            # Поле date
            elif field_name in ('date', 'date_str'):
                left = record.date_str
                right = raw_value
                
                if not re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", right):
                    raise InvalidDataError(f"REM: дата должна быть в формате ДД.ММ.ГГГГ, получено {right}")
                
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
                raise InvalidDataError(f"REM: неподдерживаемый оператор {operator} для date")
            
            # Поле location
            elif field_name in ('location', 'place'):
                left = record.location.lower()
                right = raw_value.lower()
                
                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "contains":
                    return right in left
                raise InvalidDataError(f"REM: для location поддерживаются только ==, !=, contains")
            
            # Поле quality (качество воздуха)
            elif field_name in ('quality', 'air_quality', 'air'):
                left = record.air_quality
                right = raw_value
                
                # Проверка допустимого значения
                valid_values = TemperatureModel.VALID_AIR_QUALITY
                if right not in valid_values:
                    raise InvalidDataError(
                        f"REM: недопустимое значение качества воздуха: {right}. "
                        f"Допустимые: {', '.join(valid_values)}"
                    )
                
                if operator == "==":
                    return left == right
                if operator == "!=":
                    return left != right
                if operator == "contains":
                    return right.lower() in left.lower()
                raise InvalidDataError(f"REM: для quality поддерживаются только ==, !=, contains")
            
            return False
        
        old_count = len(self.records)
        self.records = [r for r in self.records if not check(r)]
        removed = old_count - len(self.records)
        logging.info("REM: удалено %d записей по условию '%s'", removed, condition)
        self._notify_observers()
    
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
        errors = []
        
        try:
            with open(filename, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        self.execute_command(line)
                        logging.info("Команда выполнена (строка %d): %s", line_num, line)
                    except InvalidDataError as e:
                        error_msg = f"Строка {line_num}: {e}"
                        errors.append(error_msg)
                        logging.error("[Файл команд: %s, %s]", filename, error_msg)
        except FileNotFoundError:
            logging.warning("Файл команд %s не найден.", filename)
            raise
        
        self._notify_observers()
        return errors
    
    def get_records(self) -> List[Temperature]:
        """Получить копию всех записей"""
        return self.records.copy()
    
    def get_record(self, index: int) -> Optional[Temperature]:
        """Получить запись по индексу"""
        if 0 <= index < len(self.records):
            return self.records[index]
        return None
    
    def delete_record(self, index: int):
        """Удаление записи по индексу"""
        if 0 <= index < len(self.records):
            del self.records[index]
            self._notify_observers()
    
    def count(self) -> int:
        """Количество записей"""
        return len(self.records)
    
    def get_statistics_by_quality(self) -> dict:
        """Получить статистику по качеству воздуха"""
        stats = {quality: 0 for quality in self.VALID_AIR_QUALITY}
        for record in self.records:
            stats[record.air_quality] += 1
        return stats