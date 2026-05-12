"""
Модульные тесты для модели данных
"""

import unittest
import tempfile
import os
from model import TemperatureModel, InvalidDataError, Temperature

class TestTemperatureModel(unittest.TestCase):
    """Тесты модели данных"""
    
    def setUp(self):
        self.model = TemperatureModel()

    def test_parse_valid_line(self):
        """Тест: Парсинг корректной строки"""
        record = self.model.parse_line("15.03.2024,Москва,-5.5")
        self.assertEqual(record.date_str, "15.03.2024")
        self.assertEqual(record.location, "Москва")
        self.assertEqual(record.value, -5.5)

    def test_parse_invalid_date_format(self):
        """Тест: Неверный формат даты"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("2024.03.15,Москва,-5.5")

    def test_parse_invalid_date_value(self):
        """Тест: Несуществующая дата"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("32.13.2024,Москва,-5.5")

    def test_parse_missing_fields(self):
        """Тест: Не хватает полей"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("15.03.2024,Москва")

    def test_parse_invalid_number(self):
        """Тест: Неверный формат числа"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("15.03.2024,Москва,не_число")

    def test_parse_empty_string(self):
        """Тест: Пустая строка"""
        with self.assertRaises(InvalidDataError):
            self.model.parse_line("")

    def test_parse_with_comma_in_number(self):
        """Тест: Число с запятой"""
        record = self.model.parse_line("15.03.2024,Москва,-5,5")
        self.assertEqual(record.value, -5.5)

    def test_add_record(self):
        """Тест: Добавление записи"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).location, "Москва")

    def test_delete_record(self):
        """Тест: Удаление записи"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.delete_record(0)
        self.assertEqual(self.model.count(), 0)

    def test_delete_invalid_index(self):
        """Тест: Удаление с неверным индексом"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.delete_record(999)
        self.assertEqual(self.model.count(), 1)

    def test_get_records_copy(self):
        """Тест: Получение копии записей"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        records = self.model.get_records()
        records.append(Temperature("16.03.2024", "Киев", 10))
        self.assertEqual(self.model.count(), 1)

    def test_save_and_load(self):
        """Тест: Сохранение и загрузка"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("16.03.2024", "Киев", 10.0)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', 
                                        delete=False, encoding='utf-8') as f:
            filename = f.name
        
        try:
            self.assertTrue(self.model.save_to_file(filename))
            
            new_model = TemperatureModel()
            count = new_model.load_from_file(filename)
            
            self.assertEqual(count, 2)
            self.assertEqual(new_model.count(), 2)
            self.assertEqual(new_model.get_record(0).location, "Москва")
            self.assertEqual(new_model.get_record(1).value, 10.0)
        finally:
            os.unlink(filename)

    def test_observer_pattern(self):
        """Тест: Паттерн Observer"""
        updates = []
        self.model.add_observer(lambda: updates.append(1))
        
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.assertEqual(len(updates), 1)
        
        self.model.delete_record(0)
        self.assertEqual(len(updates), 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)