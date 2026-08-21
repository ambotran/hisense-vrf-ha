# Hisense VRF Home Assistant Integration

An unofficial Home Assistant custom integration for Hisense VRF (Variable Refrigerant Flow) commercial HVAC systems controlled via the **Hi-Mit II** gateway (HCCS-H64H2C1M).

> ⚠️ **Alpha / Experimental** — API endpoints are partially verified through reverse engineering. Expect iteration needed before full functionality.

---

## Background

This integration was developed by reverse engineering the Hi-Mit II Android APK (`com.hisensehitachi.oversea.himit2`) after finding that:

- The official ConnectLife integration does not support device type `045-000` (Hi-Therma II Inner / VRF indoor units)
- Both the community `connectlife-ha` and official `HomeAssistantPluginIntegration` skip this device as unsupported
- The Hi-Mit II app uses the `hijuconn.com` API backend, which is separate from ConnectLife

### What was reverse engineered

- **API backend**: `hijuconn.com` (separate from ConnectLife)
- **Authentication**: Token-based login via `auth-gateway.hijuconn.com`
- **Command structure**: `Cmd` objects with `cmdType`/`cmdValue` pairs sent to `shadow-gateway.hijuconn.com`
- **Request signing**: Parameters sorted alphabetically → concatenated → SHA256 → RSA encrypted with embedded public key → Base64 encoded
- **Device properties**: Boolean flag per mode (not single property) — unique to this VRF system

---

## Supported Hardware

| Component | Model |
|---|---|
| Gateway | Hisense Hi-Mit II (HCCS-H64H2C1M) |
| Wall controllers | HYXE-S01H (Hi-Therma II Inner) |
| Device type code | `045-000` |

Other Hisense VRF systems using the Hi-Mit app may work but are untested.

---

## Features

- **Power** on/off
- **HVAC modes**: Cool, Heat, Auto, Dry, Fan Only
- **Fan modes**: Low, Medium, High, Super High, Quiet, Auto
- **Temperature control**: 16–32°C setpoint
- **Current temperature**: Room sensor reading
- **Polling interval**: 30 seconds

---

## Installation

### Prerequisites

- Home Assistant 2024.1 or newer
- Hi-Mit II gateway connected to your network
- Active Hi-Mit II app account
- `pycryptodome` Python library

### Steps

1. Copy the `custom_components/hisense_vrf/` folder to your HA `/config/custom_components/` directory

2. Install the required Python dependency via SSH or terminal add-on:
   ```bash
   pip install pycryptodome --break-system-packages
   ```

3. Restart Home Assistant

4. Go to **Settings → Devices & Services → Add Integration** and search for **Hisense VRF**

5. Enter your Hi-Mit II app credentials (email + password)

6. Select your home and enter your **Wi-Fi ID** — this is the `wifiId` field from your Hi-Mit II device. You can find it by:
   - Using the `connectlife` Python library dump tool:
     ```bash
     pip install connectlife
     python -m connectlife.dump --username <email> --password <password>
     ```
   - The `wifiId` appears in the JSON output for each device

---

## Device Property Reference

Based on device dumps from live hardware, the `045-000` device type uses **boolean flags** per mode rather than a single property — this is a key difference from standard residential AC units:

### Power
| Property | Value | Meaning |
|---|---|---|
| `Y_K_Q_control` | `1` | On |
| `Y_K_Q_control` | `0` | Off |

### Mode (mutually exclusive)
| Property | Meaning |
|---|---|
| `modeRefrigeration` = `1` | Cool |
| `modeHeating` = `1` | Heat |
| `modeAutomatic` = `1` | Auto |
| `modeDeHumidification` = `1` | Dry |
| `modeSupplyAir` = `1` | Fan only |

### Fan Speed (mutually exclusive)
| Property | Meaning |
|---|---|
| `setLowWind` = `1` | Low |
| `setMediumWind` = `1` | Medium |
| `setHighWind` = `1` | High |
| `setSuperHighWind` = `1` | Super High |
| `setQuietSound` = `1` | Quiet |
| `isAutoAirVolume` = `1` | Auto |

### Temperature
| Property | Meaning |
|---|---|
| `setTemp` | Target setpoint (16–32°C, writable) |
| `suctionAirTemp` | Actual room temperature (read-only) |

---

## Known Limitations

- **API endpoint paths are estimated** — the base URLs are confirmed from the APK but specific paths (`/auth/login`, `/shadow/sendCommand` etc.) need verification against live traffic
- **No local control** — all commands go through Hisense cloud (`hijuconn.com`). The Hi-Mit II gateway has no local API
- **Password encryption** — the login flow may need adjustment depending on the exact password hashing the API expects
- **No scene/scheduling support** — only basic HVAC control implemented

---

## Contributing

If you have a Hisense VRF system and can help verify API endpoints or test this integration, contributions are very welcome.

To capture live API traffic for debugging, use mitmproxy with the Android APK in an emulator (the iOS app uses certificate pinning and blocks interception):

```bash
brew install mitmproxy android-studio
# Set up emulator, install APK, route traffic through mitmproxy
```

### Open Issues

- [ ] Verify exact API endpoint paths against live traffic
- [ ] Confirm login/password encryption method
- [ ] Add swing/louver control (`windFeflectorPosition_1`)
- [ ] Add energy monitoring entities
- [ ] Test token refresh flow
- [ ] Support multiple Hi-Mit II gateways

---

## Related Projects

- [connectlife-ha](https://github.com/oyvindwe/connectlife-ha) — Community ConnectLife integration (does not support `045-000`)
- [HomeAssistantPluginIntegration](https://github.com/Connectlife-LLC/HomeAssistantPluginIntegration) — Official ConnectLife integration (does not support `045-000`)

---

## Disclaimer

This integration is not affiliated with or endorsed by Hisense or Qingdao Hisense Hitachi Air-conditioning Systems Co., Ltd. Use at your own risk. The reverse engineering was performed on a legally obtained copy of the Hi-Mit II app for the purpose of home automation interoperability.
