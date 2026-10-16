<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

try {
	require_once dirname(__FILE__) . '/../../../../core/php/core.inc.php';
	include_file('core', 'authentification', 'php');

	if (!isConnect('admin')) {
		throw new Exception(__('401 - Accès non autorisé', __FILE__));
	}

	ajax::init();

	if (init('action') == 'syncDevices') {
		mideamsmart::syncDevices();
		ajax::success();
	}

	if (init('action') == 'fetchDeviceKeys') {
		$eqLogic = mideamsmart::byId(init('id'));
		if (!is_object($eqLogic) || $eqLogic->getEqType_name() != 'mideamsmart') {
			throw new Exception(__('Équipement introuvable', __FILE__) . ' : ' . init('id'));
		}
		mideamsmart::syncDevices($eqLogic);
		ajax::success();
	}

	if (init('action') == 'updateCommands') {
		$eqLogic = mideamsmart::byId(init('id'));
		if (!is_object($eqLogic) || $eqLogic->getEqType_name() != 'mideamsmart') {
			throw new Exception(__('Équipement introuvable', __FILE__) . ' : ' . init('id'));
		}
		ajax::success($eqLogic->updateCommands());
	}

	if (init('action') == 'requestDiagnostic' || init('action') == 'getDiagnostic') {
		$eqLogic = mideamsmart::byId(init('id'));
		if (!is_object($eqLogic) || $eqLogic->getEqType_name() != 'mideamsmart') {
			throw new Exception(__('Équipement introuvable', __FILE__) . ' : ' . init('id'));
		}
		if (init('action') == 'requestDiagnostic') {
			$eqLogic->requestDiagnostic();
			ajax::success();
		}
		ajax::success($eqLogic->getDiagnostic());
	}

	throw new Exception(__('Aucune méthode correspondante à', __FILE__) . ' : ' . init('action'));
} catch (Exception $e) {
	ajax::error(displayException($e), $e->getCode());
}
