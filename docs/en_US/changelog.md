# Midea MSmart plugin changelog

>**IMPORTANT**
>
>If there is no information about the update, it means that it only concerns documentation, translation or text updates.

# 16/10/2026

- Plugin creation: base structure, configuration page and equipment page
- Dependency installation: standalone Python 3.13 (via uv) and a virtual environment dedicated to the plugin
- Python daemon (asyncio): start, clean stop, communication with Jeedom and transmission of the equipment list
- Appliance synchronization: MSmartHome account, local network search, creation and update of the equipments
- Retrieval of the token and key, checked with the appliance, and button to request them again
- Protection against the Midea account lock (codes 7610 and 65027)
- Automatic broadcast address by default (every network interface)
- Local control of air conditioners (AC) and commercial air conditioners (CC) with msmart-ng: state, periodic polling, offline appliance
- Commands created according to the capabilities of each appliance, with stable codes for scenarios and an update button
- Equipment options: beep, setpoint step, power consumption
- Local control of dehumidifiers (A1) with midea-local: mode, fan, humidity setpoint, tank, swing, ionizer, pump, child lock, filter
- Tank full and filter alerts displayed with a green or red icon
