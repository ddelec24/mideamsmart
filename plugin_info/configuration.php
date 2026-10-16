<?php
/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

require_once dirname(__FILE__) . '/../../../core/php/core.inc.php';
include_file('core', 'authentification', 'php');
if (!isConnect()) {
	include_file('desktop', '404', 'php');
	die();
}
?>
<form class="form-horizontal">
	<fieldset>
		<legend><i class="fas fa-cloud"></i> {{Compte MSmartHome}}</legend>
		<div class="alert alert-info">
			{{Le compte sert uniquement à lister vos appareils et à récupérer leurs clés d'authentification (token/key). Le pilotage se fait ensuite en local.}}<br>
			{{Les appareils doivent être appairés directement sur ce compte dans l'application MSmartHome : un appareil simplement partagé ne fonctionne pas.}}
		</div>
		<div class="form-group">
			<label class="col-md-4 control-label">{{Identifiant (email)}}
				<sup><i class="fas fa-question-circle tooltips" title="{{Adresse email du compte MSmartHome}}"></i></sup>
			</label>
			<div class="col-md-4">
				<input class="configKey form-control" data-l1key="cloudAccount" autocomplete="off">
			</div>
		</div>
		<div class="form-group">
			<label class="col-md-4 control-label">{{Mot de passe}}
				<sup><i class="fas fa-question-circle tooltips" title="{{Mot de passe du compte MSmartHome}}"></i></sup>
			</label>
			<div class="col-md-4">
				<input type="text" class="configKey form-control inputPassword" data-l1key="cloudPassword" autocomplete="off">
			</div>
		</div>

		<legend><i class="fas fa-network-wired"></i> {{Réseau local}}</legend>
		<div class="form-group">
			<label class="col-md-4 control-label">{{Adresse de diffusion}}
				<sup><i class="fas fa-question-circle tooltips" title="{{Adresse(s) de broadcast utilisée(s) pour découvrir les appareils, séparées par des virgules (ex. : 192.168.1.255). Laisser vide pour utiliser toutes les interfaces réseau de Jeedom}}"></i></sup>
			</label>
			<div class="col-md-4">
				<input class="configKey form-control" data-l1key="broadcastAddress" placeholder="{{Automatique}}">
			</div>
		</div>
		<div class="form-group">
			<label class="col-md-4 control-label">{{Intervalle d'interrogation par défaut (s)}}
				<sup><i class="fas fa-question-circle tooltips" title="{{Délai entre deux lectures de l'état des appareils, appliqué aux équipements sans valeur spécifique}}"></i></sup>
			</label>
			<div class="col-md-4">
				<input type="number" min="10" class="configKey form-control" data-l1key="defaultPollingInterval" placeholder="<?php echo mideamsmart::DEFAULT_POLLING_INTERVAL; ?>">
			</div>
		</div>

		<legend><i class="fas fa-university"></i> {{Démon}}</legend>
		<div class="form-group">
			<label class="col-md-4 control-label">{{Port du démon}}
				<sup><i class="fas fa-question-circle tooltips" title="{{Port local d'écoute du démon, à ne modifier qu'en cas de conflit avec un autre plugin}}"></i></sup>
			</label>
			<div class="col-md-4">
				<input type="number" class="configKey form-control" data-l1key="socketport" placeholder="<?php echo mideamsmart::DEFAULT_SOCKET_PORT; ?>">
			</div>
		</div>
	</fieldset>
</form>
