import dash
from dash import Input, Output, State
from dash import dcc, html
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import os
import re
import glob
from app import app
from plotly.subplots import make_subplots
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import csv
import requests
import threading

dash.register_page(__name__, path='/')

data_dir = os.path.dirname(os.path.abspath(__file__)).replace('pages', 'data')
gpx_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

with open(data_dir.replace('data', 'weather_api.txt')) as api_txt:
    text = api_txt.readlines()
    WEATHER_API_KEY = text[0]

# Variables for tracking current day and file
current_date = datetime.now().date()
file_name = None

# Variables for the sauna timetable
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

# Czech holidays
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
    (12, 26): "Saint Stephen's Day",
}

# Weather fetching function
def get_weather(lat, lon, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            return {"temperature": data["main"]["temp"], "description": data["weather"][0]["description"]}
    except Exception as e:
        print(f"Error fetching weather: {e}")
    return {"temperature": "N/A", "description": "N/A"}

# Determine current session type
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

# Function to create a new CSV file for each day
def create_new_csv():
    global file_name
    today_date = datetime.now().strftime("%Y%m%d")
    file_name = f"{data_dir}/sauna_data_{today_date}.csv"

    if os.path.isfile(file_name):
        print(f"Log file already exists!")
        return file_name
    
    with open(file_name, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "day", "session_type", "persons_sauna", "persons_pool",
                         "temperature_home", "weather_description_home", 
                         "temperature_sauna", "weather_description_sauna", 
                         "national_holiday"])
    print(f"New log file created: {file_name}")
    return file_name

def is_national_holiday(date: datetime):
    month_day = (date.month, date.day)
    holiday_name = CZECH_HOLIDAYS.get(month_day)
    return holiday_name if holiday_name else None

# Function to load data from the current file
def load_data():
    if file_name and os.path.exists(file_name):
        return pd.read_csv(file_name)
    return pd.DataFrame(columns=["timestamp", "day", "session_type", "persons_sauna", 
                                 "persons_pool", "temperature_home", "weather_description_home", 
                                 "temperature_sauna", "weather_description_sauna", "national_holiday"])

# Function to save new data into the current day's CSV file
def save_data(data):
    global current_date
    new_date = datetime.now().date()
    if new_date != current_date:  # Check if the day has changed
        current_date = new_date
        create_new_csv()
    with open(file_name, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([data["timestamp"], data["day"], data["session_type"], data["persons_sauna"],
                         data["persons_pool"], data["temperature_home"], data["weather_description_home"],
                         data["temperature_sauna"], data["weather_description_sauna"], data["national_holiday"]])

# Fetch data from website and API
def fetch_data():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    session_status, session_type = get_current_session()
    if session_status == "closed":
        return None  # No need to fetch data if the sauna is closed

    driver = webdriver.Chrome(options=chrome_options)
    url = 'https://www.delfinub.cz/aktualni-obsazenost'
    try:
        driver.get(url)
        # Scroll down a little
        driver.execute_script("window.scrollBy(0, 350);")  # Adjust '200' to your needs
        time.sleep(10)
        persons_sauna = driver.find_element(By.XPATH, '//*[@id="snippet-container-default-widget-5011d2eee6b2fe3ef8b4e4abcd9a742f-widgetsnippet"]/div/div/div[3]/div/div/div/div')
        persons_pool = driver.find_element(By.XPATH, '//*[@id="snippet-container-default-widget-5011d2eee6b2fe3ef8b4e4abcd9a742f-widgetsnippet"]/div/div/div[2]/div/div/div/div')
        persons_sauna = persons_sauna.text.strip()
        persons_pool = persons_pool.text.strip()
    except Exception as e:
        print(f"Error scraping data: {e}")
        persons_sauna = "N/A"
    finally:
        driver.quit()

    weather_home = get_weather(49.03317655577836, 17.656029372771396, WEATHER_API_KEY)
    weather_sauna = get_weather(49.02044866857781, 17.649074144949278, WEATHER_API_KEY)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    day = datetime.now().strftime("%A")
    holiday = is_national_holiday(datetime.now())
    national_holiday = "Yes" if holiday else "No"

    return {
        "timestamp": timestamp,
        "day": day,
        "session_type": session_type,
        "persons_sauna": persons_sauna,
        "persons_pool": persons_pool,
        "temperature_home": weather_home["temperature"],
        "weather_description_home": weather_home["description"],
        "temperature_sauna": weather_sauna["temperature"],
        "weather_description_sauna": weather_sauna["description"],
        "national_holiday": national_holiday,
    }

# Ensure the first CSV file is created
create_new_csv()

def background_task():
    while True:
        print("Background task running...")
        new_data = fetch_data()
        if new_data:
            print(new_data)
            save_data(new_data)
        time.sleep(220)

# Start the background thread
thread = threading.Thread(target=background_task, daemon=True)
thread.start()

# Layout
layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div(id="current-info", style={'textAlign': 'center', 'fontSize': 200}),
                html.Label('persons in sauna', className="desktop-visible", style={'textAlign': 'center', 'fontSize': 30, 'marginBottom': '20px'}),
                html.Label('persons in sauna', className="mobile-visible", style={'textAlign': 'center', 'fontSize': '5vw', 'marginBottom': '20px'}),
            ]),
        ]),
    html.Div(id="temperature-info", style={'textAlign': 'center', 'fontSize': '24px', 'marginBottom': '10px'}),
    html.Div(id="date-info", style={'textAlign': 'center', 'fontSize': '20px', 'marginBottom': '20px'}),
    dcc.Graph(id="sauna-plot"),
    dcc.Interval(id="interval", interval=60 * 4 * 1000, n_intervals=0),
    ]),
])

