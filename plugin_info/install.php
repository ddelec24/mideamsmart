<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

require_once dirname(__FILE__) . '/../../../core/php/core.inc.php';

function mideamsmart_install() {
	mideamsmart_setDefaultConfig();
	mideamsmart::getScheduler(true);
}

function mideamsmart_update() {
	mideamsmart_setDefaultConfig();
	mideamsmart::getScheduler(true);
}

function mideamsmart_remove() {
}

function mideamsmart_setDefaultConfig() {
	$defaults = array(
		'socketport' => mideamsmart::DEFAULT_SOCKET_PORT,
		'broadcastAddress' => mideamsmart::DEFAULT_BROADCAST_ADDRESS,
		'defaultPollingInterval' => mideamsmart::DEFAULT_POLLING_INTERVAL,
		'connectionLifetime' => mideamsmart::DEFAULT_CONNECTION_LIFETIME,
	);
	foreach ($defaults as $key => $value) {
		if (config::byKey($key, 'mideamsmart', '') === '') {
			config::save($key, $value, 'mideamsmart');
		}
	}
}
