# Midea MSmart plugin changelog

>**IMPORTANT**
>
>If there is no information about the update, it means that it only concerns documentation, translation or text updates.

# 19/10/2026

- Beta version 0.10.0
- New **schedule**: profiles shared by all the appliances (*Normal* and *Holidays* by default, editable), slots specific to each appliance (days, time, turn on or off, mode, setpoint, fan speed, preset or humidity)
- New *Schedule* equipment, opened by the tile of the same name: its *Choose the profile* command switches every appliance at once, for example from a holidays scenario
- Catch-up of the last past slot when the profile changes, when the schedule is resumed or when Jeedom restarts (can be disabled per appliance)
- New *Follow the schedule* and *Suspend the schedule* commands on each appliance
- Dehumidifier: several commands sent in a row (for example mode then humidity) no longer cancel each other

# 17/10/2026

- Beta version 0.9.2
- Fixed the diagnostic **Copy for the forum** button when Jeedom is opened over HTTP on the local network. If the browser refuses to copy, the text is shown, selected, so that it can be copied by hand
- Last communication date of the equipment updated at each successful poll, even when no value changes: the equipment is no longer wrongly reported by the Jeedom *maximum delay between two communications*
- *Defrosting* command created only if the appliance reports this information. To remove the one already created, click **Update commands**
- More information in the diagnostic: connection lifetime and state of the capabilities request
- Beta version 0.9.1
- Credits: plugin authors specified (ddelec24, conductor; Claude, co-author) in the documentation, the license and the plugin information
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
