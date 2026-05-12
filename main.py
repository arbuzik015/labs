"""
Главный файл приложения для учета температуры
Запускает тесты и приложение
"""

import os
import sys
import logging
import unittest

from model import TemperatureModel
from view import MainView


def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("ЗАПУСК ВСЕХ ТЕСТОВ")
    print("=" * 60 + "\n")
    
    # Отключаем логирование
    logging.disable(logging.CRITICAL)
    
    # Загружаем тесты модели
    from test_model import TestTemperatureModel
    
    # Создаем suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestTemperatureModel))
    
    # Загружаем UI тесты
    from test_ui import TestMainView, TestWorkView, TestHelpView
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestMainView))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestWorkView))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestHelpView))
    
    # Запускаем
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    logging.disable(logging.NOTSET)
    
    print("\n" + "=" * 60)
    print(f"ИТОГ: {'✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if result.wasSuccessful() else '✗ ЕСТЬ ОШИБКИ'}")
    print("=" * 60 + "\n")
    
    return result.wasSuccessful()


def main():
    """Главная функция"""
    # Настройка кодировки для Windows
    if os.name == 'nt':
        os.system('chcp 1251 > nul')
    
    # Запуск тестов
    tests_passed = run_all_tests()
    
    if not tests_passed:
        response = input("\nТесты не пройдены. Запустить приложение? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    print("\n" + "=" * 40)
    print("ЗАПУСК ПРИЛОЖЕНИЯ")
    print("=" * 40 + "\n")
    
    # Создание и запуск приложения
    model = TemperatureModel()
    app = MainView(model)
    app.mainloop()


if __name__ == "__main__":
    main()