from time import sleep, strftime
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from random import randint
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import smtplib
from email.mime.multipart import MIMEMultipart

departure = 'YIA'
destination = 'KTM'

chromedriver_path = '/home/mikdelac/Downloads/chromedriver'  # Change this to your own chromedriver path!

print("Chromedriver path is ", chromedriver_path)
ser = Service(chromedriver_path)
op = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=ser, options=op)

# https://www.kayak.com/flights/YIA-KTM/2022-09-21-flexible-3days?sort=bestflight_a
kayak = 'https://www.kayak.com/flights/{}-{}/2022-09-06/2022-09-30?sort=bestflight_a'.format(departure, destination)
driver.get(kayak)

sleep(2)

# Load more results to maximize the scraping

def load_more():
    try:
        more_results = '//a[@class = "moreButton"]'
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, more_results))).click()
        #driver.find_element_by_xpath(more_results).click()
        print('sleeping.....')
        #sleep(randint(25,35))
    except:
        pass


def page_scrape():
    """This function takes care of the scraping part"""

    xp_sections = '//*[contains(@class, "section") and contains(@class, "duration")]'
    sections = driver.find_elements(By.XPATH, xp_sections)
    sections_list = [value.text for value in sections]
    section_a_list = sections_list  # This is to separate the two flights
    #section_a_list = sections_list[::2]  # This is to separate the two flights
    section_b_list = sections_list[1::2]  # This is to separate the two flights

    # if you run into a reCaptcha, you might want to do something about it
    # you will know there's a problem if the lists above are empty
    # this if statement lets you exit the bot or do something else
    # you can add a sleep here, to let you solve the captcha and continue scraping
    # i'm using a SystemExit because i want to test everything from the start
    if section_a_list == []:
        raise SystemExit

    # I'll use the letter A for the outbound flight and B for the inbound
    a_duration = []
    a_section_names = []
    for n in section_a_list:
        # Separate the time from the cities
        a_section_names.append(''.join(n.split()[2:5]))
        a_duration.append(''.join(n.split()[0:2]))
    b_duration = []
    b_section_names = []
    for n in section_b_list:
        # Separate the time from the cities
        b_section_names.append(''.join(n.split()[2:5]))
        b_duration.append(''.join(n.split()[0:2]))

    xp_dates = '//div[contains(@class, "section") and contains(@class, "date")]'
    dates = driver.find_elements(By.XPATH, xp_dates)
    dates_list = [value.text for value in dates]
    a_date_list = dates_list
    b_date_list = dates_list[1::2]
    # Separating the weekday from the day
    a_day = [value.split()[0] for value in a_date_list]
    a_weekday = [value.split()[1] for value in a_date_list]
    b_day = [value.split()[0] for value in b_date_list]
    b_weekday = [value.split()[1] for value in b_date_list]

    # getting the prices
    xp_prices = '//span[contains(@class, "price") and contains(@class, "option-text")]'
    prices = driver.find_elements(By.XPATH, xp_prices)
    prices_list = [price.text.replace('$', '').replace(',', '') for price in prices if price.text != '']

    prices_list = list(map(int, prices_list))

    # the stops are a big list with one leg on the even index and second leg on odd index
    xp_stops = '//div[contains(@class, "section") and contains(@class, "stops")]/div[1]'
    stops = driver.find_elements(By.XPATH, xp_stops)
    stops_list = [stop.text[0].replace('n', '0') for stop in stops]
    a_stop_list = stops_list
    b_stop_list = stops_list[1::2]

    xp_stops_cities = '//div[contains(@class, "section") and contains(@class, "stops")]/div[2]'
    stops_cities = driver.find_elements(By.XPATH, xp_stops_cities)
    stops_cities_list = [stop.text for stop in stops_cities]
    a_stop_name_list = stops_cities_list
    b_stop_name_list = stops_cities_list[1::2]

    # this part gets me the airline company and the departure and arrival times, for both legs
    xp_schedule = '//div[contains(@class, "section") and contains(@class, "times")]'
    schedules = driver.find_elements(By.XPATH, xp_schedule)
    hours_list = []
    carrier_list = []
    for schedule in schedules:
        hours_list.append(schedule.text.split('\n')[0])
        carrier_list.append(schedule.text.split('\n')[1])
    # split the hours and carriers, between a and b legs
    a_hours = hours_list
    a_carrier = carrier_list
    b_hours = hours_list[1::2]
    b_carrier = carrier_list[1::2]

    cols = (['Out Day', 'Out Time', 'Out Weekday', 'Out Airline', 'Out Cities', 'Out Duration', 'Out Stops',
             'Out Stop Cities',
             #'Return Day', 'Return Time', 'Return Weekday', 'Return Airline', 'Return Cities', 'Return Duration',
             #'Return Stops', 'Return Stop Cities',
             'Price'])

    flights_df = pd.DataFrame({'Out Day': a_day,
                               'Out Weekday': a_weekday,
                               'Out Duration': a_duration,
                               'Out Cities': a_section_names,
                               #'Return Day': b_day,
                               #'Return Weekday': b_weekday,
                               #'Return Duration': b_duration,
                               #'Return Cities': b_section_names,
                               'Out Stops': a_stop_list,
                               'Out Stop Cities': a_stop_name_list,
                               #'Return Stops': b_stop_list,
                               #'Return Stop Cities': b_stop_name_list,
                               'Out Time': a_hours,
                               'Out Airline': a_carrier,
                               #'Return Time': b_hours,
                               #'Return Airline': b_carrier,
                               'Price': prices_list})[cols]

    flights_df['timestamp'] = strftime("%Y%m%d-%H%M")  # so we can know when it was scraped
    return flights_df