# Callback to update the dashboard
@app.callback(
    [Output("current-info", "children"),
     Output("temperature-info", "children"),
     Output("date-info", "children"),
     Output("sauna-plot", "figure")],
    [Input("interval", "n_intervals")]
)
def update_dashboard(n):
    # Load all data
    df = load_data()

    # Determine latest information
    if not df.empty:
        latest = df.iloc[-1]
        persons_sauna = latest["persons_sauna"]
        temperature_home = latest["temperature_home"]
        temperature_sauna = latest["temperature_sauna"]
        formatted_date = datetime.now().strftime("%d of %B %Y")  # Format like "19th of November 2024"
        current_info = f"{persons_sauna}"
        temperature_info = f"Home: {temperature_home}°C | Sauna: {temperature_sauna}°C"
        date_info = formatted_date
    else:
        current_info = "0"
        temperature_info = "Home: N/A | Sauna: N/A"
        date_info = datetime.now().strftime("%dth of %B %Y")

    # Create the combined figure with elevation and speed profiles
    persons_sauna_fig = go.Scatter(
        x=df["timestamp"],
        y=df["persons_sauna"],
        mode='lines+markers',
        line=dict(color='blue'),
        marker=dict(size=5, color='blue'),
        text=[f'Number of Persons: {persons}' for persons in df["persons_sauna"]],
        hoverinfo='text'
    )

    temperature_home_fig = go.Scatter(
        x=df["timestamp"],
        y=df["temperature_home"],
        mode='lines+markers',
        line=dict(color='orange'),
        marker=dict(size=5, color='orange'),
        text=[f'Temperature at Home: {temperature} °C' for temperature in df["temperature_home"]],
        hoverinfo='text'
    )
    # if not df.empty:
    #     timetable_entry = timetable.get(datetime.now().strftime("%A").lower(), {"status": "closed"})
    #     start_of_sauna = datetime.combine(datetime.now().date(), datetime.strptime(timetable_entry[0][0], '%H:%M').time())
    #     end_of_sauna = datetime.combine(datetime.now().date(), datetime.strptime(timetable_entry[0][1], '%H:%M').time())
    #     print(start_of_sauna, end_of_sauna)
    combined_fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
    combined_fig.add_trace(persons_sauna_fig, row=1, col=1)
    combined_fig.add_trace(temperature_home_fig, row=2, col=1)
    combined_fig.update_layout(
        # xaxis_title='Time',
        yaxis1_title='Persons in Sauna',
        yaxis2_title='Temperature (°C)',
        showlegend=False,
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    return current_info, temperature_info, date_info, combined_fig


if __name__ == "__main__":
    app.run_server(debug=True)