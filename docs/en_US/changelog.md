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
