[![Release](https://img.shields.io/github/v/release/jdaleo23/ha-power-watchdog?style=for-the-badge)](https://github.com/jdaleo23/ha-power-watchdog/releases)
[![HACS Badge](https://img.shields.io/badge/HACS-default-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Compatibility](https://img.shields.io/badge/compatibility-30A%20%26%2050A-blue?style=for-the-badge)

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-red.svg?style=for-the-badge)](https://paypal.me/jordandaleo)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_☕-red?style=for-the-badge&logo=ko-fi&logoColor=white&labelColor=grey)](https://ko-fi.com/jdaleo23)

# Hughes Power Watchdog - Smart Surge Protector <img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/PWD logo.png">

A custom Home Assistant integration for the [**Hughes Power Watchdog**](https://www.powerwatchdog.com/surge-protectors) smart surge protectors. This integration uses Bluetooth Low Energy (BLE) to provide real-time monitoring of your RV's power status directly in Home Assistant.

## Compatibility & Hardware

This integration supports the Gen 2 Bluetooth protocol used by current Power Watchdog models.

| Model | BLE Prefix | Status |
|-------|-----------|--------|
| 30A Smart Surge Protector | `WD_V6` | Supported |
| 50A Smart Surge Protector | `WD_E7` | Supported |
| E8 models | `WD_E8` | Discovered (untested) |

**30A** models report a single set of voltage / current / power / energy / frequency sensors.

**50A** models report separate **L1** and **L2** sensors (one per AC line) plus combined **Total Power** and **Total Energy** sensors. The integration auto-detects which model is connected based on the data it receives.

## Features

* **Auto-Discovery:** Automatically finds nearby Power Watchdog devices via Home Assistant's Bluetooth integration.
* **Local Push:** Data arrives in real-time over BLE notifications — no cloud or polling required.
* **30A & 50A Support:** Single-line and dual-line models are both handled with the same protocol parser.
* **Robust Protocol Handling:** A packet-reassembly buffer correctly handles BLE fragmentation and ignores non-telemetry frames (error reports, alarms), preventing stale or incorrect readings.
* **Key Sensors (per line):**
  * Voltage (V) — input and output
  * Current (A)
  * Power (W)
  * Energy Consumption (kWh)
  * Frequency (Hz)
* **Totals (50A):** Combined Total Power and Total Energy across both lines.
* **Controls:**
  * Reset Total Energy Button — reset the accumulated kWh counter directly from Home Assistant.

## Requirements

* **Hardware:** Hughes Power Watchdog (Bluetooth models: WD\_V6, WD\_E7, WD\_E8).
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
4. Select your device from the discovered list.

## Sensors

### 30A Models (single line)

| Sensor | Unit | Description |
|--------|------|-------------|
| L1 Voltage | V | Input voltage |
| L1 Current | A | Line current draw |
| L1 Power | W | Active power |
| L1 Energy | kWh | Cumulative energy (total increasing) |
| L1 Frequency | Hz | Line frequency |
| L1 Output Voltage | V | Voltage after regulation |
| Total Power | W | Same as L1 Power |
| Total Energy | kWh | Same as L1 Energy |

### 50A Models (dual line)

All L1 sensors above, plus an identical set of L2 sensors. **Total Power** and **Total Energy** are the sum of both lines.

> L2 sensors will show as *unavailable* until the first dual-line data frame arrives from the device. On 30A models they remain unavailable permanently and can be hidden in your dashboard.

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

<img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/safety_gauges.png" width="300">
<img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/sensors.png" width="300">

## Support the Project
If you find this integration useful, consider supporting the original author:
* [Donate with PayPal](https://paypal.me/jordandaleo)
* [Buy Me A Coffee](https://ko-fi.com/jdaleo23)
