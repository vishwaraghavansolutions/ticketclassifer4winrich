import streamlit as st
import redis
import requests
import json

r = redis.Redis(host="localhost", port=6379, db=0)

def get_weather(city):
    key = f"weather:{city}"
    cached = r.get(key)
    if cached:
        return json.loads(cached)

    # Call API if not cached
    resp = requests.get(f"https://wttr.in/{city}?format=j1")
    data = resp.json()
    r.setex(key, 3600, json.dumps(data))  # cache for 1 hour
    return data

st.title("Weather App with Redis Cache 🌦️")
city = st.text_input("Enter city:", "London")

if city:
    weather = get_weather(city)
    st.write(weather["current_condition"][0]["temp_C"], "°C")