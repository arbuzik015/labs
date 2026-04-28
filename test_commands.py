"""
Модульные тесты для обработчика команд
"""

import unittest
import tempfile
import os
from model import TemperatureModel, InvalidDataError, Temperature


class TestCommands(unittest.TestCase):
    """Тесты команд ADD, REM, SAVE"""
    
    def setUp(self):
        self.model = TemperatureModel()
    
    def test_add_from_csv_valid(self):
        """Тест: ADD с корректными данными"""
        self.model.add_from_csv("20.03.2024;Москва;10.5")
        self.assertEqual(self.model.count(), 1)
        record = self.model.get_record(0)
        self.assertEqual(record.location, "Москва")
        self.assertEqual(record.value, 10.5)
    
    def test_add_from_csv_with_comma(self):
        """Тест: ADD с запятой вместо точки с запятой"""
        self.model.add_from_csv("20.03.2024,Москва,10.5")
        self.assertEqual(self.model.count(), 1)
    
    def test_add_from_csv_invalid(self):
        """Тест: ADD с некорректными данными"""
        with self.assertRaises(InvalidDataError):
            self.model.add_from_csv("20.03.2024;Москва")
    
    def test_remove_by_value_less(self):
        """Тест: REM value < X"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("16.03.2024", "Киев", 10.0)
        self.model.add_record("17.03.2024", "Минск", -2.0)
        
        self.model.remove_by_condition("value < 0")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).location, "Киев")
    
    def test_remove_by_value_greater(self):
        """Тест: REM value > X"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("16.03.2024", "Киев", 10.0)
        
        self.model.remove_by_condition("value > 0")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).location, "Москва")
    
    def test_remove_by_value_equal(self):
        """Тест: REM value == X"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("16.03.2024", "Киев", 10.0)
        
        self.model.remove_by_condition("value == 10.0")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).location, "Москва")
    
    def test_remove_by_location_equal(self):
        """Тест: REM location == X"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("16.03.2024", "Киев", 10.0)
        
        self.model.remove_by_condition("location == Москва")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).location, "Киев")
    
    def test_remove_by_location_contains(self):
        """Тест: REM location contains X"""
        self.model.add_record("15.03.2024", "Санкт-Петербург", -5.5)
        self.model.add_record("16.03.2024", "Киев", 10.0)
        
        self.model.remove_by_condition("location contains петер")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).location, "Киев")
    
    def test_remove_by_date_before(self):
        """Тест: REM date < X"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("20.03.2024", "Киев", 10.0)
        
        self.model.remove_by_condition("date < 18.03.2024")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).date_str, "20.03.2024")
    
    def test_remove_by_date_after(self):
        """Тест: REM date > X"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.add_record("20.03.2024", "Киев", 10.0)
        
        self.model.remove_by_condition("date > 18.03.2024")
        self.assertEqual(self.model.count(), 1)
        self.assertEqual(self.model.get_record(0).date_str, "15.03.2024")
    
    def test_remove_no_match(self):
        """Тест: REM без совпадений"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.remove_by_condition("value > 100")
        self.assertEqual(self.model.count(), 1)
    
    def test_execute_command_add(self):
        """Тест: execute_command ADD"""
        self.model.execute_command("ADD 20.03.2024;Москва;10.5")
        self.assertEqual(self.model.count(), 1)
    
    def test_execute_command_rem(self):
        """Тест: execute_command REM"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        self.model.execute_command("REM value < 0")
        self.assertEqual(self.model.count(), 0)
    
    def test_execute_command_save(self):
        """Тест: execute_command SAVE"""
        self.model.add_record("15.03.2024", "Москва", -5.5)
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            filename = f.name
        
        try:
            self.model.execute_command(f"SAVE {filename}")
            self.assertTrue(os.path.exists(filename))
            
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("15.03.2024,Москва,-5.5", content)
        finally:
            os.unlink(filename)
    
    def test_execute_command_invalid(self):
        """Тест: execute_command с неизвестной командой"""
        with self.assertRaises(InvalidDataError):
            self.model.execute_command("UNKNOWN arg")
    
    def test_apply_commands_file(self):
        """Тест: apply_commands_file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("# Комментарий\n")
            f.write("ADD 20.03.2024;Москва;10.5\n")
            f.write("ADD 21.03.2024;Киев;-2.0\n")
            f.write("REM value < 0\n")
            commands_file = f.name
        
        try:
            errors = self.model.apply_commands_file(commands_file)
            self.assertEqual(len(errors), 0)
            self.assertEqual(self.model.count(), 1)
            self.assertEqual(self.model.get_record(0).location, "Москва")
        finally:
            os.unlink(commands_file)
    
    def test_apply_commands_file_with_errors(self):
        """Тест: apply_commands_file с ошибками"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("ADD 20.03.2024;Москва;10.5\n")
            f.write("INVALID command\n")
            f.write("ADD 21.03.2024;Киев;-2.0\n")
            commands_file = f.name
        
        try:
            errors = self.model.apply_commands_file(commands_file)
            self.assertEqual(len(errors), 1)
            self.assertEqual(self.model.count(), 2)
            self.assertIn("INVALID", errors[0])
        finally:
            os.unlink(commands_file)
    
    def test_apply_commands_file_skip_comments(self):
        """Тест: пропуск комментариев и пустых строк"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("# Это комментарий\n")
            f.write("\n")
            f.write("ADD 20.03.2024;Москва;10.5\n")
            f.write("  # Еще комментарий\n")
            f.write("ADD 21.03.2024;Киев;-2.0\n")
            commands_file = f.name
        
        try:
            errors = self.model.apply_commands_file(commands_file)
            self.assertEqual(len(errors), 0)
            self.assertEqual(self.model.count(), 2)
        finally:
            os.unlink(commands_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)