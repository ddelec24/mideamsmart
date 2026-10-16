# Midea MSmart plugin

> **Plugin under development**: this documentation describes the current state of the plugin and will be completed with each release.

## Overview

The **Midea MSmart** plugin provides **local** control of Midea air conditioners and dehumidifiers, and those of related brands (Comfee, Inventor, Qlima…) compatible with the **MSmartHome** app.

The MSmartHome account is only used to:

- list the appliances linked to the account;
- retrieve, once, the authentication keys (*token* and *key*) of recent appliances (V3 protocol).

After that, all commands and state readings go directly through the local network, without the Midea cloud.

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
  - **Broadcast address**: broadcast address(es) used to discover the appliances, separated by commas. The default value `255.255.255.255` works in most cases. If the appliances are not found, enter the broadcast address of your network (for example `192.168.1.255`).
  - **Default polling interval**: delay in seconds between two readings of the appliance state (30 s by default, 10 s minimum).
- **Daemon**
  - **Daemon port**: local port used by the daemon (55114 by default). Only change it in case of conflict with another plugin.

## Adding appliances

On the plugin page, the **Synchronize** button retrieves the appliances of the MSmartHome account, looks for them on the local network and creates the matching equipments.

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
- **Options**
  - **Polling interval**: leave empty to use the value from the plugin configuration.
- **Information**
  - Serial number and model of the appliance, read-only.

> **Important**
>
> Keep the *token* and *key* of your V3 appliances in a safe place. They let you keep controlling the appliances even if the Midea cloud becomes unavailable.

## Commands

Commands are created automatically according to the capabilities reported by each appliance. Their detailed list will be added here as soon as they are available.

## Credits

The plugin relies on the open source libraries [msmart-ng](https://github.com/mill1000/midea-msmart) and [midea-local](https://github.com/midea-lan/midea-local).
