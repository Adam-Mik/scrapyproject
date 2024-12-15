from bs4 import BeautifulSoup
import requests
from datetime import datetime
import csv
from unidecode import unidecode
import numpy as np
import re

DOMAIN = "https://www.otodom.pl/pl/"



# change Python Requests' User Agent (python-requests/2.26.0) to Chrome User Agent:
# headers = {
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
# }
headers={'User-Agent': 'Mozilla/5.0'}

def extract_numbers(input_string, prefer_float=False):
    pattern = r'[-+]?\d*\.\d+|\d+'
    numbers = re.findall(pattern, input_string)
    if prefer_float:
        numbers_list = [float(num) for num in numbers]
    else:
        numbers_list = [int(float(num)) if '.' not in num else float(num) for num in numbers]
    return numbers_list[0]


def check_if_must_be_nan(value):
    '''Check if is availeable data and if not set nan value'''
    if value == 'Zapytaj' or value == "Zapytaj o cenę":
        return np.nan
    else:
        return value


def set_link_location(voivodeship_value="podkarpackie", city_scrp="rzeszow", DOMAIN=DOMAIN):
    '''make link location to scrap'''
    return (f"{DOMAIN}wyniki/wynajem/mieszkanie/{voivodeship_value}/{city_scrp}/{city_scrp}/{city_scrp}?ownerTypeSingleSelect=ALL&distanceRadius=0&viewType=listing")


def connect_with_webcontent(link, headers=headers):
    response = requests.get(link, headers=headers)
    if response.status_code == 200:
        print("Correct response")  # Print the content of the response
    else:
        print(f'Request failed with status code: {response.status_code}')
    return BeautifulSoup(response.content, "html.parser")


def check_number_pages(link):
    button_page = connect_with_webcontent(link).find("div", class_="css-1i43dhb ef1jqb1")
    button_page_list = button_page.find_all("li")
    number_of_page = button_page_list[-2].text
    try:
        number_of_page = int(number_of_page)
        if number_of_page == 1:
            page = "page"
        else:
            page = "pages"
        print(f'Is availebale {number_of_page} {page}')
    except ValueError:
        print("Error: The value of number_of_page is not a valid integer.")
    return number_of_page


def scrap_main_content(soup):
    body_div_main = soup.find("div", class_="css-1i43dhb ef1jqb1")
    div_ul_li = body_div_main.find("div", attrs={'data-cy': 'search.listing.organic'})
    main_content = div_ul_li.find_all("article", class_="css-136g1q2 eeungyz0")
    return main_content


def scrap_data(soup, meter, result):
    meter = meter
    article = soup
    for count, element in enumerate(article):
        temp = ()
        href = element.find("a")['href']
        link = f"https://www.otodom.pl{href}"
        title = unidecode(element.find("p", attrs={'data-cy': 'listing-item-title'}).text)

        soup_internal_page = connect_with_webcontent(link)
        address = soup_internal_page.find("a", class_="css-1jjm9oe e42rcgs1").text
        address = unidecode(address)
        address_list = address.split(", ")
        if len(address_list) == 4:
            street_address = address_list[0]
            district_address = address_list[1]
            city = address_list[2]
            voivodeship = address_list[3]
        elif len(address_list) == 3:
            street_address = ""
            district_address = address_list[0]
            city = address_list[1]
            voivodeship = address_list[2]
        else:
            street_address = address
            district_address = ""
            city = ""
            voivodeship = ""

        try:
            price = extract_numbers(check_if_must_be_nan(soup_internal_page.find("strong", attrs={'aria-label': "Cena"}).text.replace(" ", "")))
        except:
            price = np.nan
        # try:
        number_of_room = np.nan
        surface = np.nan
        data_blocks = soup_internal_page.find_all("div", class_="css-1ftqasz")
        for i in data_blocks:
            i = unidecode(i.text)
            surface_pattern = r'^\d+(\.\d+)?m2$'
            number_of_room_pattern = r'^\d+ (pokoj|pokoje|pokoi)$'
            if_surface = re.search(surface_pattern, i)
            if_number_of_room = re.search(number_of_room_pattern, i)

            if if_surface:
                surface = extract_numbers(check_if_must_be_nan(i))
            elif if_number_of_room:
                number_of_room = extract_numbers(check_if_must_be_nan(i))

        try:
            offer_type = check_if_must_be_nan(element.find("div", attrs={'data-testid': "listing-item-owner-name"}).text)
        except:
            offer_type = np.nan
        try:
            rent = check_if_must_be_nan(soup_internal_page.find("div", class_="css-z3xj2a e1w5xgvx5").text)
            rent = extract_numbers(rent.replace(" ", ""))
        except:
            rent = np.nan

        time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        temp = (meter, title, street_address, district_address, city, voivodeship, link,
                price, number_of_room, surface, rent, offer_type, time_now)
        meter += 1
        result.append(temp)
    return (result, meter)



url = set_link_location("podkarpackie", 'rzeszow')
num_pages = check_number_pages(url) #liczba stron

result = []
for number in range(1, num_pages + 1):
    if number == 1:
        soup = connect_with_webcontent(url)  # Pobrana treść
        main_content = scrap_main_content(soup)  # Wyodrębniona zawartość strony
        res = scrap_data(main_content, 1, result)
    elif number > 1:
        url = f"{url}&page={number}"
        soup = connect_with_webcontent(url)  # Pobrana treść
        main_content = scrap_main_content(soup)  # Wyodrębniona zawartość strony
        res = scrap_data(main_content, res[1], result)

result = res[0]

fields = ["Nr", "Title", "Street", "District", "City", "Voivodeship", "Link", "Price [PLN]", "Number_of_room",
          "Surface [m2]", "Rent [PLN/month]", "Offer_type", "Time"]
with open(f'Dane_ofert_wynajem_Rzeszow_Otodom_{datetime.now().strftime("%Y_%m_%d")}.csv', 'w', newline='',
          encoding='utf-8') as f:
    csv_writer = csv.writer(f)
    csv_writer.writerow(fields)
    csv_writer.writerows(result)