<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

require_once __DIR__ . '/../../../../core/php/core.inc.php';

class mideamsmart extends eqLogic {
	/*     * *************************Attributs****************************** */

	const DEFAULT_SOCKET_PORT = 55114;
	// Empty: broadcast on every private network interface of Jeedom
	const DEFAULT_BROADCAST_ADDRESS = '';
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
			case 'syncProgress':
				self::notifyUser(self::getSyncStepMessage(isset($_message['step']) ? $_message['step'] : ''), 'warning');
				break;
			case 'syncResult':
				self::applySyncResult($_message);
				break;
			case 'deviceCapabilities':
				$eqLogic = isset($_message['eqLogicId']) ? eqLogic::byId($_message['eqLogicId']) : null;
				if (is_object($eqLogic) && $eqLogic->getEqType_name() == __CLASS__ && isset($_message['capabilities']) && is_array($_message['capabilities'])) {
					$eqLogic->applyCapabilities($_message['capabilities']);
				}
				break;
			case 'commandError':
				$eqLogic = isset($_message['eqLogicId']) ? eqLogic::byId($_message['eqLogicId']) : null;
				$name = is_object($eqLogic) ? $eqLogic->getHumanName() : (isset($_message['eqLogicId']) ? $_message['eqLogicId'] : '');
				log::add(__CLASS__, 'warning', __('Commande non exécutée', __FILE__) . ' ' . $name . ' (' . (isset($_message['command']) ? $_message['command'] : '') . ') : ' . self::getCommandErrorMessage(isset($_message['reason']) ? $_message['reason'] : ''));
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

	/*     * *************************Commandes*************************** */

	private static function getCommandErrorMessage($_reason) {
		switch ($_reason) {
			case 'deviceNotRunning':
				return __('équipement inactif ou type non géré par le démon', __FILE__);
			case 'unsupportedValue':
				return __('valeur non supportée par l\'appareil', __FILE__);
			case 'invalidValue':
				return __('valeur invalide', __FILE__);
			case 'unknownCommand':
				return __('commande inconnue', __FILE__);
			case 'deviceOffline':
				return __('l\'appareil ne répond pas', __FILE__);
			case 'communicationError':
				return __('erreur de communication avec l\'appareil', __FILE__);
		}
		return $_reason;
	}

	/**
	 * Command definitions (core/config/commands.json), translated.
	 * @return array
	 */
	public static function getCommandDefinitions() {
		static $definitions = null;
		if ($definitions === null) {
			$path = __DIR__ . '/../config/commands.json';
			$definitions = json_decode(translate::exec(file_get_contents($path), 'plugins/' . __CLASS__ . '/core/config/commands.json'), true);
			if (!is_array($definitions)) {
				throw new Exception(__('Fichier de définition des commandes invalide', __FILE__) . ' : ' . json_last_error_msg());
			}
		}
		return $definitions;
	}

	/**
	 * Stores the capabilities reported by the daemon and creates the matching commands.
	 * @param array $_capabilities
	 */
	public function applyCapabilities($_capabilities) {
		$this->setConfiguration('capabilities', $_capabilities);
		// Direct save: the daemon configuration does not change
		$this->save(true);
		$this->createCommands(false);
	}