def start_kayak(city_from, city_to, date_start, date_end):
    """City codes - it's the IATA codes!
    Date format -  YYYY-MM-DD"""

    #2022-09-21-flexible-3days?sort=bestflight_a

    kayak = ('https://www.kayak.com/flights/' + city_from + '-' + city_to +
             '/' + date_start + '-flexible-3days?sort=bestflight_a')
    driver.get(kayak)
    #sleep(randint(8, 10))

    # sometimes a popup shows up, so we can use a try statement to check it and close
    try:
        xp_popup_close = '//button[contains(@id,"dialog-close") and contains(@class,"Button-No-Standard-Style close ")]'
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, xp_popup_close))).click()
        #driver.find_elements_by_xpath(xp_popup_close)[5].click()
    except Exception as e:
        pass
    #sleep(randint(60, 95))
    print('loading more.....')

    #     load_more()

    print('starting first scrape.....')
    df_flights_best = page_scrape()
    df_flights_best['sort'] = 'best'
    #sleep(randint(60, 80))

    # Let's also get the lowest prices from the matrix on top
    matrix = driver.find_elements("xpath", '//*[contains(@id,"FlexMatrixCell")]')
    matrix_prices = [price.text.replace('$', '').replace(',', '') for price in matrix]
    filtered_matrix_prices = list(filter(None, matrix_prices))
    filtered_matrix_prices = list(map(int, filtered_matrix_prices))
    matrix_min = min(filtered_matrix_prices)
    matrix_max = min(filtered_matrix_prices)
    matrix_avg = sum(filtered_matrix_prices) / len(filtered_matrix_prices)
    #matrix_min = 99999
    #matrix_max = 99999
    #matrix_avg = 99999

    print('switching to cheapest results.....')
    cheap_results = '//a[@data-code = "price"]'
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, cheap_results))).click()
    #driver.find_element("xpath", cheap_results).click()
    sleep(randint(60, 90))
    print('loading more.....')

    #     load_more()

    print('starting second scrape.....')
    df_flights_cheap = page_scrape()
    df_flights_cheap['sort'] = 'cheap'
    #sleep(randint(60, 80))

    print('switching to quickest results.....')
    quick_results = '//a[@data-code="duration"]'
    ad = '//div[@class="bBPb-close"]'

    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, ad))).click()
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, quick_results))).click()
    #driver.find_element("xpath", quick_results).click()
    sleep(randint(60, 90))
    print('loading more.....')

    #     load_more()

    print('starting third scrape.....')
    df_flights_fast = page_scrape()
    df_flights_fast['sort'] = 'fast'
    #sleep(randint(60, 80))

    # saving a new dataframe as an excel file. the name is custom made to your cities and dates
    final_df = df_flights_cheap.append(df_flights_best).append(df_flights_fast)
    final_df.to_excel(r'/home/mikdelac/ticket-crawler/search_backups/{}_flights_{}-{}_from_{}_to_{}.xlsx'.format(strftime("%Y%m%d-%H%M"),
                                                                                   city_from, city_to,
                                                                                   date_start, date_end), index=False)
    print('saved df.....')

    # We can keep track of what they predict and how it actually turns out!
    xp_loading = '//div[contains(@id,"advice")]'
    loading = driver.find_element("xpath", xp_loading).text
    xp_prediction = '//span[@class="info-text"]'
    prediction = driver.find_element("xpath", xp_prediction).text
    print(loading + '\n' + prediction)

    # sometimes we get this string in the loading variable, which will conflict with the email we send later
    # just change it to "Not Sure" if it happens
    weird = '¯\\_(ツ)_/¯'
    if loading == weird:
        loading = 'Not sure'

    username = ''
    password = ''

    server = smtplib.SMTP('smtp.outlook.com', 587)
    server.ehlo()
    server.starttls()
    server.login(username, password)
    msg = ('Trajectory {} -> {}\n\n\
            Dates {} - flexible 3 days\n\n\
           Cheapest Flight: {} US\nAverage Price: {} US\n\n{}\n\nEnd of message'.format(departure, destination, date_start, matrix_min, matrix_avg,
                                                                                       ('Kayak API recommandations and predictions:' + '\n' + loading + '\n' + prediction)))

    sender = ''
    recipients = ['']

    message = MIMEMultipart()
    message['From'] = sender
    message['to'] = ", ".join(recipients)
    message['Subject'] = 'Flight Scraper {}->{}'.format(departure, destination)
    message.attach(MIMEText(msg))

    files = []
    files.append('/home/mikdelac/ticket-crawler/search_backups/{}_flights_{}-{}_from_{}_to_{}.xlsx'.format(strftime("%Y%m%d-%H%M"),
                                                                                              city_from, city_to,
                                                                                              date_start, date_end))


    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        message.attach(part)

    server.sendmail(sender, recipients, message.as_string())
    print('sent email.....')


#city_from = input('From which city? ')
#city_to = input('Where to? ')
#date_start = input('Search around which departure date? Please use YYYY-MM-DD format only ')
#date_end = input('Return when? Please use YYYY-MM-DD format only ')

date_start = '2022-09-08'

# not use
date_end = '2022-09-08'

for n in range(0, 5):
    start_kayak(departure, destination, date_start, date_end)
    print('iteration {} was complete @ {}'.format(n, strftime("%Y%m%d-%H%M")))

    # Wait 4 hours
    sleep(60 * 60 * 4)
    print('sleep finished.....')
