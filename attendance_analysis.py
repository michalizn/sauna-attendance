from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import csv
import requests

WEATHER_API_KEY = "f828caa5030c02984d4cc6b0c2b778f8"

# URL of the page
url = 'https://www.delfinub.cz/aktualni-obsazenost'

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')

# Initialize the current date
current_date = datetime.now().date()

# Sauna timetable (adjust according to your specific case)
timetable = {
    "monday": {"status": "closed", "sessions": []},
    "tuesday": {"status": "open", "sessions": [("14:00", "21:30", "shared sauna")]},
    "wednesday": {
        "status": "open",
        "sessions": [
            ("14:00", "17:30", "shared sauna"),
            ("17:30", "19:30", "women only"),
            ("19:30", "21:30", "men only"),
        ],
    },
    "thursday": {"status": "open", "sessions": [("14:00", "21:30", "shared sauna")]},
    "friday": {"status": "open", "sessions": [("14:00", "21:30", "shared sauna")]},
    "saturday": {"status": "open", "sessions": [("12:00", "21:30", "shared sauna")]},
    "sunday": {"status": "open", "sessions": [("12:00", "21:30", "shared sauna")]},
}

# Dictionary of Czech national holidays (month, day)
CZECH_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (5, 1): "Labor Day",
    (5, 8): "Liberation Day",
    (7, 5): "Saints Cyril and Methodius Day",
    (7, 6): "Jan Hus Day",
    (9, 28): "Czech Statehood Day",
    (10, 28): "Independent Czechoslovak State Day",
    (11, 17): "Struggle for Freedom and Democracy Day",
    (12, 24): "Christmas Eve",
    (12, 25): "Christmas Day",
    (12, 26): "Saint Stephen's Day"
}

def get_weather(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            weather = {
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
            }
            return weather
        else:
            print(f"Weather API error: {data.get('message')}")
            return None
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def is_national_holiday(date: datetime):
    month_day = (date.month, date.day)
    holiday_name = CZECH_HOLIDAYS.get(month_day)
    return holiday_name if holiday_name else None

def get_current_session():
    now = datetime.now()
    day = now.strftime("%A").lower()
    timetable_entry = timetable.get(day, {"status": "closed"})
    if timetable_entry["status"] == "closed":
        return "closed", None
    current_time = now.strftime("%H:%M")
    for start, end, session_type in timetable_entry["sessions"]:
        if start <= current_time <= end:
            return "open", session_type
    return "closed", None

def create_new_csv():
    today_date = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"sauna_data_{today_date}.csv"
    with open(file_name, mode="a", newline="") as file:
        writer = csv.writer(file)
        # Write the header row
        writer.writerow(["timestamp", "day", "session_type", "persons_count_sauna", "persons_count_pool" 
                         "temperature_home", "weather_description_home", 
                         "temperature_sauna", "weather_description_sauna", 
                         "national_holiday"])
    print(f"New log file created: {file_name}")
    return file_name

# Create the first CSV file
file_name = create_new_csv()

# Main loop
while True:
    # Get the current date
    new_date = datetime.now().date()

    # Check if the day has changed
    if new_date != current_date:
        current_date = new_date
        # Create a new CSV file for the new day
        file_name = create_new_csv()

    today_date = datetime.now().strftime("%Y%m%d%H%M%S")

    session_status, session_type = get_current_session()
    if session_status == "open":
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get(url)  # Load the webpage
            # Scroll down a little
            driver.execute_script("window.scrollBy(0, 200);")  # Adjust '200' to your needs

            time.sleep(10)  # Allow the page to fully load
            driver_init = True
        except:
            print("Error opening URL!")
        try:
            persons_div_sauna = driver.find_element(By.XPATH, '//*[@id="snippet-container-default-widget-5011d2eee6b2fe3ef8b4e4abcd9a742f-widgetsnippet"]/div/div/div[3]/div/div/div/div')
            persons_div_pool = driver.find_element(By.XPATH, '//*[@id="snippet-container-default-widget-5011d2eee6b2fe3ef8b4e4abcd9a742f-widgetsnippet"]/div/div/div[2]/div/div/div/div')
            number_sauna = persons_div_sauna.text.strip()
            number_pool = persons_div_pool.text.strip()
        except Exception as e:
            print(f"Error scraping data: {e}")
        if driver_init:
            # Close the browser
            driver.quit()
    else:
        print("Sauna is closed.")
        number_sauna = 0
        number_pool = 0
        session_type = "closed"
    try:
        weather_home = get_weather(49.03317655577836, 17.656029372771396) # Weather at home
        weather_sauna = get_weather(49.02044866857781, 17.649074144949278) # Weather at sauna
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        holiday = is_national_holiday(datetime.now())
        day = datetime.now().strftime("%A")
        temperature_home = weather_home["temperature"] if weather_home else "N/A"
        weather_desc_home = weather_home["description"] if weather_home else "N/A"
        temperature_sauna = weather_sauna["temperature"] if weather_sauna else "N/A"
        weather_desc_sauna = weather_sauna["description"] if weather_sauna else "N/A"
        holiday_status = "Yes" if holiday else "No"
    except:
        print("Something went wrong.")

    print(
        f"{timestamp} - {day} - {session_type}: {number_sauna} persons, {number_pool} persons at pool, {temperature_home}°C, {weather_desc_home}, {temperature_sauna}°C, {weather_desc_sauna}, Holiday: {holiday_status}"
    )
    with open(file_name, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, day, session_type, number_sauna, number_pool, temperature_home, weather_desc_home, temperature_sauna, weather_desc_sauna, holiday_status])
        file.close()
    
    # Wait 210 seconds before the next check
    time.sleep(210)