	/**
	 * Creates the missing commands and updates their lists and limits from the capabilities.
	 * Names, visibility and history settings of the existing commands are kept.
	 * @param bool $_removeObsolete Also removes the commands of the features the appliance no longer reports
	 * @return int Number of created commands
	 */
	public function createCommands($_removeObsolete = false) {
		$capabilities = $this->getConfiguration('capabilities', array());
		if (!is_array($capabilities) || !isset($capabilities['features'])) {
			return 0;
		}
		$deviceType = $this->getConfiguration('deviceType', '');
		$features = is_array($capabilities['features']) ? $capabilities['features'] : array();
		$definitions = self::getCommandDefinitions();
		$created = 0;
		$order = 0;
		// Infos first, so that the actions can be linked to them
		foreach (array('info', 'action') as $type) {
			foreach ($definitions['commands'] as $definition) {
				if ($definition['type'] != $type || !in_array($deviceType, $definition['types'])) {
					continue;
				}
				$order++;
				$cmd = $this->getCmd(null, $definition['logicalId']);
				if (isset($definition['feature']) && !in_array($definition['feature'], $features)) {
					if (is_object($cmd) && $_removeObsolete) {
						$cmd->remove();
					}
					continue;
				}
				if (!is_object($cmd)) {
					$cmd = new mideamsmartCmd();
					$cmd->setEqLogic_id($this->getId());
					$cmd->setLogicalId($definition['logicalId']);
					// The core removes ASCII apostrophes from names (cleanComponanteName): keep a typographic one
					$cmd->setName(str_replace("'", '’', $definition['name']));
					$cmd->setType($definition['type']);
					$cmd->setSubType($definition['subType']);
					$cmd->setOrder($order);
					$cmd->setIsVisible(isset($definition['isVisible']) ? $definition['isVisible'] : 1);
					$cmd->setIsHistorized(isset($definition['isHistorized']) ? $definition['isHistorized'] : 0);
					if (isset($definition['genericType'])) {
						$cmd->setGeneric_type($definition['genericType']);
					}
					if (isset($definition['unit'])) {
						$cmd->setUnite($definition['unit']);
					}
					if (isset($definition['icon'])) {
						$cmd->setDisplay('icon', $definition['icon']);
					}
					if (isset($definition['template'])) {
						$cmd->setTemplate('dashboard', $definition['template']);
						$cmd->setTemplate('mobile', $definition['template']);
					}
					if (isset($definition['displayParameters'])) {
						$cmd->setDisplay('parameters', $definition['displayParameters']);
					}
					$created++;
				}
				$this->updateCommandFromCapabilities($cmd, $definition, $capabilities, $definitions['enums']);
				$cmd->save();
			}
		}
		if ($created > 0) {
			log::add(__CLASS__, 'info', $this->getHumanName() . ' : ' . $created . ' ' . __('commande(s) créée(s)', __FILE__));
			// The daemon only sends the values that change: ask it for all of them for the new commands
			$deamon_info = self::deamon_info();
			if ($deamon_info['state'] == 'ok') {
				try {
					self::sendToDaemon(array('action' => 'resendValues', 'eqLogicId' => intval($this->getId())));
				} catch (Exception $e) {
					log::add(__CLASS__, 'warning', $e->getMessage());
				}
			}
		}
		return $created;
	}

	/**
	 * Recreates the commands from the known capabilities (button of the commands tab) and asks
	 * the daemon to read them again from the appliance.
	 * @return int Number of created commands
	 */
	public function updateCommands() {
		$capabilities = $this->getConfiguration('capabilities', array());
		if (!is_array($capabilities) || !isset($capabilities['features'])) {
			throw new Exception(__('Capacités de l\'appareil inconnues : il doit d\'abord avoir été joint par le démon', __FILE__));
		}
		$created = $this->createCommands(true);
		$deamon_info = self::deamon_info();
		if ($deamon_info['state'] == 'ok') {
			self::sendToDaemon(array('action' => 'refreshCapabilities', 'eqLogicId' => intval($this->getId())));
		}
		return $created;
	}

	private function updateCommandFromCapabilities($_cmd, $_definition, $_capabilities, $_enums) {
		$minValue = isset($_definition['minValue']) ? $_definition['minValue'] : null;
		$maxValue = isset($_definition['maxValue']) ? $_definition['maxValue'] : null;
		if (isset($_definition['minFrom']) && isset($_capabilities[$_definition['minFrom']])) {
			$minValue = $_capabilities[$_definition['minFrom']];
		}
		if (isset($_definition['maxFrom']) && isset($_capabilities[$_definition['maxFrom']])) {
			$maxValue = $_capabilities[$_definition['maxFrom']];
		}
		if ($minValue !== null) {
			$_cmd->setConfiguration('minValue', $minValue);
		}
		if ($maxValue !== null) {
			$_cmd->setConfiguration('maxValue', $maxValue);
		}
		$step = isset($_definition['step']) ? $_definition['step'] : null;
		if (isset($_definition['stepFrom']) && isset($_capabilities[$_definition['stepFrom']])) {
			$step = $_capabilities[$_definition['stepFrom']];
		}
		if ($step !== null) {
			$_cmd->setDisplay('parameters', array_merge((array) $_cmd->getDisplay('parameters', array()), array('step' => $step)));
		}
		if (isset($_definition['listEnum'])) {
			$enum = $_definition['listEnum'];
			$codes = (isset($_capabilities['enums'][$enum]) && is_array($_capabilities['enums'][$enum])) ? $_capabilities['enums'][$enum] : array();
			$values = array();
			foreach ($codes as $code) {
				$label = isset($_enums[$enum][$code]) ? $_enums[$enum][$code] : $code;
				$values[] = $code . '|' . $label;
			}
			$_cmd->setConfiguration('listValue', implode(';', $values));
		}
		if (isset($_definition['value'])) {
			$info = $this->getCmd('info', $_definition['value']);
			if (is_object($info)) {
				$_cmd->setValue($info->getId());
			}
		}
	}

