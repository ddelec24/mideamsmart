# Midea MSmart plugin

> **Plugin under development**: this documentation describes the current state of the plugin and will be completed with each release.

## Overview

The **Midea MSmart** plugin provides **local** control of Midea air conditioners and dehumidifiers, and those of related brands (Comfee, Inventor, Qlima…) compatible with the **MSmartHome** app.

The MSmartHome account is only used to:

- list the appliances linked to the account;
- retrieve, once, the authentication keys (*token* and *key*) of recent appliances (V3 protocol).

After that, all commands and state readings go directly through the local network, without the Midea cloud.

A schedule is built into the plugin, with profiles shared by all the appliances (for example *Normal* and *Holidays*).

Supported appliances:

| Type | Appliance |
|---|---|
| `0xAC` | Air conditioner (split, portable, PortaSplit…) |
| `0xCC` | Commercial air conditioner |
| `0xA1` | Dehumidifier |

## Prerequisites

- Jeedom 4.5 or later, on Debian 12 or 13.
- The appliances and Jeedom must be on the **same local network** (same subnet) for discovery to work.
- An **MSmartHome** account with the appliances **paired directly** to it. An appliance only *shared* from another account does not allow its keys to be retrieved.

> **Tip**
>
> Preferably use a password made only of letters and digits.
> After several failed logins, the Midea cloud temporarily blocks the account, for a few minutes up to 24 hours (errors `7610` or `65027`). In that case, wait before trying again.

## Plugin configuration

After installation, enable the plugin and start the dependency installation. The plugin installs its own Python environment, isolated from the system.

### Dependencies

The dependency installation, started from the plugin configuration page, installs only inside the plugin folder:

