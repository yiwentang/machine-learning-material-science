# This file scraps web materials
# Originally intended to use PhantomJS, later found out this complicates the program and needs extra handling which Brower does not require
# Choosed Chrome instead

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ErrorInResponseException
from bs4 import BeautifulSoup
import pandas as pd
import re


#Globle variables: dataframe, driver

# Declare dataframe that stores all the data
df = pd.DataFrame()


# Login Session
login_url = input("Please enter the login url: ")
login_username = input("Please enter the login username: ")
login_password = input("Please enter the login password: ")
output_path = input("Please enter the output file path: ")

driver = webdriver.Chrome(executable_path="C:\\Users\\ytang\\chromedriver.exe")
driver.get(login_url)
try:
    element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'email')))
except TimeoutException as e:
    print("login: ", e)
else:
    username = driver.find_element_by_name('email')
    password = driver.find_element_by_name('password')
    username.send_keys(login_username)
    password.send_keys(login_password)
    driver.find_element_by_xpath("//input[@type='submit']").click()
    time.sleep(2)

    # Store the cookies in file
    LINE = "document.cookie = '{name}={value}; path={path}; domain={domain}';\n"
    with open('ulcookie.js', 'w') as file:
        for cookie in driver.get_cookies():
            file.write(LINE.format(**cookie))


# Load Cookies
def load_cookies(d, file_path):
    with open(file_path, 'r') as f:
        d.execute_script(f.read())
    return


# Functions to navigate through website to get links for products in certain category

def get_links(html):
    f = lambda x: "https://materials.ulprospector.com/" + x['href']
    try:
        href = html.find('table', {'id': 'RTable'}).find('tbody').findAll('a', {'href': re.compile('^Profile')})
    except AttributeError:
        l = []
    else:
        if href != []:
            l = [f(x) for x in href]
        else:
            l = []
    return l

# function that navigate the product list pages and harvest the links
def navigate_and_gather_links():
    html = BeautifulSoup(driver.page_source, 'lxml')
    l = get_links(html)
    while driver.find_element_by_id('NextNavAnchorUp').is_displayed():
        driver.find_element_by_id('NextNavAnchorUp').click()
        time.sleep(1)
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'RTable')))
        except TimeoutException as e:
            print('navigate_and_gather_links: ', e)
        else:
            html = BeautifulSoup(driver.page_source, 'lxml')
            l.extend(get_links(html))
    return l


# Get search for category and get the links for all products
def get_category(cat_name):
    all_product_links = []
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'q')))
    except TimeoutException as e:
        print('get_category (search): ', e)
    else:
        search = driver.find_element_by_name('q')
        search.clear()
        search.send_keys(cat_name)
        driver.find_element_by_id('b').click()
        time.sleep(2)
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'RTable')))
        except TimeoutException:
            print("get_category: ", "time out")
        except ErrorInResponseException:
            print("get_category: ", "response error")
        else:
            all_product_links = navigate_and_gather_links()
    return all_product_links


# Functions for parsing contents on product website
def parse_memo(bs, d):
    memos = bs.findAll('div', {'class': 'memo'})
    d['Description'] = memos[0].get_text(strip=True)
    if len(memos) > 1:
        f = lambda x: x.get_text(strip=True)
        note = [f(x) for x in memos[1:]]
        note = ", ".join(str(x) for x in note)
        d['Notes'] = note
    return d


def parse_table(rows, note, d):
    if rows != [] and note == []:
        delete_names = []
        for row in rows:
            tds = row.findAll('td')
            colname = tds[0].get_text(strip=True)
            if len(tds) == 1:
                d['Additional Information'] = colname
            else:
                f = lambda x: x.get_text(strip=True)
                if tds[1].table is not None:
                    value = [f(x) for x in tds[1].findAll('td')]
                    value = ", ".join(str(x) for x in value).strip(", ")
                else:
                    value = [f(x) for x in tds[1:]]
                    value = " ".join(str(x) for x in value)

                if 'proprow' in row.attrs['class']:
                    prop_name = colname
                else:
                    colname = prop_name + " (" + colname + ")"
                    value = value + " " + d[prop_name][0]

                    if prop_name not in delete_names:
                        delete_names.append(prop_name)

                d[colname] = [value]

        d = d.drop(delete_names, axis=1)
    return d


def parse_single_website(bs):
    d = pd.DataFrame()
    try:
        d = pd.DataFrame(index=[bs.find('div', {'class': 'crumbs'}).span.get_text()])
        d = parse_memo(bs, d)

        # parse first table that usually contains description
        tables = bs.findAll('table')
        rows0 = tables[0].findAll('tr', {'class': ['proprow', 'contextrow']})[1:]
        note0 = tables[0].findAll('tr', {'class': 'noterow'})
        d = parse_table(rows0, note0, d)

        for table in tables[1:]:
            rows = table.findAll('tr', {'class': ['proprow', 'contextrow']})
            note = table.findAll('tr', {'class': 'noterow'})
            d = parse_table(rows, note, d)
    except AttributeError as e:
        print("parse_single_website: ", e)
    return d


# Start Scrapping
categories = ['Polypropylene']
links = []
for cat in categories:
    # get the links for all product in designated category
    links.extend(get_category(cat))
print(len(links))
    # scrape data for each product
for link in links:
        print(link)
        try:
            driver.get(link)
        except ErrorInResponseException as e:
            print("response error: ", link)
        else:
            # driver.delete_all_cookie()
            # load_cookies(driver, 'ulcookie.js')
            try:
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'DSSEC')))
            except TimeoutException as e:
                print(link, ":", e)
            else:
                soup = BeautifulSoup(driver.page_source, 'lxml')
                this_df = parse_single_website(soup)
                this_df['link'] = [link]
                df = df.append(this_df)

driver.close()

# Clean up the dataframe
df['index'] = df.index
df = df.drop_duplicates(subset=['index']).drop(['index'], axis=1)

# Write into csv file
df.to_csv(output_path)