	/*     * ********************Synchronisation************************** */

	/**
	 * Asks the daemon to synchronize the appliances (cloud account + local network).
	 * The result comes back asynchronously ('syncResult' on the callback).
	 * @param mideamsmart|null $_eqLogic Only this equipment (keys retrieval), or every appliance
	 */
	public static function syncDevices($_eqLogic = null) {
		$knownDevices = array();
		foreach (eqLogic::byType(__CLASS__) as $eqLogic) {
			if ($eqLogic->getLogicalId() === '') {
				continue;
			}
			$knownDevices[$eqLogic->getLogicalId()] = array(
				'hasKeys' => ($eqLogic->getConfiguration('token', '') !== '' && $eqLogic->getConfiguration('key', '') !== ''),
				'ipAddress' => $eqLogic->getConfiguration('ipAddress', ''),
				'port' => intval($eqLogic->getConfiguration('port', self::DEFAULT_DEVICE_PORT)),
			);
		}
		$message = array(
			'action' => 'syncDevices',
			'account' => config::byKey('cloudAccount', __CLASS__, ''),
			'password' => config::byKey('cloudPassword', __CLASS__, ''),
			'broadcastAddress' => config::byKey('broadcastAddress', __CLASS__, self::DEFAULT_BROADCAST_ADDRESS),
			'knownDevices' => $knownDevices,
		);
		if (is_object($_eqLogic)) {
			if ($_eqLogic->getLogicalId() === '') {
				throw new Exception(__('Renseignez l\'identifiant de l\'appareil avant de récupérer ses clés', __FILE__));
			}
			if ($message['account'] === '' || $message['password'] === '') {
				throw new Exception(__('Renseignez le compte MSmartHome dans la configuration du plugin', __FILE__));
			}
			$message['onlyDeviceId'] = $_eqLogic->getLogicalId();
			$message['forceKeys'] = true;
		}
		self::sendToDaemon($message);
	}

	private static function notifyUser($_message, $_level) {
		event::add('jeedom::alert', array('level' => $_level, 'page' => __CLASS__, 'message' => $_message, 'ttl' => 10000));
	}

	private static function getSyncStepMessage($_step) {
		switch ($_step) {
			case 'discovery':
				return __('Recherche des appareils sur le réseau local...', __FILE__);
			case 'cloudLogin':
				return __('Connexion au compte MSmartHome...', __FILE__);
			case 'cloudDevices':
				return __('Récupération des appareils du compte...', __FILE__);
			case 'keys':
				return __('Récupération et vérification des clés...', __FILE__);
		}
		return __('Synchronisation en cours...', __FILE__);
	}

	private static function getCloudErrorMessage($_error) {
		$reason = isset($_error['reason']) ? $_error['reason'] : '';
		$code = (isset($_error['cloudCode']) && $_error['cloudCode'] !== null) ? ' (' . __('code', __FILE__) . ' ' . $_error['cloudCode'] . ')' : '';
		$retryAfter = isset($_error['retryAfter']) ? intval($_error['retryAfter']) : 0;
		switch ($reason) {
			case 'invalidCredentials':
				return __('Identifiant ou mot de passe MSmartHome incorrect', __FILE__) . $code;
			case 'accountLocked':
				return __('Le cloud Midea a temporairement bloqué le compte, réessayez dans', __FILE__) . ' ' . max(1, ceil($retryAfter / 60)) . ' min' . $code;
			case 'tooFrequent':
				return __('Connexions au cloud trop rapprochées, réessayez dans', __FILE__) . ' ' . $retryAfter . ' s';
			case 'cloudUnreachable':
				return __('Le cloud Midea est injoignable, vérifiez l\'accès internet de Jeedom', __FILE__);
			case 'loginFailed':
				return __('Échec de la connexion au compte MSmartHome', __FILE__) . $code;
		}
		return __('Erreur du cloud Midea', __FILE__) . $code;
	}

