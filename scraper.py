import requests
from bs4 import BeautifulSoup
import time
import datetime
import pandas as pd

# search_words = input('What is the product?\n').strip().replace(' ', '%20')


# url = r'https://www.buscape.com.br/search?q=' + search_words
url = r'https://www.buscape.com.br/search?q=monitor%20dell'
print('Scraping this url:', url)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36", 
           "Accept-Encoding":"gzip, deflate", 
           "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "DNT":"1",
           "Connection":"close", "Upgrade-Insecure-Requests":"1"}

page = requests.get(url, headers=headers)

soup = BeautifulSoup(page.content, features="html")
products = soup.find_all('div', class_='ProductCard_ProductCard_Body__bnVUn')
products_href = soup.find_all('a', class_='ProductCard_ProductCard_Inner__gapsh')
product_dict = {}
for i, product, href in zip(range(0, len(products)), products, products_href):
    product_dict[i] = {'name': product.h2.text, 
                               'price': product.p.text,
                               'image': product.img['src'],
                               'href': href['href']}

print(pd.DataFrame(product_dict).T)



