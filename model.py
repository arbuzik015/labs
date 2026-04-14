"""
Модель данных для учета температуры
Формат данных: ДД.ММ.ГГГГ,Место,Температура
"""

import datetime
import re
import logging
from typing import List, Optional

class InvalidDataError(Exception):
    """Ошибка валидации данных"""
    pass

class Temperature:
    """Запись о температуре"""
    def __init__(self, date_str: str, location: str, value: float):
        self.date_str = date_str
        self.location = location
        self.value = value

class TemperatureModel:
    """Модель для работы с данными температуры"""
    
    def __init__(self):
        self.records: List[Temperature] = []
        self.observers = []
    
    def add_observer(self, observer):
        """Добавить наблюдателя за изменениями модели"""
        self.observers.append(observer)
    
    def _notify_observers(self):
        """Уведомить наблюдателей об изменении данных"""
        for observer in self.observers:
            observer()
    
    def parse_line(self, line: str) -> Optional[Temperature]:
        """Парсинг строки в запись"""
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

    def load_from_file(self, filename: str) -> int:
        """Загрузка данных из файла"""
        self.records = []
        errors = 0
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
                    errors += 1
        logging.info("Загружено %d записей из %s (ошибок: %d)", len(self.records), filename, errors)
        self._notify_observers()
        return len(self.records)

    def save_to_file(self, filename: str) -> bool:
        """Сохранение данных в файл"""
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
        """Добавление записи"""
        self.records.append(Temperature(date_str, location, value))
        self._notify_observers()

    def delete_record(self, index: int):
        """Удаление записи по индексу"""
        if 0 <= index < len(self.records):
            del self.records[index]
            self._notify_observers()
    
    def get_records(self) -> List[Temperature]:
        """Получить все записи"""
        return self.records.copy()
    
    def get_record(self, index: int) -> Optional[Temperature]:
        """Получить запись по индексу"""
        if 0 <= index < len(self.records):
            return self.records[index]
        return None
    
    def count(self) -> int:
        """Количество записей"""
        return len(self.records)