	private static function getKeysStatusMessage($_status) {
		switch ($_status) {
			case 'invalid':
				return __('clés refusées par l\'appareil', __FILE__);
			case 'unreachable':
				return __('appareil injoignable pour vérifier les clés', __FILE__);
			case 'notOwned':
				return __('appareil non appairé directement sur ce compte (partagé ?)', __FILE__);
			case 'notInCloud':
				return __('appareil absent du compte MSmartHome, clés à saisir manuellement', __FILE__);
			case 'notOnLan':
				return __('appareil introuvable sur le réseau local', __FILE__);
			case 'noAccount':
				return __('aucun compte MSmartHome configuré pour récupérer les clés', __FILE__);
			case 'cloudError':
				return __('clés non récupérées (erreur du cloud)', __FILE__);
		}
		return '';
	}

	/**
	 * Creates or updates the equipments from the synchronization result sent by the daemon.
	 * @param array $_result
	 */
	public static function applySyncResult($_result) {
		if (isset($_result['failed']) && $_result['failed'] != '') {
			$message = ($_result['failed'] == 'alreadyRunning') ? __('Une synchronisation est déjà en cours', __FILE__) : __('La synchronisation a échoué, consultez le log', __FILE__) . ' ' . __CLASS__ . '_daemon';
			self::notifyUser($message, 'danger');
			event::add(__CLASS__ . '::syncDone', array('created' => 0));
			return;
		}
		$created = 0;
		$updated = 0;
		$unsupported = 0;
		$warnings = array();
		$devices = (isset($_result['devices']) && is_array($_result['devices'])) ? $_result['devices'] : array();
		foreach ($devices as $device) {
			if (empty($device['supported'])) {
				$unsupported++;
				log::add(__CLASS__, 'info', __('Appareil ignoré, type non supporté', __FILE__) . ' : ' . $device['deviceId'] . ' (0x' . $device['deviceType'] . ')');
				continue;
			}
			$eqLogic = eqLogic::byLogicalId($device['deviceId'], __CLASS__);
			if (!is_object($eqLogic)) {
				$eqLogic = self::createFromSync($device);
				$created++;
			} else {
				$updated++;
			}
			$eqLogic->updateFromSync($device);
			$eqLogic->save();
			$statusMessage = self::getKeysStatusMessage(isset($device['keysStatus']) ? $device['keysStatus'] : '');
			if ($statusMessage !== '') {
				$warnings[] = htmlspecialchars($eqLogic->getName()) . ' : ' . $statusMessage;
			}
			log::add(__CLASS__, 'info', __('Appareil synchronisé', __FILE__) . ' : ' . $eqLogic->getHumanName() . ' (' . $device['deviceId'] . ', 0x' . $device['deviceType'] . ', ' . (isset($device['keysStatus']) ? $device['keysStatus'] : '') . ')');
		}
		foreach ($warnings as $warning) {
			log::add(__CLASS__, 'warning', $warning);
		}
		$summary = __('Synchronisation terminée', __FILE__) . ' : ' . $created . ' ' . __('créé(s)', __FILE__) . ', ' . $updated . ' ' . __('mis à jour', __FILE__);
		if ($unsupported > 0) {
			$summary .= ', ' . $unsupported . ' ' . __('non supporté(s)', __FILE__);
		}
		$level = 'success';
		if (isset($_result['cloudError']) && is_array($_result['cloudError'])) {
			$summary .= '. ' . self::getCloudErrorMessage($_result['cloudError']);
			$level = 'warning';
		}
		if (count($warnings) > 0) {
			$summary .= '<br>' . implode('<br>', $warnings);
			$level = 'warning';
		}
		self::notifyUser($summary, $level);
		// The page reloads when equipments were created: it shows the summary again afterwards
		event::add(__CLASS__ . '::syncDone', array('created' => $created, 'message' => $summary, 'level' => $level));
	}

