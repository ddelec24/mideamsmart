# Midea MSmart plugin changelog

>**IMPORTANT**
>
>If there is no information about the update, it means that it only concerns documentation, translation or text updates.

# 17/10/2026

- Beta version 0.9.1
- New **Connection lifetime** option (90 s by default), remedy for the appliances that close the connection themselves (*Transport is closing or closed* and *failed CRC and checksum* errors)
- Request or command sent again once on a new connection when the appliance closes the connection, and appliance reported offline only after two failures in a row
- These library errors are logged as warnings
- Capabilities requested again quickly if the appliance did not send them, with automatic adjustment of the commands when they are received (extra commands, such as *Filter to clean*, on a single appliance)
- Capabilities state indicator on the equipment page
- Fix of an error when stopping a dehumidifier

# 16/10/2026

- First beta version (0.9.0), to be tested with real appliances: your feedback is welcome on the forum
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
- Diagnostic window per equipment, with copy of a summary without secrets for the forum
- Automatic search on the local network of the appliances that changed IP address
- Cloud locks and refused password remembered, even after a daemon restart
- Equipment reported in timeout when the appliance stops answering, Health page and forum information
