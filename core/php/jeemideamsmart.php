<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 *
 * Callback endpoint used by the daemon to push data to Jeedom.
 */

try {
	require_once dirname(__FILE__) . '/../../../../core/php/core.inc.php';

	if (!jeedom::apiAccess(init('apikey'), 'mideamsmart')) {
		echo __('Vous n\'êtes pas autorisé à effectuer cette action', __FILE__);
		die();
	}
	if (init('test') != '') {
		echo 'OK';
		die();
	}

	$result = json_decode(file_get_contents('php://input'), true);
	if (!is_array($result)) {
		die();
	}

	mideamsmart::handleDaemonMessage($result);
} catch (Exception $e) {
	log::add('mideamsmart', 'error', displayException($e));
}
