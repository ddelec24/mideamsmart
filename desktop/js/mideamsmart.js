/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

'use strict'

if (typeof jeeFrontEnd.mideamsmart === 'undefined') {
  jeeFrontEnd.mideamsmart = {
    defaultImage: 'plugins/mideamsmart/plugin_info/mideamsmart_icon.png',
    syncDevices: function() {
      jeedomUtils.showAlert({ message: '{{Synchronisation en cours...}}', level: 'warning' })
      domUtils.ajax({
        type: 'POST',
        url: 'plugins/mideamsmart/core/ajax/mideamsmart.ajax.php',
        data: {
          action: 'syncDevices'
        },
        dataType: 'json',
        error: function(error) {
          jeedomUtils.showAlert({ message: error.message, level: 'danger' })
        },
        success: function(data) {
          if (data.state != 'ok') {
            jeedomUtils.showAlert({ message: data.result, level: 'danger' })
            return
          }
          jeedomUtils.showAlert({ message: '{{Synchronisation terminée}}', level: 'success' })
          jeedomUtils.loadPage(document.URL)
        }
      })
    }
  }
}

document.getElementById('bt_mideamsmartSyncDevices')?.addEventListener('click', function() {
  jeeFrontEnd.mideamsmart.syncDevices()
})

/* Called by the core when an equipment is displayed */
function printEqLogic(_eqLogic) {
  const img = document.getElementById('img_mideamsmartDevice')
  if (img == null) return
  const deviceType = init(_eqLogic.configuration?.deviceType).toLowerCase()
  img.onerror = function() {
    this.onerror = null
    this.src = jeeFrontEnd.mideamsmart.defaultImage
  }
  img.src = (deviceType != '') ? 'plugins/mideamsmart/desktop/img/' + deviceType + '.png' : jeeFrontEnd.mideamsmart.defaultImage
}

/* Commands are created by the plugin: type, sub-type and logical ID are read-only */
function addCmdToTable(_cmd) {
  if (!isset(_cmd)) {
    _cmd = { configuration: {} }
  }
  if (!isset(_cmd.configuration)) {
    _cmd.configuration = {}
  }
  let tr = '<td class="hidden-xs">'
  tr += '<span class="cmdAttr" data-l1key="id"></span>'
  tr += '</td>'
  tr += '<td>'
  tr += '<div class="input-group">'
  tr += '<input class="cmdAttr form-control input-sm roundedLeft" data-l1key="name" placeholder="{{Nom de la commande}}">'
  tr += '<span class="input-group-btn"><a class="cmdAction btn btn-sm btn-default" data-l1key="chooseIcon" title="{{Choisir une icône}}"><i class="fas fa-icons"></i></a></span>'
  tr += '<span class="cmdAttr input-group-addon roundedRight" data-l1key="display" data-l2key="icon" style="font-size:19px;padding:0 5px 0 0!important;"></span>'
  tr += '</div>'
  tr += '<span class="cmdAttr label label-default" data-l1key="logicalId" style="display:inline-block;margin-top:5px;"></span>'
  tr += '</td>'
  tr += '<td>'
  tr += '<input class="cmdAttr form-control input-sm" data-l1key="type" disabled style="margin-bottom:5px;">'
  tr += '<input class="cmdAttr form-control input-sm" data-l1key="subType" disabled>'
  tr += '</td>'
  tr += '<td>'
  tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="isVisible" checked>{{Afficher}}</label> '
  if (init(_cmd.type) == 'info') {
    tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="isHistorized" checked>{{Historiser}}</label> '
    if (init(_cmd.subType) == 'binary') {
      tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="display" data-l2key="invertBinary">{{Inverser}}</label> '
    }
  }
  if (init(_cmd.subType) == 'numeric' || init(_cmd.subType) == 'slider') {
    tr += '<div style="margin-top:7px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="minValue" placeholder="{{Min}}" title="{{Min}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="maxValue" placeholder="{{Max}}" title="{{Max}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="unite" placeholder="{{Unité}}" title="{{Unité}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
    tr += '</div>'
  }
  tr += '</td>'
  tr += '<td>'
  tr += '<span class="cmdAttr" data-l1key="htmlstate"></span>'
  tr += '</td>'
  tr += '<td>'
  if (is_numeric(_cmd.id)) {
    tr += '<a class="btn btn-default btn-xs cmdAction" data-action="configure"><i class="fas fa-cogs"></i></a> '
    tr += '<a class="btn btn-default btn-xs cmdAction" data-action="test"><i class="fas fa-rss"></i> {{Tester}}</a>'
  }
  tr += '</td>'

  const newRow = document.createElement('tr')
  newRow.innerHTML = tr
  newRow.addClass('cmd')
  newRow.setAttribute('data-cmd_id', init(_cmd.id))
  document.getElementById('table_cmd').querySelector('tbody').appendChild(newRow)
  newRow.setJeeValues(_cmd, '.cmdAttr')
}