	private static function createFromSync($_device) {
		$name = trim(isset($_device['name']) ? $_device['name'] : '');
		if ($name === '') {
			$name = 'Midea ' . self::getDeviceTypeName($_device['deviceType']);
		}
		$existingNames = array();
		foreach (eqLogic::byType(__CLASS__) as $eqLogic) {
			if ($eqLogic->getObject_id() == null) {
				$existingNames[] = $eqLogic->getName();
			}
		}
		if (in_array($name, $existingNames)) {
			$name .= ' ' . $_device['deviceId'];
		}
		$eqLogic = new self();
		$eqLogic->setEqType_name(__CLASS__);
		$eqLogic->setLogicalId($_device['deviceId']);
		$eqLogic->setName($name);
		$eqLogic->setIsEnable(1);
		$eqLogic->setIsVisible(1);
		$eqLogic->setCategory('heating', 1);
		return $eqLogic;
	}

	/**
	 * Applies the data found during a synchronization. Empty values never erase the configuration.
	 * @param array $_device
	 */
	public function updateFromSync($_device) {
		$this->setConfiguration('deviceType', $_device['deviceType']);
		foreach (array('serialNumber' => 'serialNumber', 'model' => 'model', 'ipAddress' => 'ipAddress') as $key => $configuration) {
			if (isset($_device[$key]) && $_device[$key] !== '') {
				$this->setConfiguration($configuration, $_device[$key]);
			}
		}
		if (!empty($_device['port'])) {
			$this->setConfiguration('port', intval($_device['port']));
		}
		if (!empty($_device['protocolVersion'])) {
			$this->setConfiguration('protocolVersion', intval($_device['protocolVersion']));
		}
		if (!empty($_device['token']) && !empty($_device['key'])) {
			$this->setConfiguration('token', $_device['token']);
			$this->setConfiguration('key', $_device['key']);
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

		// Explicit defaults: an absent value would leave the checkboxes of the page in their previous state
		foreach (array('beep' => 1, 'energy' => 0, 'energyFormat' => 'bcd') as $key => $default) {
			if ($this->getConfiguration($key, '') === '') {
				$this->setConfiguration($key, $default);
			}
		}
		$this->setConfiguration('temperatureStep', (floatval($this->getConfiguration('temperatureStep', 1)) == 0.5) ? 0.5 : 1);
		$energyScale = str_replace(',', '.', trim($this->getConfiguration('energyScale', '')));
		if ($energyScale !== '' && (!is_numeric($energyScale) || floatval($energyScale) <= 0)) {
			throw new Exception(__('Facteur d\'échelle de consommation invalide', __FILE__) . ' : ' . $energyScale);
		}
		$this->setConfiguration('energyScale', ($energyScale === '') ? 1 : floatval($energyScale));
	}

	public function postSave() {
		// Options such as the temperature step change the commands display
		$this->createCommands(false);
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
			'beep' => intval($this->getConfiguration('beep', 1)),
			'temperatureStep' => floatval($this->getConfiguration('temperatureStep', 1)),
			'energy' => intval($this->getConfiguration('energy', 0)),
			'energyFormat' => $this->getConfiguration('energyFormat', 'bcd'),
			'energyScale' => floatval($this->getConfiguration('energyScale', 1)),
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
		if ($this->getType() != 'action') {
			return;
		}
		$eqLogic = $this->getEqLogic();
		$value = null;
		switch ($this->getSubType()) {
			case 'slider':
				$value = isset($_options['slider']) ? $_options['slider'] : null;
				break;
			case 'select':
				$value = isset($_options['select']) ? $_options['select'] : null;
				break;
		}
		if ($this->getSubType() != 'other' && ($value === null || $value === '')) {
			throw new Exception(__('Aucune valeur fournie pour la commande', __FILE__) . ' ' . $this->getHumanName());
		}
		mideamsmart::sendToDaemon(array(
			'action' => 'executeCommand',
			'eqLogicId' => intval($eqLogic->getId()),
			'command' => $this->getLogicalId(),
			'value' => $value,
		));
	}

	/*     * **********************Getteur Setteur*************************** */
}
