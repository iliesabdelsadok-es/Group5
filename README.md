# Group5
Raspberry-Pi–powered automated window control system

## Overview

This project is a Raspberry-Pi–powered automated window control system designed for a classroom environment.  
It uses temperature, moisture, presence detection, and a democratic voting mechanism to decide whether to open or close windows.  
All events and errors are logged to InfluxDB.

## Table of Contents

- [Overview](#overview)
- [Hardware Components](#hardware-components)
- [InfluxDB Logging](#influxdb-logging)
- [Presence Management](#presence-management)
- [Environmental Monitoring](#environmental-monitoring)
- [Voting System](#voting-system)
- [Window Closing Logic](#window-closing-logic)
- [Error Handling](#error-handling)
- [Main Loop Summary](#main-loop-summary)
- [Required Libraries](#required-libraries)
- [Monitoring & Dashboards (Grafana)](#monitoring--dashboards-grafana)
- [Conclusion](#conclusion)

## Hardware Components

| Component             | Purpose                      | GPIO       |
| --------------------- | ---------------------------- | ---------- |
| Raspberry Pi          | Main controller              | —          |
| Grove Relay           | Opens/closes window          | 22         |
| JHD1802 LCD           | Displays system messages     | I²C        |
| DHT11 Sensor          | Measures indoor temperature  | 26         |
| Grove Moisture Sensor | Rain/soil moisture detection | A1 → CH4   |
| Presence buttons      | Student presence & voting    | 12, 16, 18 |
| Start button          | New session reset            | 6          |


## Presence Management

Each student presses their assigned button to mark presence.

The START button clears presence and begins a new session.

The LCD displays the number of present students.

## Environmental Monitoring

The loop continuously reads:
- Temperature (DHT11)
- Moisture level (rain detection)

Voting is triggered when:
- Temperature > 25°C
- Moisture < 50 (dry)
- Window is closed

## Voting System

When conditions require opening the window:
- LCD displays: “Open windows? Press button”
- Present students vote by pressing their presence button

Voting rules:
- Vote duration: 15 seconds
- If YES votes > 50% → window opens
- Cooldown prevents repeated votes after a NO result

## Window Closing Logic

When the window is open:
- If temperature < 24°C → close window
- If moisture > 200 (rain detected) → close window

The LCD displays the reason for closing.

## Error Handling

If an exception happens, a safe shutdown ensures:
- Relay off
- LCD cleared
- GPIO cleanup

## Main Loop Summary

Runs every 1 second and executes:
- Presence detection
- Environmental measurement
- Voting logic
- Window opening/closing
- Logging of all events

The system operates fully autonomously.

## Required Libraries

Hardware & GPIO:
- RPi.GPIO
- grove.grove_relay
- grove.display.jhd1802
- grove.grove_moisture_sensor
- dht11

Data logging:
- influxdb_client

Utilities:
- time
- traceback
- 
## InfluxDB Logging

Different types of data are stored in an local influx database:

### Environment & Voting
- temperature
- moisture
- vote count
- totalPresent

### Error Logs
- error message
- full Python traceback in case of error

## Monitoring & Dashboards (Grafana)

The system provides real-time monitoring dashboards using **Grafana**, accessible on **port 8080**.

Dashboards are connected to **InfluxDB** and allow visualization of system behavior and voting activity.

Available dashboards include:
- **Validated votes vs number of participants**
- **Validated votes vs temperature**
- **Environmental monitoring** (temperature & moisture over time)

Grafana enables analysis of classroom behavior, environmental conditions, and decision-making efficiency.

Access Grafana at:  
`http://<raspberry-pi-ip>:8080`

## Conclusion

This prototype combines environmental sensors, user interaction, and automated decision-making to manage classroom ventilation intelligently and safely.  
It enhances comfort, encourages engagement, and logs all system activity for further analysis.
