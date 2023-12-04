
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
import time
import os
import random
from google.oauth2.service_account import Credentials
from google.cloud import bigquery
import json
import google.cloud.logging
import logging
import sys

from datetime import datetime

from selenium.webdriver.common.action_chains import ActionChains
import math

from bs4 import BeautifulSoup

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from google.cloud.bigquery import Client, LoadJobConfig

def get_logger() -> logging.Logger:
    logging_level = os.environ.get("LOGGING", 20)
    logger = logging.getLogger(__name__)
    logging.basicConfig(stream=sys.stdout, level=logging.getLevelName(int(logging_level)), format="{%(levelname)s} in %(name)s: %(message)s")

    cloud_logging = google.cloud.logging.Client()
    cloud_logging.setup_logging()

    return logger


def main():
    client = bigquery.Client(project="input-kpis-telco-c24")

    logger = get_logger()

    # "" (egal), 500, 2000, 4000, 5000, 8000, 10000, 15000, 30000, 50000, 999999 (unlimited)
    internet_volume_min = ""

    # when empty network is not selected
    network_telekom = "network[]=1&"
    network_vodafone = "network[]=2&"
    network_telefonica = "network[]=4&"

    # "" (egal), 50, 100, 200, 300, 400, phoneFlat
    telephony_package = ""

    # any, true, false
    number_porting = "any"

    # "" (all), private, company, freelance, youngPeople
    customer_group = ""

    # "" (all), 21000, 50000, 100000, 300000
    max_download_speed_kb = ""

    # "" (egal), 1, 24
    max_contract_runtime = ""

    # "" (egal), 10, 15, 20, 30
    max_costs_month = ""

    # "" (egal), vertrag, prepaid
    type = ""

    url = "https://www.verivox.de/handytarifevergleich/?mergeDefaults=false&productType=&sortBy=monthlyEffectiveCost&sortDirection=up&mobiletariffCalculatorForm=true&enableStackedOffers=&stackedOffers=&providerId=&resultLayout=&partnerId=1&t_mf1452=true&" \
    + network_telekom + network_vodafone + network_telefonica \
    + "telephonyPackage=" +  telephony_package \
    + "&internetVolumeMin=" + internet_volume_min \
    + "&numberPorting=" + number_porting \
    + "&customerGroup=" + customer_group \
    +"&maxDownloadSpeedKb=" + max_download_speed_kb \
    + "&maxContractRuntime=" + max_contract_runtime \
    + "&maxCostsMonth=" + max_costs_month \
    + "&type=" + type


    firefox_options = Options()
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/100.0'
    firefox_options.add_argument(f'user-agent={user_agent}')
    firefox_options.add_argument("--width=1920")
    firefox_options.add_argument("--height=1080")
    firefox_options.add_argument("--headless")

    # Provide the path to the geckodriver executable
    gecko_path = "/usr/local/bin/geckodriver"
    driver = webdriver.Firefox(service=Service(gecko_path), options=firefox_options)

    driver.get(url)
    time.sleep(4 + random.randint(0, 7))

    cookie_consent_verivox = '//*[@id="uc-btn-accept-banner"]'
    time.sleep(2 + random.randint(0, 7))


    driver.find_element(By.XPATH, cookie_consent_verivox).click()
    time.sleep(8 + random.randint(0, 4))

    numtariffs = driver.find_element(By.CSS_SELECTOR, ".cms-cl_result-header__meta")

    num = int(numtariffs.text.split()[0])
    num_click = math.ceil(num / 10) - 1
                
    more_results_css_selector = ".cms_continiuer-elem"

    # load all offers in browser
    for counter in range(num_click):
            driver.find_element(By.CSS_SELECTOR, more_results_css_selector).click()
            time.sleep(3 + random.randint(1, 5))
                            

    # load data with bs4
    page_source = driver.page_source
    tariff_providers = []
    net_providers = []
    soup = BeautifulSoup(page_source, "html.parser")


    driver.quit()

    logger.info("Website crawling successful!")

    # start with transformation
    all_offers = soup.find_all("div", class_="cms-cl_tariff-row")
    tariff_names = []
    tariff_providers = []
    net_providers = []
    contract_duration_months = []
    contract_duration_days = []
    notice_period_months = []
    notice_period_days = []
    offer_type = []
    actual_monthly_price = []
    offered_monthly_price = []
    monthly_price_benefits = []
    short_additional_info = []
    long_additional_info = []
    amount_gb = []
    download_speed = []
    cost_per_mb = []
    cost_per_sms = []
    cost_per_min = []
    amount_min = []
    cashback = []
    number_porting_bonus = []
    verivox_bonus = []
    dates = []

    today = datetime.today().date()

    for offer in all_offers:
        # name of the tariff
        title = offer.find("div", class_="cms-cl_tariff-row__title").text

        # tariff provider
        image_tag = offer.find("div", class_="cms-cl_tariff-row__logo").find("img")
        provider = image_tag["title"].title()

        # net provider
        network_tag = offer.find("div", class_="cms-cl_tariff-row__compact-item-network").find("div", class_="cms_vic-color")
        net_provider = network_tag["data-vic"].title()

        # contract duration & notice period
        rows = offer.find_all('tr', class_='cms-cl_data-table__body-row')
        for line in rows:
            if "Mindestvertragslaufzeit" in line.text:
                if "monat" in line.text.lower():
                    duration_months = float(line.text.split()[1])
                    duration_days = duration_months * 30.417
                if "woche" in line.text.lower():
                    duration_days = float(line.text.split()[1]) * 7
                    duration_months = duration_days / 30.417
                if "tag" in line.text.lower():
                    duration_days = float(line.text.split()[1])
                    duration_months = duration_days / 30.417
            if "Kündigungsfrist" in line.text:
                notice_period = float(line.text.split()[1])
                if "monat" in line.text.lower():
                    notice_months = float(line.text.split()[1])
                    notice_days = notice_months * 31
                if "woche" in line.text.lower():
                    notice_days = float(line.text.split()[1]) * 7
                    notice_months = notice_days / 31
                if "tag" in line.text.lower():
                    notice_days = float(line.text.split()[1])
                    notice_months = notice_days / 31


        # type of contract
        list_contract = offer.find_all("div", class_="cms-cl_tariff-row__contractinfo")
        for line in list_contract:
            if "Vertrag" in line.text:
                contract = "Vertrag"
            if "Prepaid" in line.text:
                contract = "Prepaid"


        # all additional information short 
        additional_short_tag = offer.find_all("div", class_="cms-cl_tooltip__caption")
        additional_info_short = '\n'.join([div.text.strip() for div in additional_short_tag])


        # all additional information long
        additional_long_tag = offer.find("div", class_="cms-cl_tariff-row__details")
        list_info = additional_long_tag.find_all("div", class_="cms-cl_tooltip__body")
        additional_info_long = '\n\n'.join([div.text.strip() for div in list_info])

        # amount of highspeed data & cost per mb
        list_highspeed_amount = offer.find("div", class_="cms-cl_tariff-row__compact-item-data")
        highspeed_amount = 0
        cost_mb = 0.0
        for line in list_highspeed_amount:
            if "GB" in line.text.upper():
                match = re.search(r'[\d,]+', line)
                if match:
                    number = match.group()
                    if "/" in line.text:
                        cost_mb = float(number.replace(",", ".")) / 1000
                    else:
                        highspeed_amount = float(number.replace(",", "."))
            if "MB" in line.text.upper():
                match = re.search(r'[\d,]+', line)
                if match:
                    number = match.group()
                    if "/" in line.text:
                        cost_mb = float(number.replace(",", "."))
                    else:
                        highspeed_amount = float(number.replace(",", ".")) / 1000
            if "unbegrenzt" in line.text:
                highspeed_amount = 99999

                
        # max download speed
        list_highspeed_speed = offer.find("div", class_="cms-cl_tariff-row__compact-item-speed")
        highspeed_speed = 0.0
        for line in list_highspeed_speed:
            if "MB" in line.text.upper():
                match = re.search(r'[\d,]+', line)
                if match:
                    number = match.group()
                    highspeed_speed = float(number.replace(",", "."))
            if "KB" in line.text.upper():
                match = re.search(r'[\d,]+', line)
                if match:
                    number = match.group()
                    highspeed_speed = float(number.replace(",", ".")) / 1000
            

        # cost per sms & cost per min in a call & free min / free sms
        feature_div = offer.find("div", class_="cms-cl_features__item", attrs={'data-feature-type': 'phone'})
        caption_div = feature_div.find("div", class_="cms-cl_features__caption")
        parts = caption_div.decode_contents().split('<br/>')
        cost_sms = 0.0
        cost_min = 0.0
        free_min = 0.0
        if len(parts) > 1:
            num_1 = re.search(r'\d+', parts[0])
            num_2 = re.search(r'\d+', parts[1])
            if num_2 is not None:
                if "/" in parts[1]:
                    cost_sms = float(num_2.group().replace(",", "."))
                    cost_min = float(num_2.group().replace(",", "."))
            if num_1 is not None:
                if "/" in parts[0]:
                    cost_min = float(num_1.group().replace(",", "."))
                else:
                    free_min = float(num_1.group().replace(",", "."))
        else:
            num_1 = re.search(r'\d+', parts[0])
            if num_1 is not None:
                if "/" in parts[0]:
                    if "MIN" in parts[0].upper():
                        cost_min = float(num_1.group().replace(",", "."))
                    if "SMS" in parts[0].upper():
                        cost_sms = float(num_1.group().replace(",", "."))
                else:
                    if "MIN" in parts[0].upper():
                        free_min = float(num_1.group().replace(",", "."))

        # verivox cashback
        cashback_amount = 0.0
        lines = additional_info_short.split('\n')
        for line in lines:
            if "Cashback" in line:
                match = re.search(r'[\d,]+', line)
                if match:
                    number = match.group()
                    cashback_amount = float(number.replace(",", "."))


        # number porting cash bonus
        number_porting_amount = 0.0
        for line in lines:
            if "Rufnummernmitnahmebonus" in line:
                match = re.search(r'[\d,]+', line)
                if match:
                    number = match.group()
                    number_porting_amount = float(number.replace(",", "."))

        # verivox one time bonus 
        verivox_bonus_amount = 0.0
        for line in lines:
            if "Aktion:" in line:
                if "€" in line:
                    match = re.search(r'[\d,]+', line)
                    if match:
                        number = match.group()
                        verivox_bonus_amount = float(number.replace(",", "."))

        # base price per month
        price_tag = offer.find("div", class_="cms-cl_price-details__item cms-cl_price-details__item--last")
        list_base_price = price_tag.find_all("div")
        base_price = 0.0
        for line in list_base_price:
            if "€" in line.text:
                base_price = float(line.text.replace(",", ".").replace(" ", "").replace("€", ""))

        # offered price per month on website
        offered_price_website = float(offer.find("div", class_="cms-cl_price-details-table__label-price").text.replace("€", "").replace(",", ".").replace(" ", "").replace("\n", ""))

        # price per month including benefits
        offered_price_benefits = base_price - (cashback_amount / 24) - (verivox_bonus_amount / 24) - (number_porting_amount / 24)

        # add to lists
        dates.append(str(today))
        tariff_names.append(title)
        tariff_providers.append(provider)
        net_providers.append(net_provider)

        contract_duration_months.append(duration_months)
        contract_duration_days.append(duration_days)
        notice_period_months.append(notice_months)
        notice_period_days.append(notice_days)
        offer_type.append(contract)

        actual_monthly_price.append(base_price)
        offered_monthly_price.append(offered_price_website)
        monthly_price_benefits.append(offered_price_benefits)

        short_additional_info.append(additional_info_short)
        long_additional_info.append(additional_info_long)

        amount_gb.append(highspeed_amount)
        download_speed.append(highspeed_speed)

        cost_per_mb.append(cost_mb)
        cost_per_sms.append(cost_sms)
        cost_per_min.append(cost_min)
        amount_min.append(free_min)

        cashback.append(cashback_amount)
        number_porting_bonus.append(number_porting_amount)
        verivox_bonus.append(verivox_bonus_amount)

    data = {
        "Tariff_Name" : tariff_names,
        "Tarrif_Provider" : tariff_providers,
        "Net_Provider" : net_providers,
        "Datavolume_in_GB" : amount_gb,
        "Downloadspeed_in_MBits" : download_speed,
        "Contract_Type" : offer_type,
        "Contract_Duration_in_Months" : contract_duration_months,
        "Contract_Duration_in_Days" : contract_duration_days,
        "Notice_Period_in_Months" : notice_period_months,
        "Notice_Period_in_Days" : notice_period_days,
        "Monthly_Base_Price" : actual_monthly_price,
        "Monthly_Price_Website": offered_monthly_price,
        "Monthly_Price_All_Benefits" : monthly_price_benefits,
        "Cashback_Amount" : cashback,
        "Number_Porting_Bonus" : number_porting_bonus,
        "Verixvox_Bonus" : verivox_bonus,
        "Cost_per_SMS_in_Euro" : cost_per_sms,
        "Cost_per_MIN_in_Euro" : cost_per_min,
        "Cost_per_MB_in_Euro" : cost_per_mb,
        "Amount_of_MIN_Free" : amount_min,
        "Additional_Info_Header" : short_additional_info,
        "Additional_Info_Detailed" : long_additional_info,
        "Date_Crawled" : dates
    }


    df = pd.DataFrame(data)

    logger.info("Datatransformation successful!")
    
    try:
       job = client.load_table_from_dataframe(df, 'input-kpis-telco-c24.telco_kpis.mobilfunk_verivox_updated', job_config=LoadJobConfig())
       logger.info(f"BigQuery upload successful!")
    except Exception as e:
        logger.critical(repr(e))
        logger.critical("Upload to BigQuery failed")
    return ("ok", 200)
    
if __name__ == "__main__":
    main()