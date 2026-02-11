[![Release](https://img.shields.io/github/v/release/jdaleo23/ha-power-watchdog?style=for-the-badge)](https://github.com/jdaleo23/ha-power-watchdog/releases)
[![HACS Badge](https://img.shields.io/badge/HACS-default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Compatibility](https://img.shields.io/badge/compatibility-30A%20only-blue?style=for-the-badge)

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge)](https://paypal.me/jordandaleo)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_☕-F16061?style=for-the-badge&logo=ko-fi&logoColor=white&labelColor=grey)](https://ko-fi.com/jdaleo23)

# Hughes Power Watchdog - Smart Surge Protector <img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/PWD logo.png">

A custom Home Assistant integration for the [**Hughes Power Watchdog Gen 2 (WD_V6)**](https://www.powerwatchdog.com/surge-protectors) smart surge protectors. This integration uses Bluetooth Low Energy (BLE) to provide real-time monitoring of your RV's power status directly in Home Assistant.

## 🔌 Compatibility & Hardware
This integration is designed specifically for **Gen 2 (WD_V6)** Bluetooth models.

* **Tested:** 30 Amp Smart Surge Protector (WD_V6).
* **Not Currently Supported:** 50 Amp models. 

> [!IMPORTANT]
> Because 50A models monitor two separate power "legs" (L1 and L2), the data structure is different. If you have a 50A model and are comfortable sharing a Bluetooth packet dump, please open a **Discussion** so we can add support!

## 🚀 Features
* **Auto-Discovery:** Automatically finds nearby Power Watchdog devices via Home Assistant's Bluetooth integration.
* **Local Monitoring:** For fast updates without relying on the cloud.
* **Key Sensors:**
  * ⚡ **Voltage (V)**
  * 🔌 **Current (A)**
  * 🔋 **Power (W)**
  * 📈 **Energy Consumption (kWh)**
  * 〰️ **Frequency (Hz)**
* **Controls:**
  * 🔄 **Reset Total Energy Button:** Reset your accumulated kWh counter directly from Home Assistant.

## 🛠️ Requirements
* **Hardware:** Hughes Power Watchdog Gen 2 (Bluetooth version WD_V6).
* **Bluetooth:** Bluetooth adapter or proxy on your Home Assistant host.
* **Mobile App:** Ensure the Power Watchdog mobile app is **closed** when trying to connect, as the device only supports one active Bluetooth connection at a time.

## 📦 Installation

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

## ⚙️ Configuration
1. Navigate to **Settings > Devices & Services**.
2. Click **+ Add Integration**.
3. Search for **Hughes Power Watchdog**.
4. Select your device from the discovered list.

## ⚠️ Known Issues / Troubleshooting
* **"No Devices Found":** Ensure your Power Watchdog is powered on and that the official phone app is completely closed.
* **Connection Stability:** Bluetooth range can be limited; if you experience dropouts, consider using an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) closer to your RV.

## 💬 Support & Community
* **Found a bug?** Please [open an issue](https://github.com/jdaleo23/ha-power-watchdog/issues) and include your logs.
* **Have a question?** Join the [Discussions](https://github.com/jdaleo23/ha-power-watchdog/discussions) to ask questions or share your dashboard setup.
* **Feature Requests:** Have an idea for a new sensor or feature? Let's talk about it in the Discussions tab!

## 📊 Dashboard Setup
Here is a sample layout for your 30A connection showing the 80% safety limits and available sensors:

<img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/safety_gauges.png" width="300">
<img src="https://raw.githubusercontent.com/jdaleo23/ha-power-watchdog/main/images/sensors.png" width="300">

## ❤️ Support the Project
This is my first integration. I appreciate your support in its development, if you find it useful to help keep your RV safe.
* [Donate with PayPal](https://paypal.me/jordandaleo)
* [Buy Me A Coffee](https://ko-fi.com/jdaleo23)
