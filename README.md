[![Release](https://img.shields.io/github/v/release/jdaleo23/ha-power-watchdog?style=for-the-badge)](https://github.com/jdaleo23/ha-power-watchdog/releases)
[![HACS Badge](https://img.shields.io/badge/HACS-default-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Compatibility](https://img.shields.io/badge/compatibility-30A%20%26%2050A-blue?style=for-the-badge)

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-red.svg?style=for-the-badge)](https://paypal.me/jordandaleo)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_☕-red?style=for-the-badge&logo=ko-fi&logoColor=white&labelColor=grey)](https://ko-fi.com/jdaleo23)

# Hughes Power Watchdog - Smart Surge Protector <img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/PWD logo.png" alt="Power Watchdog logo">

A custom Home Assistant integration for the [**Hughes Power Watchdog**](https://www.powerwatchdog.com/surge-protectors) smart surge protectors. This integration uses Bluetooth Low Energy (BLE) to provide real-time monitoring of your RV's power status directly in Home Assistant.

## Compatibility & Hardware

This integration supports both Gen 1 (Bluetooth-only) and Gen 2 (WiFi + Bluetooth) Power Watchdog models.

### Gen 2 (WiFi + Bluetooth)

Gen 2 devices advertise as `WD_{type}_{serial}`. The type suffix digit determines the line count:

| Suffix digit | Line type | Examples |
|-------------|-----------|----------|
| 5, 6 | 30A single-line | `WD_V5`, `WD_V6`, `WD_E5`, `WD_E6` |
| 7, 8, 9 | 50A dual-line | `WD_E7`, `WD_E8`, `WD_V7`, `WD_V8`, `WD_E9`, `WD_V9` |

### Gen 1 (Bluetooth-only)

Gen 1 devices advertise as `PM{S|D}...` (19-character name):

| Prefix | Line type |
|--------|-----------|
| `PMS` | 30A single-line |
| `PMD` | 50A dual-line |

### Sensor behaviour

**30A** models report a single set of voltage / current / power / energy / frequency sensors.

**50A** models report separate **L1** and **L2** sensors (one per AC line) plus combined **Total Power** and **Total Energy** sensors. The integration auto-detects which model is connected based on the data it receives.

> **Note:** This integration has been developed and tested on a **WD_V6 (30A Gen 2)**. The 50A dual-line and Gen 1 models are implemented but have not been personally verified. If you have one of these and can confirm it works, please [open an issue](https://github.com/jdaleo23/ha-power-watchdog/issues) or start a [Discussion](https://github.com/jdaleo23/ha-power-watchdog/discussions)!

## Features

* **Auto-Discovery:** Automatically finds nearby Power Watchdog devices via Home Assistant's Bluetooth integration.
* **Local Push:** Data arrives in real-time over BLE notifications — no cloud or polling required.
* **30A & 50A Support:** Single-line and dual-line models are both handled with the same protocol parser.
* **Smart Sensor Defaults:** Sensors are automatically enabled or disabled based on your device's model number so your dashboard is clean from the start.
* **Robust Protocol Handling:** A packet-reassembly buffer correctly handles BLE fragmentation and ignores non-telemetry frames (error reports, alarms), preventing stale or incorrect readings.
* **Key Sensors (per line):**
  * Voltage (V) — input voltage
  * Current (A)
  * Power (W)
  * Energy Consumption (kWh)
  * Frequency (Hz)
* **Totals (50A):** Combined Total Power and Total Energy across both lines.
* **Controls:**
  * Reset Total Energy Button — reset the accumulated kWh counter directly from Home Assistant.

## Requirements

* **Hardware:** Hughes Power Watchdog — any Gen 1 (PM\*) or Gen 2 (WD\_\*) Bluetooth model.
* **Bluetooth:** Bluetooth adapter or proxy on your Home Assistant host.
* **Mobile App:** Ensure the Power Watchdog mobile app is **closed** when trying to connect, as the device only supports one active Bluetooth connection at a time.

## Installation

### Option 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Paste the URL of this repository: `https://github.com/jdaleo23/ha-power-watchdog`
4. Select **Integration** as the category and click **Add**.
5. Find "Hughes Power Watchdog" and click **Download**.
6. **Restart Home Assistant.**

### Option 2: Manual
1. Download the latest `hughes_power_watchdog.zip` from the [Releases](https://github.com/jdaleo23/ha-power-watchdog/releases) page.
2. Extract the contents into your `config/custom_components/hughes_power_watchdog` folder.
3. **Restart Home Assistant.**

## Configuration
1. Navigate to **Settings > Devices & Services**.
2. Click **+ Add Integration**.
3. Search for **Hughes Power Watchdog**.
4. Select your device from the discovered list and give it a name.

## Sensors

The integration uses your device's model number to automatically enable the sensors that apply to your hardware. The table below shows what's on by default — any disabled sensor can be manually enabled in **Settings → Devices & Services → your device → disabled entities**.

| Sensor | Unit | Description | 30A | 50A | Unknown |
|--------|------|-------------|:---:|:---:|:-------:|
| L1 Voltage | V | Input voltage | ✅ | ✅ | ✅ |
| L1 Current | A | Line current draw | ✅ | ✅ | ✅ |
| L1 Power | W | Active power | ✅ | ✅ | ✅ |
| L1 Energy | kWh | Cumulative energy | ✅ | ✅ | ✅ |
| L1 Frequency | Hz | Line frequency | ✅ | ✅ | ✅ |
| L1 Output Voltage | V | Voltage after regulation | ❌ | ❌ | ❌ |
| L2 Voltage | V | Input voltage (line 2) | ❌ | ✅ | ✅ |
| L2 Current | A | Line 2 current draw | ❌ | ✅ | ✅ |
| L2 Power | W | Line 2 active power | ❌ | ✅ | ✅ |
| L2 Energy | kWh | Line 2 cumulative energy | ❌ | ✅ | ✅ |
| L2 Frequency | Hz | Line 2 frequency | ❌ | ✅ | ✅ |
| L2 Output Voltage | V | Voltage after regulation (line 2) | ❌ | ❌ | ❌ |
| Total Power | W | Combined L1 + L2 power | ✅ | ✅ | ✅ |
| Total Energy | kWh | Combined L1 + L2 energy | ✅ | ✅ | ✅ |

> If your model isn't listed above, all sensors except Output Voltage will be enabled by default. [Open an issue](https://github.com/jdaleo23/ha-power-watchdog/issues) with your device's BLE name so it can be added to the compatibility list.
 
> **Output Voltage** is disabled on all models — on tested hardware it was found to not report a real voltage reading. It may work on voltage-booster variants, so if you have one and can confirm it works, please [open an issue](https://github.com/jdaleo23/ha-power-watchdog/issues) with your model number.
## Known Issues / Troubleshooting

* **"No Devices Found":** Ensure your Power Watchdog is powered on and that the official phone app is completely closed.
* **Connection Stability:** Bluetooth range can be limited; if you experience dropouts, consider using an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) closer to your RV.
* **Stale BlueZ Connections:** If the device was previously connected and the connection was not cleanly closed, your Bluetooth stack may hold a stale connection handle. Power-cycling the Power Watchdog or restarting Home Assistant will resolve this.

## Support & Community
* **Found a bug?** Please [open an issue](https://github.com/jdaleo23/ha-power-watchdog/issues) and include your logs.
* **Have a question?** Join the [Discussions](https://github.com/jdaleo23/ha-power-watchdog/discussions) to ask questions or share your dashboard setup.
* **Feature Requests:** Have an idea for a new sensor or feature? Let's talk about it in the Discussions tab!

## Dashboard Setup
Here is a sample layout for your 30A connection showing the 80% safety limits and available sensors:

<img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/safety_gauges.png" width="300" alt="Safety gauge dashboard example">
<img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/sensors.png" width="300" alt="Sensor card dashboard example">

## Support the Project
If you find this integration useful, consider supporting the original author:
* [Donate with PayPal](https://paypal.me/jordandaleo)
* [Buy Me A Coffee](https://ko-fi.com/jdaleo23)
