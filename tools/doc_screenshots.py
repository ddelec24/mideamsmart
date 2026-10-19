"""Screenshots of the plugin pages for the documentation (docs/images), on the dev Jeedom instance.

Runs in the official Playwright image, in the network of the Jeedom container (dev-env):

  docker run --rm --network container:jeedom-dev --env-file ../dev-env/.env \\
    -v "$PWD":/work mcr.microsoft.com/playwright/python:v1.48.0-noble \\
    sh -c "pip install -q playwright==1.48.0 && python3 /work/tools/doc_screenshots.py /work/docs/images <ac eqLogic id> <AC object id> <A1 object id>"

JEEDOM_ADMIN_USER / JEEDOM_ADMIN_PASSWORD come from dev-env/.env. Expected data: an AC equipment and
an A1 equipment, each in its own object, online through the fake appliances (tools/fake_device.py),
and the light theme (core config theme_changeAccordingTime = 0). For the configuration capture, set
an example account (e.g. mon.compte@exemple.fr), never a real one. For the schedule captures, the AC
equipment has a few slots in two profiles (e.g. Normal and Vacances).

ONLY=name1.png,name2.png (environment) saves only these captures.
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1'
OUT = sys.argv[1]
AC_ID = sys.argv[2]
SALON_ID = sys.argv[3]
BUANDERIE_ID = sys.argv[4]


ONLY = [name for name in os.environ.get('ONLY', '').split(',') if name]


def shot(page, name, **kwargs):
    if ONLY and name not in ONLY:
        return
    path = os.path.join(OUT, name)
    page.screenshot(path=path, **kwargs)
    print('saved', path)


with sync_playwright() as p:
    # French browser: 24 h time inputs
    browser = p.chromium.launch(args=['--lang=fr-FR'])
    page = browser.new_page(viewport={'width': 1280, 'height': 860}, locale='fr-FR')
    page.goto(BASE + '/index.php')
    page.fill('#in_login_username', os.environ['JEEDOM_ADMIN_USER'])
    page.fill('#in_login_password', os.environ['JEEDOM_ADMIN_PASSWORD'])
    page.press('#in_login_password', 'Enter')
    page.wait_for_url(lambda url: 'p=' in url and 'connection' not in url, timeout=20000)
    page.wait_for_load_state('load')

    # Plugin configuration (the page events keep a connection open: never wait for networkidle)
    page.set_viewport_size({'width': 1280, 'height': 1180})
    page.goto(BASE + '/index.php?v=d&p=plugin&id=mideamsmart')
    page.wait_for_load_state('load')
    page.wait_for_timeout(1500)
    shot(page, 'plugin_config.png')

    # Plugin page (list of the appliances)
    page.set_viewport_size({'width': 1280, 'height': 860})
    page.goto(BASE + '/index.php?v=d&m=mideamsmart&p=mideamsmart')
    page.wait_for_load_state('load')
    page.wait_for_timeout(1000)
    if page.get_attribute('#bt_pluginDisplayAsTable', 'data-state') == '1':
        page.click('#bt_pluginDisplayAsTable')
        page.wait_for_timeout(800)
    shot(page, 'plugin_devices.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 470})

    # Equipment page
    page.set_viewport_size({'width': 1280, 'height': 1180})
    page.goto(BASE + f'/index.php?v=d&m=mideamsmart&p=mideamsmart&id={AC_ID}')
    page.wait_for_load_state('load')
    page.wait_for_timeout(1500)
    shot(page, 'device_config.png')
    page.set_viewport_size({'width': 1280, 'height': 860})

    # Commands tab
    page.click('a[href="#commandtab"]')
    page.wait_for_timeout(1000)
    shot(page, 'device_commands.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 640})

    # Schedule tab
    page.click('a[href="#scheduletab"]')
    page.wait_for_selector('#table_mideamsmartSlots tr.mideamsmartSlot')
    page.wait_for_timeout(800)
    shot(page, 'device_schedule.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 560})

    # Schedule equipment (shared profiles)
    page.goto(BASE + '/index.php?v=d&m=mideamsmart&p=mideamsmart')
    page.wait_for_load_state('load')
    page.wait_for_timeout(1000)
    page.click('#bt_mideamsmartScheduler')
    page.wait_for_selector('tr.mideamsmartProfile')
    page.wait_for_timeout(800)
    shot(page, 'scheduler.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 480})

    # Diagnostic window
    page.goto(BASE + f'/index.php?v=d&m=mideamsmart&p=mideamsmart&id={AC_ID}')
    page.wait_for_load_state('load')
    page.wait_for_timeout(1500)
    page.click('#bt_mideamsmartDiagnostic')
    page.wait_for_function("document.getElementById('pre_mideamsmartDiagnosticDaemon') && document.getElementById('pre_mideamsmartDiagnosticDaemon').textContent.includes('driver')", timeout=20000)
    page.wait_for_timeout(500)
    shot(page, 'device_diagnostic.png')

    # Dashboard widgets, one object at a time
    for object_id, name in ((SALON_ID, 'dashboard_ac.png'), (BUANDERIE_ID, 'dashboard_a1.png')):
        page.goto(BASE + f'/index.php?v=d&p=dashboard&object_id={object_id}')
        page.wait_for_load_state('load')
        page.wait_for_timeout(2500)
        widget = page.locator('.eqLogic-widget').first
        box = widget.bounding_box()
        shot(page, name, clip={'x': box['x'] - 6, 'y': box['y'] - 6, 'width': box['width'] + 12, 'height': box['height'] + 12})
    browser.close()
