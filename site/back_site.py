import requests
from bs4 import BeautifulSoup
import lxml
import json
import re
import os
from unidecode import unidecode

BAZOS = 'https://reality.bazos.sk/prenajmu/byt/'
NEHNUTENOSTI = 'https://www.nehnutelnosti.sk/vysledky/'


def search_nehnutelnosti_sk(size=2, min_price=1, max_price=2000, location="poprad"):

    if size <= 0 and size >= 4:
        return

    location = unidecode(location.lower())

    pattern = re.compile(fr"(?:okres\s+)?{re.escape(location)}", re.IGNORECASE)

    url = f'https://www.nehnutelnosti.sk/vysledky/{size}-izbove-byty/{location}/prenajom/'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/237.84.2.178 Safari/537.36'}

    file_name = 'nehnutelnosti_sk.json'
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as file:
            cached_data = json.load(file)
        nehnutelnosti_sk = []
        for item in cached_data:
            price_digits = re.findall(r"\d+", item.get("price", ""))
            if not price_digits:
                continue
            price_val = int("".join(price_digits).replace(" ", ""))
            if pattern.search(item.get("adress", "")) and (min_price <= price_val <= max_price) and (item.get("room") == size):
                nehnutelnosti_sk.append(item)
    else:
        nehnutelnosti_sk = []

    existing_sites = {item.get("link") for item in nehnutelnosti_sk}

    count_of_rooms = re.compile(fr"\b{re.escape(str(size))}[\s\-]?izb[a-z]*\b", re.IGNORECASE)

    page = 0
    while True:
        if page == 0:
            response = requests.get(url=url, headers=headers)
        else:
            response = requests.get(url=f'{url}?page={page}', headers=headers)

        if response.status_code != 200:
            print('Error')
            break
        
        print('Parsing page', page + 1)

        soup = BeautifulSoup(response.text, "lxml")

        get_ads = soup.find_all('div', class_='MuiBox-root mui-0')

        if not get_ads:
            break

        for got in get_ads:

            if response.status_code != 200:
                print('Error')
                continue                
                
            try:
                cena = got.find('p', class_='MuiTypography-root MuiTypography-h5 mui-7e5awq').text.strip()
                adress = got.find('p', class_='MuiTypography-root MuiTypography-body3 MuiTypography-noWrap mui-e9ka76').text.strip()
                link = got.find('a', href=True) 
                size_apart = got.find('p', class_="MuiTypography-root MuiTypography-body3 MuiTypography-noWrap mui-1w8a5rz").text.strip()
            except:
                continue

            print("Check link", link['href'])

            adress = unidecode(adress.lower())

            if pattern.search(adress) is None:
                continue
            
            size_apart_decode = unidecode(size_apart)

            if count_of_rooms.search(size_apart_decode) is None:
                continue

            price = re.findall(r"\d+", cena)
            if len(price) == 0:
                continue

            join_price = "".join(price).replace(" ", "")

            if (int(join_price) < min_price or int(join_price) > max_price) and (min_price != 0 and max_price != 0):
                continue

            if link['href'] in existing_sites:
                continue

            dict_byt = {
                'price': cena,
                'adress': adress,
                'link': link['href'],
                'room': size,
                'accept': True
            }

            existing_sites.add(link['href'])

            nehnutelnosti_sk.append(dict_byt)


        page += 1

    print('Count of ads', len(nehnutelnosti_sk))

    with open("nehnutelnosti_sk.json", "w", encoding="utf-8") as file:
        json.dump(nehnutelnosti_sk, file, ensure_ascii=False, indent=4)


def search_bazos_sk(size="2", min_price=400, max_price=600, location="040 11"):
    file_name = 'bazos_sk.json'
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as file:
            cached_data = json.load(file)
        bazos_sk = []
        for item in cached_data:
            price_digits = re.findall(r"\d+", item.get("price", ""))
            if not price_digits:
                continue
            price_val = int("".join(price_digits).replace(" ", ""))
            if location.replace(" ", "") == item.get("adress").replace(" ", "") and (min_price <= price_val <= max_price) and (item.get("room") == size):
                bazos_sk.append(item)
    else:
        bazos_sk = []

    location = unidecode(location.lower())

    existing_sites = {item.get("link") for item in bazos_sk}

    url = BAZOS
    parsing = True
    count = 0
    strank = 20

    count_of_rooms = re.compile(fr"\b{re.escape(str(size))}[\s\-]?izb[a-z]*\b", re.IGNORECASE)

    while True:
        if count == 0:
            response = requests.get(url=url)
        else:
            response = requests.get(url=f'{url}{strank}/')

        if response.status_code != 200:
            print('Error')
            break
        
        
        soup = BeautifulSoup(response.text, "lxml")
        
        main_content = soup.find('div', class_='maincontent')

        if not main_content:
            break

        all_inzeraty = main_content.find_all('div', class_='inzeraty inzeratyflex')

        if not all_inzeraty:
            break

        for inzerat in all_inzeraty:

            inzeratycena = inzerat.find('div', class_='inzeratycena').text.strip()
            inzeratylok = inzerat.find('div', class_='inzeratylok').find('br').next_sibling
            inzeratynadpis = inzerat.find('div', class_='inzeratynadpis').find('a')
            popis = inzerat.find('div', class_='inzeratynadpis').find('div', class_='popis').text.strip()

            link = inzeratynadpis.get('href')
            inzeratynadpis = f'https://reality.bazos.sk{link}'

            popis_decoded = unidecode(popis)

            if inzeratylok.replace(" ", "") != location.replace(" ", ""):
                continue

            if count_of_rooms.search(popis_decoded) is None:
                continue
            
            price = re.findall(r"\d+", inzeratycena)
            if len(price) == 0:
                continue

            join_price = "".join(price).replace(" ", "")

            if int(join_price) > max_price or int(join_price) < min_price:
                continue
            
            if inzeratynadpis in existing_sites:
                continue

            inzeraty_data = {
                'price': inzeratycena,
                'adress': inzeratylok,
                'link': inzeratynadpis,
                'room': size,
                'accept': True
            }

            bazos_sk.append(inzeraty_data)
            existing_sites.add(inzeratynadpis)
        print('Parsing page', strank)
        print('Count of ads', len(bazos_sk))
        strank += 20
        count += 1

        if not parsing:
            break

    with open("bazos_sk.json", "w", encoding="utf-8") as file:
        json.dump(bazos_sk, file, ensure_ascii=False, indent=4)

def reset_apartmens(apartment):
    apartment = apartment.lower().split("_")
    apartment[1] = "sk"
    apartment = "_".join(apartment)

    with open(f"{apartment}.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    if len(data) == 0:
        return False

    for item in data:
        item["accept"] = True

    with open(f"{apartment}.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    return True


def main():
    search_nehnutelnosti_sk()
    search_bazos_sk()

if __name__ == '__main__':
    main()