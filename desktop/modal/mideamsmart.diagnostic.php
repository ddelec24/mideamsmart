<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 *
 * Diagnostic of an equipment: Jeedom configuration and state seen by the daemon.
 */

if (!isConnect('admin')) {
	throw new Exception('{{401 - Accès non autorisé}}');
}
$eqLogic = mideamsmart::byId(init('id'));
if (!is_object($eqLogic) || $eqLogic->getEqType_name() != 'mideamsmart') {
	throw new Exception('{{Équipement introuvable}}' . ' : ' . init('id'));
}
$deamon_info = mideamsmart::deamon_info();
$capabilities = $eqLogic->getConfiguration('capabilities', array());
// No secret here: the summary can be copied to the community forum
$jeedomInfo = array(
	'plugin' => array(
		'daemon' => $deamon_info['state'],
		'dependencies' => plugin::byId('mideamsmart')->dependancy_info()['state'],
	),
	'equipment' => array(
		'enabled' => intval($eqLogic->getIsEnable()),
		'deviceType' => $eqLogic->getConfiguration('deviceType', ''),
		'protocolVersion' => intval($eqLogic->getConfiguration('protocolVersion', 3)),
		'ipAddress' => $eqLogic->getConfiguration('ipAddress', ''),
		'port' => intval($eqLogic->getConfiguration('port', mideamsmart::DEFAULT_DEVICE_PORT)),
		'hasToken' => $eqLogic->getConfiguration('token', '') !== '',
		'hasKey' => $eqLogic->getConfiguration('key', '') !== '',
		'model' => $eqLogic->getConfiguration('model', ''),
		'pollingInterval' => $eqLogic->getPollingInterval(),
		'lastCommunication' => $eqLogic->getStatus('lastCommunication', ''),
		'timeout' => intval($eqLogic->getStatus('timeout', 0)),
		'commands' => count($eqLogic->getCmd()),
	),
	'capabilities' => $capabilities,
);
sendVarToJS('mideamsmartDiagnostic', array(
	'eqLogicId' => intval($eqLogic->getId()),
	'jeedom' => $jeedomInfo,
	'daemonRunning' => $deamon_info['state'] == 'ok',
));
?>
<div id="div_mideamsmartDiagnostic">
	<div class="input-group pull-right" style="display:inline-flex;">
		<span class="input-group-btn">
			<a class="btn btn-sm btn-default roundedLeft" id="bt_mideamsmartDiagnosticRefresh"><i class="fas fa-sync"></i> {{Actualiser}}
			</a><a class="btn btn-sm btn-primary roundedRight" id="bt_mideamsmartDiagnosticCopy"><i class="fas fa-copy"></i> {{Copier pour le forum}}</a>
		</span>
	</div>
	<legend><i class="fas fa-stethoscope"></i> <?php echo $eqLogic->getHumanName(true); ?></legend>
	<div class="alert alert-info">{{Ce résumé ne contient ni mot de passe, ni token, ni key : il peut être joint à une demande d'aide sur le forum.}}</div>
	<div class="row">
		<div class="col-lg-6">
			<legend><i class="fas fa-home"></i> {{Jeedom}}</legend>
			<pre id="pre_mideamsmartDiagnosticJeedom" style="max-height:60vh;overflow:auto;"></pre>
		</div>
		<div class="col-lg-6">
			<legend><i class="fas fa-university"></i> {{Démon}}</legend>
			<pre id="pre_mideamsmartDiagnosticDaemon" style="max-height:60vh;overflow:auto;">{{Interrogation du démon...}}</pre>
		</div>
	</div>
</div>

<script>
(function() {
  const diagnostic = mideamsmartDiagnostic
  const preJeedom = document.getElementById('pre_mideamsmartDiagnosticJeedom')
  const preDaemon = document.getElementById('pre_mideamsmartDiagnosticDaemon')
  let daemonData = null
  preJeedom.textContent = JSON.stringify(diagnostic.jeedom, null, 2)

  function ajax(_action, _success) {
    domUtils.ajax({
      type: 'POST',
      url: 'plugins/mideamsmart/core/ajax/mideamsmart.ajax.php',
      data: { action: _action, id: diagnostic.eqLogicId },
      dataType: 'json',
      global: false,
      error: function(error) {
        preDaemon.textContent = error.message
      },
      success: function(data) {
        if (data.state != 'ok') {
          preDaemon.textContent = data.result
          return
        }
        _success(data.result)
      }
    })
  }

  function load() {
    if (!diagnostic.daemonRunning) {
      preDaemon.textContent = '{{Le démon n\'est pas démarré}}'
      return
    }
    preDaemon.textContent = '{{Interrogation du démon...}}'
    ajax('requestDiagnostic', function() {
      let attempts = 0
      const poll = function() {
        ajax('getDiagnostic', function(result) {
          if (result !== null && result !== '') {
            daemonData = result
            preDaemon.textContent = JSON.stringify(result, null, 2)
            return
          }
          if (++attempts < 20) {
            setTimeout(poll, 500)
          } else {
            preDaemon.textContent = '{{Le démon n\'a pas répondu}}'
          }
        })
      }
      setTimeout(poll, 300)
    })
  }

  document.getElementById('bt_mideamsmartDiagnosticRefresh').addEventListener('click', load)
  document.getElementById('bt_mideamsmartDiagnosticCopy').addEventListener('click', function() {
    const text = '[details="mideamsmart - diagnostic"]\n```json\n' + JSON.stringify({ jeedom: diagnostic.jeedom, daemon: daemonData }, null, 2) + '\n```\n[/details]'
    navigator.clipboard.writeText(text).then(function() {
      jeedomUtils.showAlert({ message: '{{Diagnostic copié dans le presse-papiers}}', level: 'success' })
    }, function() {
      jeedomUtils.showAlert({ message: '{{Copie impossible, sélectionnez le texte à la main}}', level: 'warning' })
    })
  })
  load()
})()
</script>
