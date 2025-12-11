import time
import RPi.GPIO as GPIO
from grove.grove_relay import GroveRelay
from grove.display.jhd1802 import JHD1802
from grove.grove_moisture_sensor import GroveMoistureSensor
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import dht11
import traceback

# ---------------------------
# Hardware setup
# ---------------------------
BUTTON_PINS = [12, 16, 18]
START_BUTTON = 6

GPIO.setmode(GPIO.BCM)

for pin in BUTTON_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.setup(START_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

relay = GroveRelay(22)
lcd = JHD1802()

# DHT11 on GPIO26
DHT_IN_PIN = 26
temp_in_sensor = dht11.DHT11(pin=DHT_IN_PIN)

moisture_sensor = GroveMoistureSensor(4)  # Analog A1

# ---------------------------
# InfluxDB setup
# ---------------------------
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "1DsThT98xSUYXaKABqOi124660yCYPTuN7s9JVUqB_2c6EDrN-QFrAZ5mPIf5WZlnVwQUnAuL6HXvF4-Oevuzw=="
INFLUX_ORG = "Universidad de Deusto"
INFLUX_BUCKET = "group5"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ---------------------------
# global var
# ---------------------------
last_no_vote_time = 0
VOTE_COOLDOWN = 10

# ---------------------------
# Presence management
# ---------------------------
present_students = set()
voting_in_progress = False

# ---------------------------
# Helper functions
# ---------------------------
def log_data(temp, moisture, vote, totalPresent):
    point = Point("classroom") \
        .field("temperature", temp) \
        .field("moisture", moisture) \
        .field("vote", vote)\
        .field("totalPresent", totalPresent)
    write_api.write(bucket=INFLUX_BUCKET, record=point)

def log_error(message, traceback):
    point = Point("error") \
        .field("message", message) \
        .field("traceback", traceback)
    write_api.write(bucket=INFLUX_BUCKET, record=point)

def check_conditions():
    temp = temp_in_sensor.read()
    temperature = temp.temperature if temp.is_valid() else None
    moisture = moisture_sensor.moisture
    print(f"Temp: {temperature}°C, Moisture: {moisture}")
    condition = (temperature is not None and temperature > 25 and moisture < 50)
    return condition, temperature, moisture

def lcd_clear_line(row):
    lcd.setCursor(row, 0)
    lcd.write(" " * 16)

def lcd_write_line(row, text):
    lcd_clear_line(row)
    lcd.setCursor(row, 0)
    lcd.write(text[:16])

def close_windows_conditions(temperature, moisture):
    print("verifying if room is cooler")
    print(f"Temp: {temperature}°C, Moisture: {moisture}")
    notCooler = temperature is None or temperature > 23
    lowMoisture = moisture < 200
    if not notCooler:
       lcd_write_line(0, "Room cooler")
       lcd_write_line(1, "closing windows.")
       print("room cooler. Closing windows.")
       relay.off()
    elif not lowMoisture:
       lcd_write_line(0, "It's raining")
       lcd_write_line(1, "closing windows.")
       print("it's raining. Closing windows.")
       relay.off()
    else:
        print("room not cooler")
    return notCooler and lowMoisture, temperature, moisture

def update_presence():
    for pin in BUTTON_PINS:
        value = GPIO.input(pin)
#        if pin == 6:
#            value = not value   #invert logic here
        if value == 1 and pin not in present_students:
            present_students.add(pin)
            print(f"Participant present on button {pin} → total: {len(present_students)}")
            lcd_write_line(0, f"{len(present_students)} present")
            lcd_write_line(1, "Ready to vote")
            time.sleep(0.2)

def vote_for_window(temperature, moisture, vote_duration=15):
    global voting_in_progress
    if len(present_students) == 0:
        print("No students present → skip vote")
        return False

    voting_in_progress = True
    print("Vote for windows started")
    lcd_write_line(0, "Open windows?")
    lcd_write_line(1, "Press button")

    pressed = {pin: False for pin in BUTTON_PINS}
    start_time = time.time()

    while (time.time() - start_time) < vote_duration:
         for pin in BUTTON_PINS:
            value = GPIO.input(pin)
            if pin == 6:
                value = not value   #invert logic here
            if value == 1 and not pressed[pin] and pin in present_students:
                pressed[pin] = True
                print(f"Button {pin} pressed")
         time.sleep(0.1)

    yes_votes = sum(pressed.values())
    total_present = len(present_students)
    print(f"YES votes = {yes_votes}, PRESENT = {total_present}")

    if yes_votes > total_present / 2:
        lcd_write_line(0, "Vote: YES")
        lcd_write_line(1, "Opening window")
        relay.on()
        log_data(temperature, moisture, yes_votes, total_present)
        result = True
    else:
        lcd_write_line(0, "Vote: NO")
        lcd_write_line(1, "Staying closed")
        log_data(temperature, moisture, yes_votes, total_present)
        result = False

    voting_in_progress = False
    return result

# ---------------------------
# Main loop
# ---------------------------
try:
    window_open = False
    while True:
        print("Windows open ?")
        print(window_open)
        if GPIO.input(START_BUTTON) == 0:
            print("START course button pressed → resetting presence")
            present_students.clear()
            lcd_write_line(0, "Class started")
            lcd_write_line(1, "Presence cleared")
            time.sleep(1)

        lcd_clear_line(0)
        lcd_clear_line(1)

        if not voting_in_progress:
            update_presence()

        condition, temperature, moisture = check_conditions()
        current_time = time.time()
        if condition and not window_open:
            if current_time - last_no_vote_time >= VOTE_COOLDOWN:
                voted = vote_for_window(temperature, moisture)
                if voted:
                    window_open = True
                else:
                    last_no_vote_time = time.time()
            else:
                lcd_write_line(0, "Vote paused")
                lcd_write_line(1, "Wait 10 min")

        if window_open:
            condition, temperature, moisture = close_windows_conditions(temperature, moisture)
            if not condition:
                window_open = False

        time.sleep(1)

except KeyboardInterrupt:
    print("Exiting program")
    relay.off()
    lcd.text("", "")
    GPIO.cleanup()
    tb_str = traceback.format_exc()

except Exception as e:
    print("Exception catched")
    relay.off()
    lcd_clear_line(0)
    lcd_clear_line(1)
    GPIO.cleanup()
    tb_str = traceback.format_exc()
    log_error(str(e), tb_str)