- a standalone **Python 3.13**, downloaded with the [uv](https://github.com/astral-sh/uv) tool, independently of the system Python version;
- a virtual environment (`resources/python_venv`) holding the plugin libraries, in pinned versions checked by hash.

The installation takes a few minutes and uses about 130 MB. On a 32-bit system (Raspberry Pi on `armhf`), a compiler is also installed and the operation takes longer, because one library has to be compiled there.

After a plugin update that changes these versions, the dependencies go back to the *NOK* state: simply relaunch their installation. They are not included in Jeedom backups; after a restore, relaunch their installation.

### Settings

![Plugin configuration](../images/plugin_config.png)

- **MSmartHome account**
  - **Login (email)** and **Password** of the MSmartHome account.
- **Local network**
  - **Broadcast address**: broadcast address(es) used to discover the appliances, separated by commas. Leave empty (default) to broadcast on every network interface of Jeedom. If the appliances are not found, enter the broadcast address of their network (for example `192.168.1.255`).
  - **Default polling interval**: delay in seconds between two readings of the appliance state (30 s by default, 10 s minimum).
  - **Connection lifetime**: the air conditioners are reconnected after this delay (90 s by default). Some appliances close the connection themselves after a while, which causes errors and drops: a value below that delay avoids them. 0 = connection kept indefinitely.
- **Daemon**
  - **Daemon port**: local port used by the daemon (55114 by default). Only change it in case of conflict with another plugin.

### Daemon

The daemon handles the local communication with the appliances. Once the dependencies are installed, it starts automatically (automatic management enabled), or with the **(Re)Start** button of the plugin configuration page.

- It only listens on the Jeedom machine (`127.0.0.1`), on the port set above.
- It **never** connects to the Midea cloud when it starts, which avoids account blocking.
- Its messages are in the `mideamsmart_daemon` log, those of the dependency installation in `mideamsmart_update`. Set the plugin log level to *Debug* to get the details of the exchanges. The plugin masks passwords, *token* and *key* in its messages.

## Adding appliances

On the plugin page, the **Synchronize** button (the daemon must be running):

1. looks for the appliances on the local network;
2. if an MSmartHome account is set, logs in and retrieves the list of appliances of the account;
3. for each V3 appliance whose keys are not known yet, retrieves the *token* and *key* from the cloud, then **checks them directly with the appliance** before saving them;
4. creates the new equipments, or updates the IP address, port and protocol of the existing ones. Names and existing keys are never changed.

A message summarizes the operation and reports the appliances whose keys could not be obtained. Appliances of an unsupported type are ignored. Without an MSmartHome account, only the local search is done.

![Plugin page](../images/plugin_devices.png)

The **Add** button creates an equipment manually, for example for an appliance on another subnet. You then have to enter the identifier, the IP address and, for a V3 appliance, the *token* and *key* yourself.

## Equipment

![Equipment](../images/device_config.png)

- **Midea appliance**
  - **Appliance type**: air conditioner, commercial air conditioner or dehumidifier.
  - **Appliance identifier**: Midea identifier, filled in automatically during synchronization.
- **Local connection**
  - **IP address** and **Port** (6444 by default).
  - **Protocol version**: V3 for most recent appliances, V2 for older ones.
  - **Token** and **Key**: authentication keys of V3 appliances, retrieved automatically.
  - **Retrieve token/key from the cloud**: asks the cloud again for the keys of this appliance and checks them, for example after a reset of the Wi-Fi module. Save the equipment before using it.
- **Options**
  - **Polling interval**: leave empty to use the value from the plugin configuration.
  - **Connection lifetime** (air conditioners): leave empty to use the value from the plugin configuration.
  - **Confirmation beep**: the appliance beeps on each command received.
  - **Setpoint step** (air conditioners): 1 °C or 0.5 °C.
  - **Power consumption** (air conditioners): creates the power and consumption commands. If the values are inconsistent, change the **format** (BCD or binary) or the **scale factor**.
- **Information**
  - Serial number and model of the appliance, read-only.
  - **Capabilities**: *Received from the appliance*, or *Default ones* if the appliance has not sent them yet. In that case they are requested again automatically, and the commands are adjusted as soon as they are received.

> **Important**
>
> Keep the *token* and *key* of your V3 appliances in a safe place. They let you keep controlling the appliances even if the Midea cloud becomes unavailable.

## Commands

![Air conditioner and dehumidifier widgets](../images/dashboard_ac.png) ![](../images/dashboard_a1.png)

![Commands tab](../images/device_commands.png)

Commands are created automatically **according to the capabilities reported by each appliance**, as soon as it answers for the first time. If the appliance does not return its capabilities, default ones are used and the request is repeated after 30 seconds, then at growing intervals up to 10 minutes. When they are received, the commands are adjusted automatically.

Text info commands hold a **stable code**, independent of the language (for example `cool`): use these codes in your scenarios. The related action commands offer translated labels. Infos already displayed by a linked action are hidden by default.

The **Update commands** button of the *Commands* tab adds the missing commands, removes those of the features the appliance no longer reports, then reads its capabilities again. The names and settings of your existing commands are kept.

| Logical ID | Appliances | Content |
|---|---|---|
| `power`, `on`, `off` | AC, CC, A1 | State (0/1), turn on, turn off |
| `mode`, `setMode` | AC, CC | Mode: `auto`, `cool`, `dry`, `smart_dry`, `heat`, `fan_only` (CC: `fan`). Choosing a mode turns the appliance on |
| `targetTemperature`, `setTargetTemperature` | AC, CC | Setpoint in °C, with the limits of the appliance and the step chosen in the equipment |
| `indoorTemperature`, `outdoorTemperature` | AC, CC | Indoor and outdoor temperatures |
| `fanSpeed`, `setFanSpeed` | AC, CC | Fan: `auto`, `silent`, `low`, `medium`, `high`, `max`, `custom` (CC: `l1` to `l7`, `auto`) |
| `fanSpeedPercent`, `setFanSpeedPercent` | AC | Free speed from 1 to 100 %, if the appliance supports it |
| `swingMode`, `setSwingMode` | AC, CC | Swing: `off`, `vertical`, `horizontal`, `both` |
| `horizontalSwingAngle`, `verticalSwingAngle` + `set…` | AC, CC | Louver position: `off`/`close`, `pos_1` to `pos_5`, `auto` |
| `preset`, `setPreset` | AC, CC | Exclusive preset: `none`, `sleep`, `freeze_protection`, `eco`, `ieco`, `turbo` (CC: `none`, `eco`, `silent`, `sleep`) |
| `breezeMode`, `setBreezeMode` | AC | Breeze mode: `off`, `breeze_away`, `breeze_mild`, `breezeless` |
| `indoorHumidity`, `targetHumidity`, `setTargetHumidity` | AC, CC | Indoor humidity and humidity setpoint (%) |
| `displayOn`, `toggleDisplay` | AC | Display state and toggle |
| `purifier`, `purifierOn`, `purifierOff` / `purifierMode`, `setPurifierMode` | AC / CC | Purifier (AC: on/off; CC: `off`, `on`, `auto`) |
| `flash`, `outSilent`, `cascadeMode`, `freshAirFanSpeed`, `rateSelect`, `auxMode` + actions | AC (CC : `auxMode`) | Advanced features, depending on the model |
| `selfCleanActive`, `startSelfClean`, `filterAlert`, `defrostActive`, `errorCode` | AC | Self-cleaning, filter alert, defrost (only if the appliance reports it), error code |
| `realTimePower`, `currentEnergy`, `totalEnergy` | AC | Power (W) and consumptions (kWh), if the *Power consumption* option is checked |
| `mode`, `setMode` | A1 | Mode: `manual`, `continuous`, `auto`, `clothes_dry`, `shoes_dry`, `silent`. Choosing a mode turns the appliance on |
| `fanSpeed`, `setFanSpeed` | A1 | Fan: `lowest`, `low`, `medium`, `high`, `auto` |
| `currentHumidity`, `currentTemperature`, `targetHumidity`, `setTargetHumidity` | A1 | Room humidity and temperature, humidity setpoint from 35 to 85 % |
| `tankLevel`, `tankFull`, `waterLevelSet`, `setWaterLevelSet` | A1 | Tank level (%), tank full, tank threshold (`25`, `50`, `75`, `100`) |
| `swing`, `childLock`, `anion`, `pump` + `…On`, `…Off` | A1 | Swing, child lock, ionizer, pump (if the appliance has one) |
| `filterCleaningReminder`, `resetFilter` | A1 | Filter cleaning reminder and its reset |
| `online`, `refresh` | AC, CC, A1 | Appliance reachable (0/1) and immediate refresh |
| `scheduleEnabled`, `scheduleOn`, `scheduleOff` | AC, CC, A1 | Schedule followed (0/1), follow and suspend the schedule of the appliance |
| `profile`, `setProfile` | Schedule | Name of the active profile and choice of the profile (identifier or name) |

## Schedule

The plugin can control your appliances on a timetable, for example with one program for school weeks and another for the holidays. Everything happens in Jeedom, locally. The programs of the MSmartHome app cannot be reached from the local network: disable them to avoid conflicts.

### Shared profiles

![Schedule profiles](../images/scheduler.png)

The **Schedule** tile of the plugin page opens the *Schedule* equipment, created automatically. It holds the **profiles**, shared by all the appliances (*Normal* and *Holidays* by default):

- add, rename or delete profiles, then save;
- choose the **active profile** here, or with the *Choose the profile* action command (`setProfile`), for example in a scenario run at the start and at the end of the holidays. The command also accepts the profile name;
- the *Profile* info command (`profile`) gives the name of the active profile;
- disabling the *Schedule* equipment suspends the schedule of every appliance.

### Slots of each appliance

![Schedule tab](../images/device_schedule.png)

The **Schedule** tab of each appliance holds its slots. A slot has:

- a profile, days and a time;
- an action: **Turn on** or **Turn off**;
- for *Turn on*, optional settings: mode, setpoint, fan speed and preset (for example *Sleep*) for an air conditioner; mode, humidity and fan speed for a dehumidifier. An empty setting is not changed, and choosing a mode turns the appliance on.

Only the slots of the active profile apply. The **Display** list filters the table by profile, and a new slot is added in the displayed profile.

Options of the appliance:

- **Follow the schedule**: the appliance applies its slots. The *Follow the schedule* (`scheduleOn`) and *Suspend the schedule* (`scheduleOff`) commands do the same from a scenario, and the *Schedule followed* info (`scheduleEnabled`) gives the state;
- **Catch-up** (enabled by default): when the profile changes, when the schedule is resumed or when Jeedom restarts, the last past slot is applied at once instead of waiting for the next one. For example, switching to *Holidays* at 10 am puts the air conditioner in the state of the 8 am slot of the *Holidays* profile.

Good to know:

- the slots are checked every minute by the *cron* task of the plugin, which must stay enabled in the plugin configuration;
- a manual setting (remote control, widget, scenario) stays until the next slot;
- adding or changing a slot applies nothing at once: the next slot is applied at its time.

Example for an air conditioner, during school weeks and holidays:

| Profile | Days | Time | Action |
|---|---|---|---|
| Normal | Mo to Fr | 07:00 | Turn on, Heat, 21 °C |
| Normal | Mo to Fr | 08:00 | Turn on, 18 °C |
| Normal | Mo to Fr | 16:30 | Turn on, Heat, 21 °C |
| Normal | Mo to Fr | 20:30 | Turn on, 19 °C, Sleep preset |
| Holidays | Mo to Su | 08:00 | Turn on, Heat, 20 °C |
| Holidays | Mo to Su | 21:00 | Turn off |

## Diagnostic and reliability

![Diagnostic](../images/device_diagnostic.png)

- **Diagnostic** (button at the top of the equipment page): shows the configuration seen by Jeedom and the state seen by the daemon (connection, last answer, last error, raw capabilities and values of the appliance). The **Copy for the forum** button copies this summary, without password, *token* or *key*, ready to paste in a help request on the [Jeedom forum](https://community.jeedom.com).
- **Unreachable appliance**: the `online` command goes to 0 and the equipment is reported in *timeout* in Jeedom. Polling is gradually spaced out, down to once every 5 minutes, then goes back to its normal rate as soon as the appliance answers.
- **IP address change**: if an appliance has not answered for 5 minutes, the daemon looks for it on the local network (at most once every 10 minutes, without the cloud). If it finds it at another address, the IP address of the equipment is updated automatically. Reserving the address of your appliances in your router is still recommended.
- **MSmartHome account protection**: a cloud lock (codes `7610`, `65027`) or a refused password is remembered, even after a daemon restart. During a lock, the synchronization is limited to the local network and the keys retrieval is refused. A refused password is not tried again until it is changed.
- Jeedom **Health page**: shows the number of reachable appliances and the state of the MSmartHome account.

## Troubleshooting

| Message | Solution |
|---|---|
| *Network error … Transport is closing or closed* (warning) | The appliance closed the connection: the plugin reconnects and sends the request again at once. If this message is frequent, lower the **connection lifetime** (for example 60 s). |
| *Payload … failed CRC and checksum* (warning) | Invalid frame ignored by the library, often linked to connection drops: same solution as above. |
| Extra commands, or different commands between identical appliances | The capabilities were not received (*Capabilities* indicator of the equipment): they are requested again automatically. You can also click **Update commands**. |
| *Wrong MSmartHome login or password* | Check the account in the plugin configuration. The plugin does not retry until the credentials change. |
| *The Midea cloud temporarily locked the account* | Too many logins (codes `7610`, `65027`). Wait for the indicated delay without starting another synchronization. |
| *appliance not paired directly with this account (shared?)* | In the MSmartHome app, pair the appliance with this account, not only through sharing. |
| *appliance not in the MSmartHome account* | The appliance is on the network but in another account: enter *token* and *key* manually, or pair it with this account. |
| *keys refused by the appliance* | Run **Retrieve token/key from the cloud** again; if the problem persists, pair the appliance again in the app. |
| *appliance not found on the local network* / *unreachable* | Check that the appliance is on and on the same network as Jeedom, or enter the **broadcast address** of its network. |

## Credits

The plugin relies on the open source libraries [msmart-ng](https://github.com/mill1000/midea-msmart) and [midea-local](https://github.com/midea-lan/midea-local).

The plugin is designed and directed by **ddelec24** (project conductor) and developed with **Claude** (Anthropic), co-author of the code and the documentation.
