<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

require_once __DIR__ . '/../../../../core/php/core.inc.php';

class mideamsmart extends eqLogic {
	/*     * *************************Attributs****************************** */

	const DEFAULT_SOCKET_PORT = 55114;
	const DEFAULT_BROADCAST_ADDRESS = '255.255.255.255';
	const DEFAULT_POLLING_INTERVAL = 30;
	const MIN_POLLING_INTERVAL = 10;
	const DEFAULT_DEVICE_PORT = 6444;

	const DEVICE_TYPE_AC = 'AC';
	const DEVICE_TYPE_CC = 'CC';
	const DEVICE_TYPE_A1 = 'A1';

	public static $_encryptConfigKey = array('cloudAccount', 'cloudPassword');

	/*     * ***********************Methode static*************************** */

	/**
	 * Device types handled by the plugin, indexed by Midea hexadecimal type.
	 * @return array
	 */
	public static function getSupportedDeviceTypes() {
		return array(
			self::DEVICE_TYPE_AC => __('Climatiseur', __FILE__),
			self::DEVICE_TYPE_CC => __('Climatiseur commercial', __FILE__),
			self::DEVICE_TYPE_A1 => __('Déshumidificateur', __FILE__),
		);
	}

	public static function isSupportedDeviceType($_deviceType) {
		return array_key_exists(strtoupper($_deviceType), self::getSupportedDeviceTypes());
	}

	public static function getDeviceTypeName($_deviceType) {
		$deviceTypes = self::getSupportedDeviceTypes();
		$deviceType = strtoupper($_deviceType);
		if (isset($deviceTypes[$deviceType])) {
			return $deviceTypes[$deviceType];
		}
		return __('Type non supporté', __FILE__) . ' (0x' . $deviceType . ')';
	}

	public static function preConfig_socketport($_value) {
		if (trim($_value) === '') {
			return self::DEFAULT_SOCKET_PORT;
		}
		$value = intval($_value);
		if ($value < 1024 || $value > 65535) {
			throw new Exception(__('Le port du démon doit être compris entre 1024 et 65535', __FILE__));
		}
		return $value;
	}

	public static function preConfig_defaultPollingInterval($_value) {
		if (trim($_value) === '') {
			return self::DEFAULT_POLLING_INTERVAL;
		}
		return self::checkPollingInterval($_value);
	}

	public static function preConfig_broadcastAddress($_value) {
		$addresses = array();
		foreach (explode(',', $_value) as $address) {
			$address = trim($address);
			if ($address === '') {
				continue;
			}
			if (filter_var($address, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) === false) {
				throw new Exception(__('Adresse de diffusion invalide', __FILE__) . ' : ' . $address);
			}
			$addresses[] = $address;
		}
		if (count($addresses) == 0) {
			return self::DEFAULT_BROADCAST_ADDRESS;
		}
		return implode(',', $addresses);
	}

	/*     * ***********************Dépendances*************************** */

	public static function getVenvPython() {
		return __DIR__ . '/../../resources/python_venv/bin/python3';
	}

	/**
	 * Fingerprint of the install script and of the lock file, written by the
	 * install script once the installation succeeded.
	 * @return string
	 */
	private static function getDependenciesFingerprint() {
		$resourcesDir = __DIR__ . '/../../resources';
		return hash('sha256', file_get_contents($resourcesDir . '/install_apt.sh') . file_get_contents($resourcesDir . '/requirements.lock'));
	}

	public static function dependancy_info() {
		$return = array();
		$return['log'] = __CLASS__ . '_update';
		$return['progress_file'] = jeedom::getTmpFolder(__CLASS__) . '/dependance';
		$return['state'] = 'nok';
		$markerFile = __DIR__ . '/../../resources/python_venv/.mideamsmart_dependencies';
		if (is_executable(self::getVenvPython()) && file_exists($markerFile) && trim(file_get_contents($markerFile)) === self::getDependenciesFingerprint()) {
			$return['state'] = 'ok';
		}
		return $return;
	}

	public static function dependancy_install() {
		log::remove(__CLASS__ . '_update');
		return array(
			'script' => __DIR__ . '/../../resources/install_#stype#.sh ' . jeedom::getTmpFolder(__CLASS__) . '/dependance',
			'log' => log::getPathToLog(__CLASS__ . '_update'),
		);
	}

	/**
	 * Folders excluded from the Jeedom backups (python_venv is already excluded by the core)
	 * @return array
	 */
	public static function backupExclude() {
		return array('resources/python_runtime');
	}

	private static function checkPollingInterval($_value) {
		$value = intval($_value);
		if ($value < self::MIN_POLLING_INTERVAL) {
			throw new Exception(__('L\'intervalle d\'interrogation doit être d\'au moins', __FILE__) . ' ' . self::MIN_POLLING_INTERVAL . ' s');
		}
		return $value;
	}

	/*     * *********************Méthodes d'instance************************* */

	public function preSave() {
		$deviceType = strtoupper(trim($this->getConfiguration('deviceType', '')));
		$this->setConfiguration('deviceType', $deviceType);

		$ipAddress = trim($this->getConfiguration('ipAddress', ''));
		if ($ipAddress !== '' && filter_var($ipAddress, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) === false) {
			throw new Exception(__('Adresse IP invalide', __FILE__) . ' : ' . $ipAddress);
		}
		$this->setConfiguration('ipAddress', $ipAddress);

		$port = trim($this->getConfiguration('port', ''));
		if ($port === '') {
			$port = self::DEFAULT_DEVICE_PORT;
		}
		$port = intval($port);
		if ($port < 1 || $port > 65535) {
			throw new Exception(__('Port de l\'appareil invalide', __FILE__) . ' : ' . $port);
		}
		$this->setConfiguration('port', $port);

		$pollingInterval = trim($this->getConfiguration('pollingInterval', ''));
		if ($pollingInterval !== '') {
			$this->setConfiguration('pollingInterval', self::checkPollingInterval($pollingInterval));
		}
	}

	public function decrypt() {
		$this->setConfiguration('token', utils::decrypt($this->getConfiguration('token')));
		$this->setConfiguration('key', utils::decrypt($this->getConfiguration('key')));
	}

	public function encrypt() {
		$this->setConfiguration('token', utils::encrypt($this->getConfiguration('token')));
		$this->setConfiguration('key', utils::encrypt($this->getConfiguration('key')));
	}

	public function getImage() {
		$customImage = $this->getCustomImage();
		if ($customImage !== null) {
			return $customImage;
		}
		$deviceType = strtolower($this->getConfiguration('deviceType', ''));
		$image = 'plugins/' . __CLASS__ . '/desktop/img/' . $deviceType . '.png';
		if ($deviceType !== '' && file_exists(__DIR__ . '/../../../../' . $image)) {
			return $image;
		}
		return parent::getImage();
	}

	public function getPollingInterval() {
		$pollingInterval = $this->getConfiguration('pollingInterval', '');
		if ($pollingInterval === '') {
			$pollingInterval = config::byKey('defaultPollingInterval', __CLASS__, self::DEFAULT_POLLING_INTERVAL);
		}
		return intval($pollingInterval);
	}

	/*     * **********************Getteur Setteur*************************** */
}

class mideamsmartCmd extends cmd {
	/*     * *************************Attributs****************************** */

	/*     * *********************Methode d'instance************************* */

	public function execute($_options = array()) {
	}

	/*     * **********************Getteur Setteur*************************** */
}
