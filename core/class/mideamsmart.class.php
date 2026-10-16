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
	const DAEMON_START_TIMEOUT = 30;
	const DAEMON_STOP_TIMEOUT = 5;

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

	/*     * ***************************Démon***************************** */

	private static function getDaemonPidFile() {
		return jeedom::getTmpFolder(__CLASS__) . '/deamon.pid';
	}

	private static function getDaemonPid() {
		$pidFile = self::getDaemonPidFile();
		if (!file_exists($pidFile)) {
			return 0;
		}
		return intval(trim(file_get_contents($pidFile)));
	}

	public static function deamon_info() {
		$return = array();
		$return['log'] = __CLASS__ . '_daemon';
		$return['state'] = 'nok';
		$pid = self::getDaemonPid();
		if ($pid > 0) {
			if (@posix_getsid($pid) !== false) {
				$return['state'] = 'ok';
			} else {
				@unlink(self::getDaemonPidFile());
			}
		}
		$return['launchable'] = 'ok';
		return $return;
	}

	public static function deamon_start() {
		self::deamon_stop();
		$deamon_info = self::deamon_info();
		if ($deamon_info['launchable'] != 'ok') {
			throw new Exception(__('Veuillez vérifier la configuration', __FILE__));
		}
		$cmd = escapeshellarg(self::getVenvPython()) . ' ' . escapeshellarg(realpath(__DIR__ . '/../../resources/mideamsmartd/mideamsmartd.py'));
		$cmd .= ' --loglevel ' . escapeshellarg(log::convertLogLevel(log::getLogLevel(__CLASS__)));
		$cmd .= ' --socketport ' . intval(config::byKey('socketport', __CLASS__, self::DEFAULT_SOCKET_PORT));
		$cmd .= ' --callback ' . escapeshellarg(network::getNetworkAccess('internal', 'proto:127.0.0.1:port:comp') . '/plugins/' . __CLASS__ . '/core/php/jee' . __CLASS__ . '.php');
		$cmd .= ' --apikey ' . escapeshellarg(jeedom::getApiKey(__CLASS__));
		$cmd .= ' --pid ' . escapeshellarg(self::getDaemonPidFile());
		log::add(__CLASS__, 'info', __('Lancement du démon', __FILE__));
		exec($cmd . ' >> ' . escapeshellarg(log::getPathToLog(__CLASS__ . '_daemon')) . ' 2>&1 &');
		for ($i = 0; $i < self::DAEMON_START_TIMEOUT; $i++) {
			sleep(1);
			$deamon_info = self::deamon_info();
			if ($deamon_info['state'] == 'ok') {
				message::removeAll(__CLASS__, 'unableStartDeamon');
				log::add(__CLASS__, 'info', __('Démon démarré', __FILE__));
				return true;
			}
		}
		log::add(__CLASS__, 'error', __('Impossible de lancer le démon, consultez le log', __FILE__) . ' ' . __CLASS__ . '_daemon', 'unableStartDeamon');
		return false;
	}

	public static function deamon_stop() {
		$pid = self::getDaemonPid();
		if ($pid > 0) {
			// SIGTERM first so that the daemon closes its connections properly
			system::kill($pid, false);
			for ($i = 0; $i < self::DAEMON_STOP_TIMEOUT * 2 && @posix_getsid($pid) !== false; $i++) {
				usleep(500000);
			}
		}
		system::kill('mideamsmartd.py');
		@unlink(self::getDaemonPidFile());
	}

	/**
	 * Sends a message (one JSON line) to the daemon socket.
	 * @param array $_params Message, with at least an 'action' key
	 */
	public static function sendToDaemon($_params) {
		$deamon_info = self::deamon_info();
		if ($deamon_info['state'] != 'ok') {
			throw new Exception(__('Le démon n\'est pas démarré', __FILE__));
		}
		$_params['apikey'] = jeedom::getApiKey(__CLASS__);
		$payload = json_encode($_params) . "\n";
		$port = intval(config::byKey('socketport', __CLASS__, self::DEFAULT_SOCKET_PORT));
		$socket = @stream_socket_client('tcp://127.0.0.1:' . $port, $errorCode, $errorMessage, 5);
		if ($socket === false) {
			throw new Exception(__('Impossible de contacter le démon', __FILE__) . ' : ' . $errorMessage . ' (' . $errorCode . ')');
		}
		$written = 0;
		$length = strlen($payload);
		while ($written < $length) {
			$result = fwrite($socket, substr($payload, $written));
			if ($result === false || $result === 0) {
				fclose($socket);
				throw new Exception(__('Erreur lors de l\'envoi au démon', __FILE__));
			}
			$written += $result;
		}
		fclose($socket);
	}

	/**
	 * Sends the configuration of every enabled equipment (when the daemon starts).
	 */
	public static function sendDevicesToDaemon() {
		$devices = array();
		foreach (eqLogic::byType(__CLASS__, true) as $eqLogic) {
			$devices[] = $eqLogic->getDaemonConfig();
		}
		self::sendToDaemon(array('action' => 'setDevices', 'devices' => $devices));
	}

	public static function postConfig_defaultPollingInterval($_value) {
		self::notifyDaemonOfDevices();
	}

	private static function notifyDaemonOfDevices() {
		$deamon_info = self::deamon_info();
		if ($deamon_info['state'] != 'ok') {
			return;
		}
		try {
			self::sendDevicesToDaemon();
		} catch (Exception $e) {
			log::add(__CLASS__, 'warning', $e->getMessage());
		}
	}

	/**
	 * Handles a message posted by the daemon on the callback (core/php/jeemideamsmart.php).
	 * @param array $_message
	 */
	public static function handleDaemonMessage($_message) {
		$action = isset($_message['action']) ? $_message['action'] : '';
		switch ($action) {
			case 'daemonStarted':
				log::add(__CLASS__, 'debug', __('Démon prêt, envoi de la liste des équipements', __FILE__));
				self::sendDevicesToDaemon();
				break;
			case 'deviceValues':
				if (isset($_message['devices']) && is_array($_message['devices'])) {
					foreach ($_message['devices'] as $eqLogicId => $values) {
						$eqLogic = eqLogic::byId($eqLogicId);
						if (!is_object($eqLogic) || $eqLogic->getEqType_name() != __CLASS__ || !is_array($values)) {
							continue;
						}
						$eqLogic->updateValues($values);
					}
				}
				break;
			default:
				log::add(__CLASS__, 'debug', __('Message du démon non traité', __FILE__) . ' : ' . json_encode($_message));
		}
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

	public function postSave() {
		$deamon_info = self::deamon_info();
		if ($deamon_info['state'] != 'ok') {
			return;
		}
		try {
			if ($this->getIsEnable() == 1) {
				self::sendToDaemon(array('action' => 'updateDevice', 'device' => $this->getDaemonConfig()));
			} else {
				self::sendToDaemon(array('action' => 'removeDevice', 'eqLogicId' => intval($this->getId())));
			}
		} catch (Exception $e) {
			log::add(__CLASS__, 'warning', $e->getMessage());
		}
	}

	public function preRemove() {
		$deamon_info = self::deamon_info();
		if ($deamon_info['state'] != 'ok') {
			return;
		}
		try {
			self::sendToDaemon(array('action' => 'removeDevice', 'eqLogicId' => intval($this->getId())));
		} catch (Exception $e) {
			log::add(__CLASS__, 'warning', $e->getMessage());
		}
	}

	/**
	 * Equipment configuration as expected by the daemon (DeviceConfig.from_jeedom)
	 * @return array
	 */
	public function getDaemonConfig() {
		return array(
			'eqLogicId' => intval($this->getId()),
			'deviceId' => $this->getLogicalId(),
			'deviceType' => $this->getConfiguration('deviceType', ''),
			'name' => $this->getHumanName(),
			'ipAddress' => $this->getConfiguration('ipAddress', ''),
			'port' => intval($this->getConfiguration('port', self::DEFAULT_DEVICE_PORT)),
			'protocolVersion' => intval($this->getConfiguration('protocolVersion', 3)),
			'token' => $this->getConfiguration('token', ''),
			'key' => $this->getConfiguration('key', ''),
			'pollingInterval' => $this->getPollingInterval(),
		);
	}

	/**
	 * Updates the info commands from values sent by the daemon.
	 * @param array $_values Values indexed by command logicalId
	 */
	public function updateValues($_values) {
		foreach ($_values as $logicalId => $value) {
			$this->checkAndUpdateCmd($logicalId, $value);
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
