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
	// Reconnection delay recommended by midea-ac-py for the appliances that close their connection (0 = never)
	const DEFAULT_CONNECTION_LIFETIME = 90;
	const MIN_CONNECTION_LIFETIME = 10;
	const DEFAULT_DEVICE_PORT = 6444;
	const DAEMON_START_TIMEOUT = 30;
	const DAEMON_STOP_TIMEOUT = 5;

	const DEVICE_TYPE_AC = 'AC';
	const DEVICE_TYPE_CC = 'CC';
	const DEVICE_TYPE_A1 = 'A1';

	// Equipment holding the shared schedule profiles (the appliances have a numeric Midea identifier)
	const SCHEDULER_LOGICAL_ID = 'scheduler';
	// A slot reached less than 5 minutes ago is applied even without catch-up (late cron)
	const SCHEDULE_FRESH_DELAY = 300;
	const SCHEDULE_LOOKBACK_DAYS = 7;

	public static $_encryptConfigKey = array('cloudAccount', 'cloudPassword');

	// Set by preSave for postSave: the schedule was resumed or edited by this save
	private $_scheduleResumed = false;
	private $_scheduleEdited = false;

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

	/**
	 * Midea appliances of the plugin: every equipment except the schedule one.
	 * @param bool $_onlyEnable
	 * @return mideamsmart[]
	 */
	public static function getDevices($_onlyEnable = false) {
		$devices = array();
		foreach (eqLogic::byType(__CLASS__, $_onlyEnable) as $eqLogic) {
			if (!$eqLogic->isScheduler()) {
				$devices[] = $eqLogic;
			}
		}
		return $devices;
	}

	public function isScheduler() {
		return $this->getLogicalId() === self::SCHEDULER_LOGICAL_ID;
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

	public static function preConfig_connectionLifetime($_value) {
		if (trim($_value) === '') {
			return self::DEFAULT_CONNECTION_LIFETIME;
		}
		return self::checkConnectionLifetime($_value);
	}

	public static function postConfig_connectionLifetime($_value) {
		self::notifyDaemonOfDevices();
	}

	private static function checkConnectionLifetime($_value) {
		$value = intval($_value);
		if ($value != 0 && ($value < self::MIN_CONNECTION_LIFETIME || $value > 3600)) {
			throw new Exception(__('La durée de vie des connexions doit être 0 ou comprise entre', __FILE__) . ' ' . self::MIN_CONNECTION_LIFETIME . ' ' . __('et', __FILE__) . ' 3600 s');
		}
		return $value;
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
		foreach (self::getDevices(true) as $eqLogic) {
			$devices[] = $eqLogic->getDaemonConfig();
		}
		self::sendToDaemon(array(
			'action' => 'setDevices',
			'devices' => $devices,
			'broadcastAddress' => config::byKey('broadcastAddress', __CLASS__, self::DEFAULT_BROADCAST_ADDRESS),
		));
	}

	public static function postConfig_defaultPollingInterval($_value) {
		self::notifyDaemonOfDevices();
	}

	public static function postConfig_broadcastAddress($_value) {
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
			case 'deviceAddressChanged':
				$eqLogic = isset($_message['eqLogicId']) ? eqLogic::byId($_message['eqLogicId']) : null;
				if (is_object($eqLogic) && $eqLogic->getEqType_name() == __CLASS__ && isset($_message['ipAddress'])) {
					log::add(__CLASS__, 'warning', $eqLogic->getHumanName() . ' : ' . __('appareil retrouvé à une nouvelle adresse', __FILE__) . ' ' . $_message['ipAddress'] . ' (' . __('ancienne', __FILE__) . ' : ' . $eqLogic->getConfiguration('ipAddress', '') . ')');
					$eqLogic->setConfiguration('ipAddress', $_message['ipAddress']);
					if (!empty($_message['port'])) {
						$eqLogic->setConfiguration('port', intval($_message['port']));
					}
					$eqLogic->save();
				}
				break;
			case 'deviceDiagnostic':
				if (isset($_message['eqLogicId'])) {
					cache::set(__CLASS__ . '::diagnostic::' . intval($_message['eqLogicId']), isset($_message['diagnostic']) ? $_message['diagnostic'] : array(), 120);
				}
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
		$previous = $this->getConfiguration('capabilities', array());
		$this->setConfiguration('capabilities', $_capabilities);
		// Direct save: the daemon configuration does not change
		$this->save(true);
		// First real capabilities after default ones (the appliance did not answer at first):
		// the commands created for the default capabilities may not apply to this appliance
		$wasComplete = is_array($previous) && !empty($previous['complete']);
		if (!empty($_capabilities['complete']) && !$wasComplete && is_array($previous) && isset($previous['features'])) {
			log::add(__CLASS__, 'info', $this->getHumanName() . ' : ' . __('capacités reçues de l\'appareil, commandes ajustées', __FILE__));
			$this->createCommands(true);
			return;
		}
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
		if ($_removeObsolete) {
			// Commands of another appliance type (type changed by hand)
			$typeLogicalIds = array();
			foreach ($definitions['commands'] as $definition) {
				if (in_array($deviceType, $definition['types'])) {
					$typeLogicalIds[] = $definition['logicalId'];
				}
			}
			foreach ($this->getCmd() as $cmd) {
				if (!in_array($cmd->getLogicalId(), $typeLogicalIds)) {
					$cmd->remove();
				}
			}
		}
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

	/*     * ******************Santé et diagnostic*********************** */

	public static function health() {
		$return = array();
		$deamon_info = self::deamon_info();
		$eqLogics = self::getDevices(true);
		$offline = array();
		foreach ($eqLogics as $eqLogic) {
			$online = $eqLogic->getCmd('info', 'online');
			if (is_object($online) && $online->execCmd() != 1) {
				$offline[] = $eqLogic->getHumanName();
			}
		}
		$return[] = array(
			'test' => __('Appareils joignables', __FILE__),
			'result' => (count($eqLogics) - count($offline)) . '/' . count($eqLogics),
			'advice' => (count($offline) > 0) ? __('Injoignables', __FILE__) . ' : ' . implode(', ', $offline) : '',
			'state' => ($deamon_info['state'] == 'ok' && count($offline) == 0),
		);
		$cloudBlock = self::getCloudBlockMessage(config::byKey('cloudAccount', __CLASS__, ''), config::byKey('cloudPassword', __CLASS__, ''));
		$return[] = array(
			'test' => __('Compte MSmartHome', __FILE__),
			'result' => ($cloudBlock !== '') ? $cloudBlock : ((config::byKey('cloudAccount', __CLASS__, '') === '') ? __('Non configuré', __FILE__) : __('OK', __FILE__)),
			'advice' => '',
			'state' => ($cloudBlock === ''),
		);
		return $return;
	}

	/**
	 * Information added to the posts created from Jeedom on the community forum (no personal data).
	 * @return string
	 */
	public static function getConfigForCommunity() {
		$deamon_info = self::deamon_info();
		$byType = array();
		$online = 0;
		$total = 0;
		foreach (self::getDevices(true) as $eqLogic) {
			$type = $eqLogic->getConfiguration('deviceType', '?') . ' V' . $eqLogic->getConfiguration('protocolVersion', '?');
			$byType[$type] = isset($byType[$type]) ? $byType[$type] + 1 : 1;
			$cmd = $eqLogic->getCmd('info', 'online');
			$online += (is_object($cmd) && $cmd->execCmd() == 1) ? 1 : 0;
			$total++;
		}
		$types = array();
		foreach ($byType as $type => $count) {
			$types[] = $count . ' × ' . $type;
		}
		$requirements = array();
		foreach (file(__DIR__ . '/../../resources/requirements.in', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
			if (substr(trim($line), 0, 1) != '#') {
				$requirements[] = trim($line);
			}
		}
		$return = '- ' . __('Démon', __FILE__) . ' : ' . $deamon_info['state'] . '<br>';
		$return .= '- ' . __('Bibliothèques', __FILE__) . ' : ' . implode(', ', $requirements) . '<br>';
		$return .= '- ' . __('Appareils', __FILE__) . ' : ' . (($total > 0) ? implode(', ', $types) : '0') . ' (' . $online . '/' . $total . ' ' . __('joignables', __FILE__) . ')<br>';
		$return .= '- ' . __('Compte MSmartHome configuré', __FILE__) . ' : ' . ((config::byKey('cloudAccount', __CLASS__, '') === '') ? __('non', __FILE__) : __('oui', __FILE__)) . '<br>';
		$return .= '- ' . __('Adresse de diffusion', __FILE__) . ' : ' . ((config::byKey('broadcastAddress', __CLASS__, '') === '') ? __('automatique', __FILE__) : __('manuelle', __FILE__)) . '<br>';
		return $return;
	}

	/**
	 * Asks the daemon for the diagnostic of the equipment, read afterwards with getDiagnostic().
	 */
	public function requestDiagnostic() {
		cache::delete(__CLASS__ . '::diagnostic::' . $this->getId());
		self::sendToDaemon(array('action' => 'getDiagnostic', 'eqLogicId' => intval($this->getId())));
	}

	/**
	 * @return array|null Diagnostic sent by the daemon, null while it has not answered
	 */
	public function getDiagnostic() {
		$cache = cache::byKey(__CLASS__ . '::diagnostic::' . $this->getId());
		$value = $cache->getValue(null);
		return is_array($value) ? $value : null;
	}

	/*     * ********************Synchronisation************************** */

	/**
	 * Asks the daemon to synchronize the appliances (cloud account + local network).
	 * The result comes back asynchronously ('syncResult' on the callback).
	 * @param mideamsmart|null $_eqLogic Only this equipment (keys retrieval), or every appliance
	 */
	public static function syncDevices($_eqLogic = null) {
		$knownDevices = array();
		foreach (self::getDevices() as $eqLogic) {
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
		// The cloud refusals are remembered here too: they must survive a daemon restart
		$cloudBlock = self::getCloudBlockMessage($message['account'], $message['password']);
		if ($cloudBlock !== '') {
			if (is_object($_eqLogic)) {
				throw new Exception($cloudBlock);
			}
			// The local search stays useful (new addresses): synchronize without the cloud
			$message['account'] = '';
			$message['password'] = '';
			self::notifyUser($cloudBlock . '. ' . __('Synchronisation limitée au réseau local', __FILE__), 'warning');
		}
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

	private static function getCredentialsFingerprint($_account, $_password) {
		return sha1($_account . "\0" . $_password);
	}

	/**
	 * Reason why the cloud must not be contacted now, or an empty string.
	 * @return string
	 */
	public static function getCloudBlockMessage($_account, $_password) {
		if ($_account === '' || $_password === '') {
			return '';
		}
		$lockedUntil = intval(config::byKey('cloudLockedUntil', __CLASS__, 0));
		if ($lockedUntil > time()) {
			return __('Le cloud Midea a temporairement bloqué le compte, réessayez dans', __FILE__) . ' ' . max(1, ceil(($lockedUntil - time()) / 60)) . ' min';
		}
		if (config::byKey('cloudRejectedCredentials', __CLASS__, '') === self::getCredentialsFingerprint($_account, $_password)) {
			return __('Identifiant ou mot de passe MSmartHome incorrect', __FILE__) . ' : ' . __('modifiez-les dans la configuration du plugin', __FILE__);
		}
		return '';
	}

	private static function recordCloudError($_error) {
		$reason = isset($_error['reason']) ? $_error['reason'] : '';
		if ($reason == 'accountLocked') {
			$retryAfter = max(60, isset($_error['retryAfter']) ? intval($_error['retryAfter']) : 0);
			config::save('cloudLockedUntil', time() + $retryAfter, __CLASS__);
		} elseif ($reason == 'invalidCredentials') {
			config::save('cloudRejectedCredentials', self::getCredentialsFingerprint(config::byKey('cloudAccount', __CLASS__, ''), config::byKey('cloudPassword', __CLASS__, '')), __CLASS__);
		}
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
			self::recordCloudError($_result['cloudError']);
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
		if ($this->isScheduler()) {
			$this->checkProfiles();
			return;
		}
		$this->checkSchedule();

		// Midea type in hexadecimal (AC, CC, A1…): it is displayed in the pages
		$deviceType = strtoupper(trim($this->getConfiguration('deviceType', '')));
		if ($deviceType !== '' && !preg_match('/^[0-9A-F]{2}$/', $deviceType)) {
			throw new Exception(__('Type d\'appareil invalide', __FILE__) . ' : ' . htmlspecialchars($deviceType));
		}
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
		$connectionLifetime = trim($this->getConfiguration('connectionLifetime', ''));
		if ($connectionLifetime !== '') {
			$this->setConfiguration('connectionLifetime', self::checkConnectionLifetime($connectionLifetime));
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
		if ($this->isScheduler()) {
			$this->createSchedulerCommands();
			// The active profile may have been changed in the page
			self::runSchedules();
			return;
		}
		// Options such as the temperature step change the commands display
		$this->createCommands(false);
		$this->checkAndUpdateCmd('scheduleEnabled', $this->getConfiguration('scheduleEnabled', 0));
		if ($this->_scheduleResumed) {
			// Resumed: the current slot is applied (catch-up) or the next one is waited for
			$this->_scheduleResumed = false;
			$this->resetSchedule();
			self::runSchedules($this);
		} elseif ($this->_scheduleEdited) {
			// Editing the slots must not change the appliance state: wait for the next one
			$this->_scheduleEdited = false;
			$this->markScheduleApplied();
		}
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
		if ($this->isScheduler()) {
			return;
		}
		cache::delete($this->getScheduleCacheKey());
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
			'connectionLifetime' => $this->getConnectionLifetime(),
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
		// The appliance status is shown at once in the Jeedom health and timeout views.
		// online is sent at each successful poll, even when no value changed: the last
		// communication date stays up to date for the "max delay between 2 communications" check
		if (isset($_values['online'])) {
			if ($_values['online'] == 1) {
				$this->setStatus(array('lastCommunication' => date('Y-m-d H:i:s'), 'timeout' => 0));
			} else {
				$this->setStatus('timeout', 1);
			}
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
		$deviceType = $this->isScheduler() ? 'scheduler' : strtolower($this->getConfiguration('deviceType', ''));
		$image = 'plugins/' . __CLASS__ . '/desktop/img/' . $deviceType . '.png';
		if ($deviceType !== '' && file_exists(__DIR__ . '/../../../../' . $image)) {
			return $image;
		}
		return parent::getImage();
	}

	public function getConnectionLifetime() {
		$connectionLifetime = $this->getConfiguration('connectionLifetime', '');
		if ($connectionLifetime === '') {
			$connectionLifetime = config::byKey('connectionLifetime', __CLASS__, self::DEFAULT_CONNECTION_LIFETIME);
		}
		return intval($connectionLifetime);
	}

	public function getPollingInterval() {
		$pollingInterval = $this->getConfiguration('pollingInterval', '');
		if ($pollingInterval === '') {
			$pollingInterval = config::byKey('defaultPollingInterval', __CLASS__, self::DEFAULT_POLLING_INTERVAL);
		}
		return intval($pollingInterval);
	}

	/*     * ************************Programmation************************** */

	/**
	 * Equipment holding the schedule profiles.
	 * @param bool $_create Creates it when it is missing
	 * @return mideamsmart|null
	 */
	public static function getScheduler($_create = false) {
		$scheduler = eqLogic::byLogicalId(self::SCHEDULER_LOGICAL_ID, __CLASS__);
		if (is_object($scheduler)) {
			return $scheduler;
		}
		if (!$_create) {
			return null;
		}
		$scheduler = new self();
		$scheduler->setEqType_name(__CLASS__);
		$scheduler->setLogicalId(self::SCHEDULER_LOGICAL_ID);
		$scheduler->setName(__('Programmation', __FILE__));
		$scheduler->setIsEnable(1);
		$scheduler->setIsVisible(1);
		$scheduler->setConfiguration('profiles', array(
			array('id' => '1', 'name' => __('Normal', __FILE__)),
			array('id' => '2', 'name' => __('Vacances', __FILE__)),
		));
		$scheduler->setConfiguration('nextProfileId', 3);
		$scheduler->setConfiguration('activeProfile', '1');
		$scheduler->save();
		log::add(__CLASS__, 'info', __('Équipement de programmation créé', __FILE__) . ' : ' . $scheduler->getHumanName());
		return $scheduler;
	}

	/**
	 * @return array Profiles of the schedule equipment: array(array('id' => '1', 'name' => 'Normal'), ...)
	 */
	public function getProfiles() {
		$profiles = $this->getConfiguration('profiles', array());
		return is_array($profiles) ? array_values($profiles) : array();
	}

	/**
	 * @return array|null Active profile of the schedule equipment
	 */
	public function getActiveProfile() {
		$activeProfile = (string) $this->getConfiguration('activeProfile', '');
		foreach ($this->getProfiles() as $profile) {
			if ((string) $profile['id'] === $activeProfile) {
				return $profile;
			}
		}
		return null;
	}

	/**
	 * Checks the profiles of the schedule equipment and gives an identifier to the new ones.
	 * The identifiers are never reused: the slots of a deleted profile are not taken over by a new one.
	 */
	private function checkProfiles() {
		$nextId = max(1, intval($this->getConfiguration('nextProfileId', 1)));
		foreach ($this->getProfiles() as $profile) {
			if (isset($profile['id']) && ctype_digit((string) $profile['id'])) {
				$nextId = max($nextId, intval($profile['id']) + 1);
			}
		}
		$profiles = array();
		$names = array();
		foreach ($this->getProfiles() as $profile) {
			// | and ; separate the values of the profile list command
			$name = trim(str_replace(array('|', ';'), '', isset($profile['name']) ? (string) $profile['name'] : ''));
			if ($name === '') {
				throw new Exception(__('Le nom d\'un profil ne peut pas être vide', __FILE__));
			}
			$key = mb_strtolower($name);
			if (isset($names[$key])) {
				throw new Exception(__('Nom de profil en double', __FILE__) . ' : ' . htmlspecialchars($name));
			}
			$names[$key] = true;
			$id = isset($profile['id']) ? trim((string) $profile['id']) : '';
			if ($id === '') {
				$id = (string) $nextId++;
			}
			$profiles[] = array('id' => $id, 'name' => $name);
		}
		if (count($profiles) == 0) {
			throw new Exception(__('Créez au moins un profil', __FILE__));
		}
		$this->setConfiguration('profiles', $profiles);
		$this->setConfiguration('nextProfileId', $nextId);
		if ($this->getActiveProfile() === null) {
			$this->setConfiguration('activeProfile', $profiles[0]['id']);
		}
	}

	private function createSchedulerCommands() {
		$info = $this->getCmd('info', 'profile');
		if (!is_object($info)) {
			$info = new mideamsmartCmd();
			$info->setEqLogic_id($this->getId());
			$info->setLogicalId('profile');
			$info->setName(__('Profil', __FILE__));
			$info->setType('info');
			$info->setSubType('string');
			$info->setOrder(1);
			$info->setIsVisible(0);
			$info->save();
		}
		$action = $this->getCmd('action', 'setProfile');
		if (!is_object($action)) {
			$action = new mideamsmartCmd();
			$action->setEqLogic_id($this->getId());
			$action->setLogicalId('setProfile');
			$action->setName(__('Choisir le profil', __FILE__));
			$action->setType('action');
			$action->setSubType('select');
			$action->setOrder(2);
			$action->setIsVisible(1);
		}
		$values = array();
		foreach ($this->getProfiles() as $profile) {
			$values[] = $profile['id'] . '|' . $profile['name'];
		}
		$action->setConfiguration('listValue', implode(';', $values));
		$action->setValue($info->getId());
		$action->save();
		$activeProfile = $this->getActiveProfile();
		$this->checkAndUpdateCmd('profile', is_array($activeProfile) ? $activeProfile['name'] : '');
	}

	/**
	 * Changes the active profile (command of the schedule equipment) and applies it at once.
	 * @param string $_value Profile identifier or name (case insensitive)
	 */
	public function setActiveProfile($_value) {
		$value = trim((string) $_value);
		foreach ($this->getProfiles() as $profile) {
			if ((string) $profile['id'] !== $value && mb_strtolower($profile['name']) !== mb_strtolower($value)) {
				continue;
			}
			if ((string) $this->getConfiguration('activeProfile', '') !== (string) $profile['id']) {
				log::add(__CLASS__, 'info', __('Profil de programmation actif', __FILE__) . ' : ' . $profile['name']);
			}
			$this->setConfiguration('activeProfile', (string) $profile['id']);
			// Direct save: no preSave/postSave, the profiles do not change
			$this->save(true);
			$this->checkAndUpdateCmd('profile', $profile['name']);
			self::runSchedules();
			return;
		}
		throw new Exception(__('Profil de programmation inconnu', __FILE__) . ' : ' . htmlspecialchars($value));
	}

	/**
	 * Checks the schedule of an appliance (slots edited in the page).
	 */
	private function checkSchedule() {
		$slots = $this->getConfiguration('scheduleSlots', array());
		$checkedSlots = array();
		foreach (is_array($slots) ? $slots : array() as $slot) {
			if (!is_array($slot)) {
				continue;
			}
			$time = isset($slot['time']) ? trim((string) $slot['time']) : '';
			if (!preg_match('/^([01][0-9]|2[0-3]):[0-5][0-9]$/', $time)) {
				throw new Exception(__('Heure de créneau invalide', __FILE__) . ' : ' . htmlspecialchars($time));
			}
			$days = array();
			foreach ((isset($slot['days']) && is_array($slot['days'])) ? $slot['days'] : array() as $day) {
				if (intval($day) >= 1 && intval($day) <= 7) {
					$days[intval($day)] = intval($day);
				}
			}
			if (count($days) == 0) {
				throw new Exception(__('Choisissez au moins un jour pour le créneau de', __FILE__) . ' ' . $time);
			}
			ksort($days);
			$checkedSlot = array(
				'profile' => isset($slot['profile']) ? (string) $slot['profile'] : '',
				'days' => array_values($days),
				'time' => $time,
				'action' => (isset($slot['action']) && $slot['action'] == 'off') ? 'off' : 'on',
			);
			if ($checkedSlot['action'] == 'on') {
				foreach (array('mode', 'fanSpeed', 'preset') as $key) {
					if (isset($slot[$key]) && trim((string) $slot[$key]) !== '') {
						$checkedSlot[$key] = trim((string) $slot[$key]);
					}
				}
				foreach (array('targetTemperature' => array(0, 50), 'targetHumidity' => array(0, 100)) as $key => $limits) {
					$value = isset($slot[$key]) ? str_replace(',', '.', trim((string) $slot[$key])) : '';
					if ($value === '') {
						continue;
					}
					if (!is_numeric($value) || floatval($value) < $limits[0] || floatval($value) > $limits[1]) {
						throw new Exception(__('Valeur invalide dans le créneau de', __FILE__) . ' ' . $time . ' : ' . htmlspecialchars($value));
					}
					$checkedSlot[$key] = floatval($value);
				}
			}
			$checkedSlots[] = $checkedSlot;
		}
		usort($checkedSlots, function ($a, $b) {
			return strcmp($a['profile'] . ' ' . $a['time'], $b['profile'] . ' ' . $b['time']);
		});
		$this->setConfiguration('scheduleSlots', $checkedSlots);
		$scheduleEnabled = ($this->getConfiguration('scheduleEnabled', 0) == 1) ? 1 : 0;
		$this->setConfiguration('scheduleEnabled', $scheduleEnabled);
		$this->setConfiguration('scheduleCatchUp', ($this->getConfiguration('scheduleCatchUp', 1) == 1) ? 1 : 0);

		$previous = ($this->getId() != '') ? self::byId($this->getId()) : null;
		$previousSlots = is_object($previous) ? $previous->getConfiguration('scheduleSlots', array()) : array();
		$this->_scheduleResumed = ($scheduleEnabled == 1 && (!is_object($previous) || $previous->getConfiguration('scheduleEnabled', 0) != 1));
		$this->_scheduleEdited = (json_encode($previousSlots) !== json_encode($checkedSlots));
	}

	/**
	 * Suspends or resumes the schedule of the appliance (commands scheduleOff and scheduleOn).
	 * @param bool $_enabled
	 */
	public function setScheduleEnabled($_enabled) {
		$enabled = $_enabled ? 1 : 0;
		$resumed = ($enabled == 1 && $this->getConfiguration('scheduleEnabled', 0) != 1);
		$this->setConfiguration('scheduleEnabled', $enabled);
		// Direct save: the daemon configuration does not change
		$this->save(true);
		$this->checkAndUpdateCmd('scheduleEnabled', $enabled);
		log::add(__CLASS__, 'info', $this->getHumanName() . ' : ' . ($enabled ? __('programmation suivie', __FILE__) : __('programmation suspendue', __FILE__)));
		if ($resumed) {
			$this->resetSchedule();
			self::runSchedules($this);
		}
	}

	public static function cron() {
		self::runSchedules();
	}

	/**
	 * Applies the schedule slots that are due.
	 * @param mideamsmart|null $_eqLogic Only this appliance, or every appliance that follows the schedule
	 */
	public static function runSchedules($_eqLogic = null) {
		$scheduler = self::getScheduler();
		if (!is_object($scheduler) || $scheduler->getIsEnable() != 1) {
			return;
		}
		$profileId = (string) $scheduler->getConfiguration('activeProfile', '');
		$now = time();
		foreach (is_object($_eqLogic) ? array($_eqLogic) : self::getDevices(true) as $eqLogic) {
			if ($eqLogic->getIsEnable() != 1 || $eqLogic->getConfiguration('scheduleEnabled', 0) != 1) {
				continue;
			}
			try {
				$eqLogic->runSchedule($profileId, $now);
			} catch (Exception $e) {
				log::add(__CLASS__, 'warning', $eqLogic->getHumanName() . ' : ' . __('créneau de programmation non appliqué', __FILE__) . ' : ' . $e->getMessage());
			}
		}
	}

	/**
	 * Most recent past occurrence of the slots of a profile, over the last 7 days.
	 * @param array $_slots
	 * @param string $_profileId
	 * @param int $_now Timestamp
	 * @return array|null array('slot' => array, 'timestamp' => int)
	 */
	public static function findLastOccurrence($_slots, $_profileId, $_now) {
		$last = null;
		foreach (is_array($_slots) ? $_slots : array() as $slot) {
			if (!is_array($slot) || !isset($slot['profile'], $slot['time'], $slot['days']) || (string) $slot['profile'] !== (string) $_profileId) {
				continue;
			}
			if (!preg_match('/^([0-9]{2}):([0-9]{2})$/', $slot['time'], $matches)) {
				continue;
			}
			$days = array_map('intval', (array) $slot['days']);
			for ($i = 0; $i <= self::SCHEDULE_LOOKBACK_DAYS; $i++) {
				$day = strtotime('-' . $i . ' days', $_now);
				$timestamp = mktime(intval($matches[1]), intval($matches[2]), 0, date('n', $day), date('j', $day), date('Y', $day));
				if ($timestamp > $_now || !in_array(intval(date('N', $day)), $days)) {
					continue;
				}
				if ($last === null || $timestamp > $last['timestamp']) {
					$last = array('slot' => $slot, 'timestamp' => $timestamp);
				}
				break;
			}
		}
		return $last;
	}

	private static function getOccurrenceKey($_occurrence, $_profileId) {
		if ($_occurrence === null) {
			return $_profileId . '|';
		}
		return $_profileId . '|' . sha1(json_encode($_occurrence['slot'])) . '|' . date('Y-m-d H:i', $_occurrence['timestamp']);
	}

	private function getScheduleCacheKey() {
		return __CLASS__ . '::schedule::' . $this->getId();
	}

	public function getScheduleSlots() {
		$slots = $this->getConfiguration('scheduleSlots', array());
		return is_array($slots) ? $slots : array();
	}

	/**
	 * Applies the current slot of the profile when it was not applied yet.
	 * @param string $_profileId
	 * @param int $_now Timestamp
	 * @return bool A new occurrence was handled
	 */
	public function runSchedule($_profileId, $_now) {
		$occurrence = self::findLastOccurrence($this->getScheduleSlots(), $_profileId, $_now);
		$key = self::getOccurrenceKey($occurrence, $_profileId);
		if (cache::byKey($this->getScheduleCacheKey())->getValue('') === $key) {
			return false;
		}
		if ($occurrence !== null) {
			$fresh = ($_now - $occurrence['timestamp']) < self::SCHEDULE_FRESH_DELAY;
			if ($fresh || $this->getConfiguration('scheduleCatchUp', 1) == 1) {
				// Not remembered when the daemon cannot be reached: new try at the next minute
				$this->applyScheduleSlot($occurrence['slot'], $fresh);
			}
		}
		cache::set($this->getScheduleCacheKey(), $key);
		return true;
	}

	private function markScheduleApplied() {
		$scheduler = self::getScheduler();
		if (!is_object($scheduler)) {
			return;
		}
		$profileId = (string) $scheduler->getConfiguration('activeProfile', '');
		cache::set($this->getScheduleCacheKey(), self::getOccurrenceKey(self::findLastOccurrence($this->getScheduleSlots(), $profileId, time()), $profileId));
	}

	private function resetSchedule() {
		cache::delete($this->getScheduleCacheKey());
	}

	/**
	 * Sends the commands of a slot to the appliance, in one message (executed in this order).
	 * @param array $_slot
	 * @param bool $_fresh false when the slot is caught up
	 */
	public function applyScheduleSlot($_slot, $_fresh = true) {
		$commands = array();
		if ($_slot['action'] == 'off') {
			$commands[] = array('command' => 'off', 'value' => null);
		} else {
			// Choosing a mode turns the appliance on
			if (isset($_slot['mode']) && is_object($this->getCmd('action', 'setMode'))) {
				$commands[] = array('command' => 'setMode', 'value' => $_slot['mode']);
			} else {
				$commands[] = array('command' => 'on', 'value' => null);
			}
			foreach (array('targetTemperature' => 'setTargetTemperature', 'fanSpeed' => 'setFanSpeed', 'preset' => 'setPreset', 'targetHumidity' => 'setTargetHumidity') as $key => $logicalId) {
				if (!isset($_slot[$key])) {
					continue;
				}
				if (!is_object($this->getCmd('action', $logicalId))) {
					log::add(__CLASS__, 'debug', $this->getHumanName() . ' : ' . __('commande absente, ignorée', __FILE__) . ' : ' . $logicalId);
					continue;
				}
				$commands[] = array('command' => $logicalId, 'value' => $_slot[$key]);
			}
		}
		self::sendToDaemon(array('action' => 'executeCommands', 'eqLogicId' => intval($this->getId()), 'commands' => $commands));
		log::add(__CLASS__, 'info', $this->getHumanName() . ' : ' . __('créneau de programmation appliqué', __FILE__) . ' ' . $_slot['time'] . ($_fresh ? '' : ' (' . __('rattrapage', __FILE__) . ')') . ' : ' . json_encode($commands));
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
		// Commands handled by Jeedom only
		if ($eqLogic->isScheduler()) {
			if ($this->getLogicalId() == 'setProfile') {
				$eqLogic->setActiveProfile($value);
			}
			return;
		}
		if ($this->getLogicalId() == 'scheduleOn' || $this->getLogicalId() == 'scheduleOff') {
			$eqLogic->setScheduleEnabled($this->getLogicalId() == 'scheduleOn');
			return;
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
