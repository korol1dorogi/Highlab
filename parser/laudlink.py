import requests
from bs4 import BeautifulSoup

url = 'https://laudlink.ru/collection/all?page='
response = requests.get(url)
print(response.status_code)
soup = BeautifulSoup(response.text, 'html.parser')  # Исправлено здесь

# Ищем элемент с классом 'grid-list catalog-list'
grid_list = soup.find('div', class_='grid-list catalog-list')  # Уточнили поиск по div

if grid_list:
    print(grid_list)

