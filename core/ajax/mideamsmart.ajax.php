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

	if (init('action') == 'getScheduleContext') {
		$scheduler = mideamsmart::getScheduler();
		$definitions = mideamsmart::getCommandDefinitions();
		ajax::success(array(
			'schedulerId' => is_object($scheduler) ? intval($scheduler->getId()) : null,
			'schedulerEnabled' => is_object($scheduler) ? intval($scheduler->getIsEnable()) : 0,
			'profiles' => is_object($scheduler) ? $scheduler->getProfiles() : array(),
			'activeProfile' => is_object($scheduler) ? (string) $scheduler->getConfiguration('activeProfile', '') : '',
			'enums' => $definitions['enums'],
		));
	}

	if (init('action') == 'openScheduler') {
		ajax::success(intval(mideamsmart::getScheduler(true)->getId()));
	}

	throw new Exception(__('Aucune méthode correspondante à', __FILE__) . ' : ' . init('action'));
} catch (Exception $e) {
	ajax::error(displayException($e), $e->getCode());
}
