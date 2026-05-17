import tkinter as tk
from tkinter import Frame, Label, Button, Text
import threading
import requests
import speech_recognition as sr
import pyttsx3

# =========================
# CONFIG
# =========================
WEATHER_API_KEY = "c8558652c35dd3188649b9785b3e446b"
LAT, LON = 18.3, 74.6

# =========================
# SPEECH
# =========================
engine = pyttsx3.init()
voice_enabled = True

def speak(text):
    if voice_enabled:
        engine.stop()
        engine.say(text)
        engine.runAndWait()

# =========================
# LISTEN
# =========================
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        update_status("🎤 Listening...")
        audio = r.listen(source)

    try:
        return r.recognize_google(audio).lower()
    except:
        return ""

# =========================
# OLLAMA AI
# =========================
def ask_ai(prompt):
    try:
        url = "http://localhost:11434/api/generate"

        system_prompt = f"""
You are an AI driver assistant for India.

If user asks for trip:
- Give detailed plan (days, places, food, cost)
- Keep realistic Indian prices

User: {prompt}
AI:
"""

        res = requests.post(
            url,
            json={
                "model": "llama3",
                "prompt": system_prompt,
                "stream": False
            },
            timeout=120   # 🔥 FIXED
        )

        return res.json().get("response", "AI not responding")

    except Exception as e:
        return f"AI error: {e}"

# =========================
# WEATHER (SAFE)
# =========================
def get_weather(city=None):
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "appid": WEATHER_API_KEY,
            "units": "metric"
        }

        if city:
            params["q"] = city
        else:
            params["lat"] = LAT
            params["lon"] = LON

        data = requests.get(url, params=params, timeout=5).json()

        if "main" not in data:
            return None, None

        return data["main"]["temp"], data["weather"][0]["main"]

    except:
        return None, None

# =========================
# LOCATION
# =========================
def get_coordinates(city):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json"}
        headers = {"User-Agent": "driver-ai"}

        data = requests.get(url, params=params, headers=headers).json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass
    return None, None

# =========================
# FUEL
# =========================
def get_fuel_city(city):
    lat, lon = get_coordinates(city)
    if not lat:
        return ["Location not found"]

    query = f"""
    [out:json][timeout:20];
    node["amenity"="fuel"](around:4000,{lat},{lon});
    out;
    """

    try:
        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers={"User-Agent": "driver-ai"},
            timeout=10
        )

        data = res.json()
        stations = []

        for el in data.get("elements", []):
            name = el.get("tags", {}).get("name")
            if name and len(name) > 3:
                stations.append(name)

        return list(dict.fromkeys(stations))[:5] or ["No stations found"]

    except:
        return ["Fuel unavailable"]

# =========================
# CAFES
# =========================
def get_cafes(city):
    lat, lon = get_coordinates(city)
    if not lat:
        return ["Location not found"]

    query = f"""
    [out:json][timeout:20];
    node["amenity"="cafe"](around:4000,{lat},{lon});
    out;
    """

    try:
        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers={"User-Agent": "driver-ai"},
            timeout=10
        )

        data = res.json()
        cafes = []

        for el in data.get("elements", []):
            name = el.get("tags", {}).get("name")
            if name and len(name) > 3:
                cafes.append(name)

        return list(dict.fromkeys(cafes))[:5] or ["No cafes found"]

    except:
        return ["Cafe unavailable"]






# =========================
# SMART HANDLER
# =========================
def extract_city(text):
    if "in" in text:
        return text.split("in")[-1].strip()
    if "of" in text:
        return text.split("of")[-1].strip()
    return None

def handle(user):
    user = user.lower()

    if "weather" in user:
        city = extract_city(user)
        temp, cond = get_weather(city)

        if temp is None:
            return "Weather service not working"
        return f"{city or 'Your area'}: {temp}°C, {cond}"

    elif "fuel" in user or "petrol" in user:
        city = extract_city(user)
        if not city:
            return "Please specify city"
        return "Fuel: " + ", ".join(get_fuel_city(city))

    elif "cafe" in user:
        city = extract_city(user)
        if not city:
            return "Please specify city"
        return "Cafes: " + ", ".join(get_cafes(city))

    elif "drive" in user:
        temp, cond = get_weather()
        if temp and temp >= 40:
            return "Extreme heat. Avoid driving."
        elif cond and "rain" in cond.lower():
            return "Rain detected. Drive carefully."
        return "Driving conditions normal"

    elif "exit" in user:
        root.destroy()

    return ask_ai(user)

# =========================
# UI
# =========================
root = tk.Tk()
root.title("🚗 AI Driver Assistant")
root.geometry("520x650")
root.configure(bg="#0f1117")

Label(root, text="🚗 AI Driver Dashboard",
      font=("Helvetica", 18, "bold"),
      fg="#00ffcc", bg="#0f1117").pack(pady=10)

info = Frame(root, bg="#0f1117")
info.pack()

Label(info, text="📍 Location: Pune",
      fg="white", bg="#0f1117").grid(row=0, column=0, padx=10)

weather_label = Label(info, text="🌦 Loading...",
                      fg="white", bg="#0f1117")
weather_label.grid(row=0, column=1, padx=10)

chat_frame = Frame(root, bg="white", padx=2, pady=2)
chat_frame.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)

chat = Text(chat_frame, bg="#111318", fg="#00ffcc", font=("Consolas", 11))
chat.pack(fill=tk.BOTH, expand=True)

entry = tk.Entry(root, bg="#1c1f26", fg="white")
entry.pack(padx=15, pady=5, fill=tk.X)

def update_status(text):
    status.config(text=text)
    root.update()

def send():
    user = entry.get()
    if not user:
        return

    chat.insert(tk.END, f"You: {user}\n")
    entry.delete(0, tk.END)
    update_status("Thinking...")

    def process():
        reply = handle(user)
        root.after(0, lambda: update_ui(reply))

    threading.Thread(target=process).start()

def update_ui(reply):
    chat.insert(tk.END, f"AI: {reply}\n\n")
    chat.see(tk.END)
    update_status("Ready")
    speak(reply)

def voice():
    text = listen()
    if text:
        entry.insert(0, text)
        send()

def toggle_voice():
    global voice_enabled
    voice_enabled = not voice_enabled
    update_status(f"Voice {'ON' if voice_enabled else 'OFF'}")

btns = Frame(root, bg="#0f1117")
btns.pack()

Button(btns, text="Send", command=send).grid(row=0, column=0, padx=5)
Button(btns, text="Voice", command=lambda: threading.Thread(target=voice).start()).grid(row=0, column=1, padx=5)
Button(btns, text="Toggle Voice", command=toggle_voice).grid(row=0, column=2, padx=5)

status = Label(root, text="Ready", fg="lightgreen", bg="#0f1117")
status.pack()

# load weather
def load_weather():
    temp, cond = get_weather()
    if temp:
        weather_label.config(text=f"🌦 {temp}°C, {cond}")

root.after(1000, load_weather)

root.mainloop()



#ollama run llama3
#python main.py

#run this file to start the app. You can type or speak commands like:       
# "What's the weather in Mumbai?"
# "Find fuel stations in Delhi"
# "Is it safe to drive?"    