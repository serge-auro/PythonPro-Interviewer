# https://easyoffer.ru/rating/python_developer
# Особенности: Для доступа к полному списку вопросов на сайте нужна подписка на ТГ каналы

# Импорт библиотек
from selenium import webdriver
from selenium.webdriver.common.by import By  # Для поиска элементов на сайте

import time
import csv


def read_table(browser):
    # Чтение таблицы вопросов с сайта
    data = []
    # Строки таблицы
    rows = browser.find_elements(By.TAG_NAME, "tr")  # ищем все тэги "tr"
    # print(rows)

    for row in rows:  # Разбор строк таблицы
        cols = row.find_elements(By.TAG_NAME, 'td')  # ищем все тэги "td"
        my_str = []
        for col in cols:  # Забираем текстовое содержимое ячеек
            my_str.append(col.text)

        data.append(my_str)

    # Первый (0) элемент списка пустой, удаляем его
    data = data[1:]
    # print(data)
    return data


def write_csv(data):
    # Выгрузка данных в csv файл
    with open("easyoffer.csv", 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Шанс', 'Вопрос', 'Тэг'])
        for i in range(0, len(data)):
            writer.writerows(data[i])


def parsing_easyoffer():
    #  Выгрузка данных с сайта easyoffer.ru
    browser = webdriver.Chrome()  # Объект браузера
    try:
        # Страница easyoffer:
        url = "https://easyoffer.ru/rating/python_developer?page="

        parsed_data = []

        # На сайте на момент выгрузки 11 страниц с вопросами
        for page in range(1, 12):
            # Формируем ссылку на конкретную страницу
            url_page = url+str(page).strip()
            # print(url_page)
            # Загрузка страницы
            browser.get(url_page)
            time.sleep(5)

            cur_page = read_table(browser)
            parsed_data.append(cur_page)
            # print(parsed_data)

        # Закрытие браузера
        browser.quit()

        # print(parsed_data)
        # Выгрузка в файл csv
        write_csv(parsed_data)

    except Exception as e:
        print(f"Ошибка. Исключение {type(e).__name__}")
        print(f"Сообщение исключения: {e}")


parsing_easyoffer()
