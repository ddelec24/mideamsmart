/* This file is part of the mideamsmart plugin for Jeedom.
 * Licensed under the MIT License, see the LICENSE file.
 */

'use strict'

if (typeof jeeFrontEnd.mideamsmart === 'undefined') {
  jeeFrontEnd.mideamsmart = {
    defaultImage: 'plugins/mideamsmart/plugin_info/mideamsmart_icon.png',
    // Equipment whose keys were requested, redisplayed when the synchronization ends
    pendingEqLogicId: null,
    request: function(_action, _data, _successMessage) {
      domUtils.ajax({
        type: 'POST',
        url: 'plugins/mideamsmart/core/ajax/mideamsmart.ajax.php',
        data: Object.assign({ action: _action }, _data),
        dataType: 'json',
        error: function(error) {
          jeedomUtils.showAlert({ message: error.message, level: 'danger' })
        },
        success: function(data) {
          if (data.state != 'ok') {
            jeedomUtils.showAlert({ message: data.result, level: 'danger' })
            return
          }
          jeedomUtils.showAlert({ message: _successMessage, level: 'warning' })
        }
      })
    },
    syncDevices: function() {
      this.pendingEqLogicId = null
      this.request('syncDevices', {}, '{{Synchronisation lancée...}}')
    },
    fetchDeviceKeys: function() {
      const eqLogicId = document.querySelector('.eqLogicAttr[data-l1key="id"]').jeeValue()
      if (modifyWithoutSave) {
        jeedomUtils.showAlert({ message: '{{Sauvegardez l\'équipement avant de récupérer ses clés}}', level: 'warning' })
        return
      }
      this.pendingEqLogicId = eqLogicId
      this.request('fetchDeviceKeys', { id: eqLogicId }, '{{Récupération des clés lancée...}}')
    },
    // Schedule: context read when an appliance is displayed (profiles, active profile, labels)
    scheduleContext: null,
    scheduleEqLogic: null,
    slotsLoaded: false,
    profilesLoaded: false,
    days: [[1, '{{Lu}}'], [2, '{{Ma}}'], [3, '{{Me}}'], [4, '{{Je}}'], [5, '{{Ve}}'], [6, '{{Sa}}'], [7, '{{Di}}']],
    storageKey: 'mideamsmart::syncSummary',
    // detail: {created, message, level}, from a DOM event (event.detail) or a jQuery one (second argument)
    onSyncDone: function(_event, _jQueryDetail) {
      const detail = _jQueryDetail || (_event && _event.detail) || {}
      const eqLogicId = jeeFrontEnd.mideamsmart.pendingEqLogicId
      jeeFrontEnd.mideamsmart.pendingEqLogicId = null
      if (eqLogicId != null && document.querySelector('.eqLogic').isVisible()) {
        jeeFrontEnd.pluginTemplate.displayEqlogic(null, eqLogicId)
        return
      }
      if (!(detail.created > 0) || !document.querySelector('.eqLogicThumbnailDisplay').isVisible()) {
        return
      }
      try {
        sessionStorage.setItem(jeeFrontEnd.mideamsmart.storageKey, JSON.stringify({ message: detail.message, level: detail.level }))
      } catch (error) {}
      jeedomUtils.loadPage('index.php?v=d&m=mideamsmart&p=mideamsmart')
    },
    showPendingSummary: function() {
      let summary = null
      try {
        summary = JSON.parse(sessionStorage.getItem(this.storageKey))
        sessionStorage.removeItem(this.storageKey)
      } catch (error) {}
      if (summary && summary.message) {
        jeedomUtils.showAlert({ message: summary.message, level: summary.level || 'success' })
      }
    }
  }
  // Sent by the plugin (event::add) when a synchronization ends
  document.body.addEventListener('mideamsmart::syncDone', jeeFrontEnd.mideamsmart.onSyncDone)
  if (typeof jQuery === 'function') {
    // The core still triggers non-core events through jQuery when it is loaded
    $('body').off('mideamsmart::syncDone').on('mideamsmart::syncDone', jeeFrontEnd.mideamsmart.onSyncDone)
  }
}

jeeFrontEnd.mideamsmart.showPendingSummary()

document.getElementById('bt_mideamsmartSyncDevices')?.addEventListener('click', function() {
  jeeFrontEnd.mideamsmart.syncDevices()
})

document.getElementById('bt_mideamsmartUpdateCommands')?.addEventListener('click', function() {
  const eqLogicId = document.querySelector('.eqLogicAttr[data-l1key="id"]').jeeValue()
  domUtils.ajax({
    type: 'POST',
    url: 'plugins/mideamsmart/core/ajax/mideamsmart.ajax.php',
    data: { action: 'updateCommands', id: eqLogicId },
    dataType: 'json',
    error: function(error) {
      jeedomUtils.showAlert({ message: error.message, level: 'danger' })
    },
    success: function(data) {
      if (data.state != 'ok') {
        jeedomUtils.showAlert({ message: data.result, level: 'danger' })
        return
      }
      jeedomUtils.showAlert({ message: '{{Commandes mises à jour}}', level: 'success' })
      jeeFrontEnd.pluginTemplate.displayEqlogic(null, eqLogicId)
    }
  })
})

document.getElementById('bt_mideamsmartDiagnostic')?.addEventListener('click', function() {
  const eqLogicId = document.querySelector('.eqLogicAttr[data-l1key="id"]').jeeValue()
  jeeDialog.dialog({
    id: 'md_mideamsmartDiagnostic',
    title: '{{Diagnostic}}',
    width: '85%',
    height: '80%',
    contentUrl: 'index.php?v=d&plugin=mideamsmart&modal=mideamsmart.diagnostic&id=' + eqLogicId
  })
})

/* Options that only apply to some appliance types */
function mideamsmartUpdateTypeFields() {
  const deviceType = document.querySelector('.eqLogicAttr[data-l1key="configuration"][data-l2key="deviceType"]')?.jeeValue() || ''
  document.querySelectorAll('.mideamsmartDeviceType').forEach(function(element) {
    element.style.display = element.getAttribute('data-device-types').split(',').includes(deviceType) ? '' : 'none'
  })
}

document.querySelector('.eqLogicAttr[data-l1key="configuration"][data-l2key="deviceType"]')?.addEventListener('change', mideamsmartUpdateTypeFields)

document.getElementById('bt_mideamsmartFetchKeys')?.addEventListener('click', function() {
  jeeFrontEnd.mideamsmart.fetchDeviceKeys()
})

/* Schedule ----------------------------------------------------------------- */

function mideamsmartAjax(_action, _data, _success) {
  domUtils.ajax({
    type: 'POST',
    url: 'plugins/mideamsmart/core/ajax/mideamsmart.ajax.php',
    data: Object.assign({ action: _action }, _data),
    dataType: 'json',
    error: function(error) {
      jeedomUtils.showAlert({ message: error.message, level: 'danger' })
    },
    success: function(data) {
      if (data.state != 'ok') {
        jeedomUtils.showAlert({ message: data.result, level: 'danger' })
        return
      }
      _success(data.result)
    }
  })
}

function mideamsmartOpenScheduler() {
  if (jeeFrontEnd.modifyWithoutSave) {
    jeedomUtils.showAlert({ message: '{{Sauvegardez l\'équipement avant d\'ouvrir la programmation}}', level: 'warning' })
    return
  }
  mideamsmartAjax('openScheduler', {}, function(_schedulerId) {
    jeeFrontEnd.pluginTemplate.displayEqlogic(null, _schedulerId)
  })
}

function mideamsmartModified() {
  jeeFrontEnd.modifyWithoutSave = true
}

/* Built with the DOM API: profile names are typed by the user */
function mideamsmartElement(_tag, _className, _text) {
  const element = document.createElement(_tag)
  if (_className) element.className = _className
  if (_text != null) element.textContent = _text
  return element
}

function mideamsmartSelect(_className, _options, _value) {
  const select = mideamsmartElement('select', 'form-control input-sm ' + _className)
  _options.forEach(function(_option) {
    const option = mideamsmartElement('option', null, _option[1])
    option.value = _option[0]
    select.appendChild(option)
  })
  select.value = (_value == null) ? '' : String(_value)
  if (select.selectedIndex < 0) select.selectedIndex = 0
  return select
}

function mideamsmartRemoveButton(_onClick) {
  const button = mideamsmartElement('a', 'btn btn-xs btn-danger')
  button.title = '{{Supprimer}}'
  button.appendChild(mideamsmartElement('i', 'fas fa-minus-circle'))
  button.addEventListener('click', _onClick)
  return button
}

/* Profiles of the schedule equipment */
function mideamsmartAddProfileRow(_profile) {
  const tr = mideamsmartElement('tr', 'mideamsmartProfile')
  tr.setAttribute('data-profile-id', _profile.id || '')
  const input = mideamsmartElement('input', 'form-control input-sm mideamsmartProfileName')
  input.value = _profile.name || ''
  input.placeholder = '{{Nom du profil}}'
  input.addEventListener('input', function() {
    mideamsmartModified()
    mideamsmartUpdateActiveProfileOptions()
  })
  const tdName = mideamsmartElement('td')
  tdName.appendChild(input)
  const tdRemove = mideamsmartElement('td', 'text-center')
  tdRemove.appendChild(mideamsmartRemoveButton(function() {
    tr.remove()
    mideamsmartModified()
    mideamsmartUpdateActiveProfileOptions()
  }))
  tr.append(tdName, tdRemove)
  document.querySelector('#table_mideamsmartProfiles tbody').appendChild(tr)
}

/* Only the saved profiles can be activated: the new ones get their identifier when saved */
function mideamsmartUpdateActiveProfileOptions(_value) {
  const select = document.getElementById('sel_mideamsmartActiveProfile')
  const value = (_value != null) ? String(_value) : select.value
  const options = []
  document.querySelectorAll('#table_mideamsmartProfiles tr.mideamsmartProfile').forEach(function(_tr) {
    const id = _tr.getAttribute('data-profile-id')
    if (id !== '') options.push([id, _tr.querySelector('.mideamsmartProfileName').value])
  })
  const newSelect = mideamsmartSelect('', options, value)
  newSelect.id = 'sel_mideamsmartActiveProfile'
  newSelect.classList.remove('input-sm')
  newSelect.addEventListener('change', mideamsmartModified)
  select.replaceWith(newSelect)
}

function mideamsmartPrintScheduler(_eqLogic) {
  document.querySelector('#table_mideamsmartProfiles tbody').innerHTML = ''
  const profiles = Array.isArray(_eqLogic.configuration?.profiles) ? _eqLogic.configuration.profiles : []
  profiles.forEach(mideamsmartAddProfileRow)
  mideamsmartUpdateActiveProfileOptions(_eqLogic.configuration?.activeProfile)
  jeeFrontEnd.mideamsmart.profilesLoaded = true
}

/* Slots of an appliance */
function mideamsmartEnumOptions(_enum, _emptyLabel) {
  const context = jeeFrontEnd.mideamsmart.scheduleContext || {}
  const capabilities = jeeFrontEnd.mideamsmart.scheduleEqLogic?.configuration?.capabilities || {}
  const codes = Array.isArray(capabilities.enums?.[_enum]) ? capabilities.enums[_enum] : []
  const labels = context.enums?.[_enum] || {}
  return [['', _emptyLabel]].concat(codes.map(function(_code) {
    return [_code, labels[_code] || _code]
  }))
}

function mideamsmartNumberInput(_key, _placeholder, _value, _min, _max, _step) {
  const input = mideamsmartElement('input', 'form-control input-sm mideamsmartSlotAttr')
  input.type = 'number'
  input.setAttribute('data-key', _key)
  input.placeholder = _placeholder
  input.title = _placeholder
  if (_min != null) input.min = _min
  if (_max != null) input.max = _max
  if (_step != null) input.step = _step
  input.value = (_value == null) ? '' : _value
  input.style.width = '110px'
  return input
}

function mideamsmartSlotSettings(_slot) {
  const eqLogic = jeeFrontEnd.mideamsmart.scheduleEqLogic
  const capabilities = eqLogic?.configuration?.capabilities || {}
  const features = Array.isArray(capabilities.features) ? capabilities.features : []
  const isDehumidifier = (eqLogic?.configuration?.deviceType == 'A1')
  const settings = mideamsmartElement('div', 'mideamsmartSlotSettings')
  settings.style.display = 'flex'
  settings.style.flexWrap = 'wrap'
  settings.style.gap = '4px'
  const fields = [mideamsmartSelect('mideamsmartSlotAttr', mideamsmartEnumOptions('mode', '{{Mode inchangé}}'), _slot.mode)]
  fields[0].setAttribute('data-key', 'mode')
  if (isDehumidifier) {
    fields.push(mideamsmartNumberInput('targetHumidity', '{{Humidité (%)}}', _slot.targetHumidity, capabilities.minTargetHumidity, capabilities.maxTargetHumidity, 5))
  } else {
    fields.push(mideamsmartNumberInput('targetTemperature', '{{Consigne (°C)}}', _slot.targetTemperature, capabilities.minTargetTemperature, capabilities.maxTargetTemperature, capabilities.temperatureStep || 1))
  }
  const fanSpeed = mideamsmartSelect('mideamsmartSlotAttr', mideamsmartEnumOptions('fanSpeed', '{{Ventilation inchangée}}'), _slot.fanSpeed)
  fanSpeed.setAttribute('data-key', 'fanSpeed')
  fields.push(fanSpeed)
  if (!isDehumidifier && features.includes('preset')) {
    const preset = mideamsmartSelect('mideamsmartSlotAttr', mideamsmartEnumOptions('preset', '{{Préréglage inchangé}}'), _slot.preset)
    preset.setAttribute('data-key', 'preset')
    fields.push(preset)
  }
  fields.forEach(function(_field) {
    if (_field.tagName == 'SELECT') _field.style.width = 'auto'
    settings.appendChild(_field)
  })
  return settings
}

function mideamsmartAddSlotRow(_slot) {
  const context = jeeFrontEnd.mideamsmart.scheduleContext || {}
  const profiles = Array.isArray(context.profiles) ? context.profiles : []
  const profileOptions = profiles.map(function(_profile) {
    return [String(_profile.id), _profile.name]
  })
  if (_slot.profile && !profileOptions.some(function(_option) { return _option[0] === String(_slot.profile) })) {
    profileOptions.push([String(_slot.profile), '{{Profil supprimé}}'])
  }
  const tr = mideamsmartElement('tr', 'mideamsmartSlot')

  const profile = mideamsmartSelect('mideamsmartSlotAttr', profileOptions, _slot.profile)
  profile.setAttribute('data-key', 'profile')
  profile.addEventListener('change', mideamsmartFilterSlots)
  const tdProfile = mideamsmartElement('td')
  tdProfile.appendChild(profile)

  const tdDays = mideamsmartElement('td')
  tdDays.style.whiteSpace = 'nowrap'
  const days = Array.isArray(_slot.days) ? _slot.days.map(Number) : [1, 2, 3, 4, 5, 6, 7]
  jeeFrontEnd.mideamsmart.days.forEach(function(_day) {
    const label = mideamsmartElement('label', 'checkbox-inline')
    label.style.marginLeft = '0'
    label.style.marginRight = '12px'
    label.style.paddingLeft = '18px'
    const checkbox = mideamsmartElement('input', 'mideamsmartSlotDay')
    checkbox.type = 'checkbox'
    checkbox.value = _day[0]
    checkbox.checked = days.includes(_day[0])
    label.append(checkbox, ' ' + _day[1])
    tdDays.appendChild(label)
  })

  const time = mideamsmartElement('input', 'form-control input-sm mideamsmartSlotAttr')
  time.type = 'time'
  time.setAttribute('data-key', 'time')
  time.value = _slot.time || '08:00'
  const tdTime = mideamsmartElement('td')
  tdTime.appendChild(time)

  const action = mideamsmartSelect('mideamsmartSlotAttr', [['on', '{{Allumer}}'], ['off', '{{Éteindre}}']], _slot.action || 'on')
  action.setAttribute('data-key', 'action')
  const tdAction = mideamsmartElement('td')
  tdAction.appendChild(action)

  const settings = mideamsmartSlotSettings(_slot)
  const tdSettings = mideamsmartElement('td')
  tdSettings.appendChild(settings)
  const updateSettings = function() {
    settings.style.visibility = (action.value == 'off') ? 'hidden' : ''
  }
  action.addEventListener('change', updateSettings)
  updateSettings()

  const tdRemove = mideamsmartElement('td', 'text-center')
  tdRemove.appendChild(mideamsmartRemoveButton(function() {
    tr.remove()
    mideamsmartModified()
  }))
  tr.append(tdProfile, tdDays, tdTime, tdAction, tdSettings, tdRemove)
  tr.addEventListener('change', mideamsmartModified)
  document.querySelector('#table_mideamsmartSlots tbody').appendChild(tr)
  mideamsmartFilterSlots()
}

function mideamsmartFilterSlots() {
  const filter = document.getElementById('sel_mideamsmartSlotFilter')?.value || ''
  document.querySelectorAll('#table_mideamsmartSlots tr.mideamsmartSlot').forEach(function(_tr) {
    _tr.style.display = (filter === '' || _tr.querySelector('[data-key="profile"]').value === filter) ? '' : 'none'
  })
}

function mideamsmartGetSlots() {
  const slots = []
  document.querySelectorAll('#table_mideamsmartSlots tr.mideamsmartSlot').forEach(function(_tr) {
    const slot = { days: [] }
    _tr.querySelectorAll('.mideamsmartSlotAttr').forEach(function(_field) {
      slot[_field.getAttribute('data-key')] = _field.value
    })
    _tr.querySelectorAll('.mideamsmartSlotDay').forEach(function(_checkbox) {
      if (_checkbox.checked) slot.days.push(Number(_checkbox.value))
    })
    slots.push(slot)
  })
  return slots
}

function mideamsmartPrintSchedule(_eqLogic) {
  jeeFrontEnd.mideamsmart.scheduleEqLogic = _eqLogic
  // The catch-up is enabled by default
  if (_eqLogic.configuration?.scheduleCatchUp == null || _eqLogic.configuration.scheduleCatchUp === '') {
    document.querySelector('.eqLogicAttr[data-l2key="scheduleCatchUp"]').checked = true
  }
  document.querySelector('#table_mideamsmartSlots tbody').innerHTML = ''
  mideamsmartAjax('getScheduleContext', {}, function(_context) {
    // Another equipment may have been displayed meanwhile
    if (jeeFrontEnd.mideamsmart.scheduleEqLogic !== _eqLogic) return
    jeeFrontEnd.mideamsmart.scheduleContext = _context
    const profiles = Array.isArray(_context.profiles) ? _context.profiles : []
    const active = profiles.find(function(_profile) { return String(_profile.id) === String(_context.activeProfile) })
    document.getElementById('span_mideamsmartActiveProfile').textContent = active ? active.name : '{{Aucun}}'
    const warning = document.getElementById('div_mideamsmartSchedulerWarning')
    warning.textContent = (_context.schedulerId == null) ? '{{L\'équipement Programmation n\'existe pas : cliquez sur « Gérer les profils » pour le créer.}}' : ((_context.schedulerEnabled != 1) ? '{{L\'équipement Programmation est désactivé : aucun créneau n\'est appliqué.}}' : '')
    warning.style.display = (warning.textContent === '') ? 'none' : ''
    const filter = mideamsmartSelect('', [['', '{{Tous les profils}}']].concat(profiles.map(function(_profile) {
      return [String(_profile.id), _profile.name]
    })), '')
    filter.id = 'sel_mideamsmartSlotFilter'
    filter.classList.remove('input-sm')
    filter.addEventListener('change', mideamsmartFilterSlots)
    document.getElementById('sel_mideamsmartSlotFilter').replaceWith(filter)
    document.querySelector('#table_mideamsmartSlots tbody').innerHTML = ''
    const slots = Array.isArray(_eqLogic.configuration?.scheduleSlots) ? _eqLogic.configuration.scheduleSlots : []
    slots.forEach(mideamsmartAddSlotRow)
    jeeFrontEnd.mideamsmart.slotsLoaded = true
  })
}

document.getElementById('bt_mideamsmartScheduler')?.addEventListener('click', mideamsmartOpenScheduler)
document.getElementById('bt_mideamsmartManageProfiles')?.addEventListener('click', mideamsmartOpenScheduler)

document.getElementById('bt_mideamsmartAddProfile')?.addEventListener('click', function() {
  mideamsmartAddProfileRow({ id: '', name: '' })
  mideamsmartModified()
})

document.getElementById('bt_mideamsmartAddSlot')?.addEventListener('click', function() {
  if (!jeeFrontEnd.mideamsmart.slotsLoaded) return
  const context = jeeFrontEnd.mideamsmart.scheduleContext || {}
  // New slot in the displayed profile, or the active one
  const profile = document.getElementById('sel_mideamsmartSlotFilter')?.value || context.activeProfile || ''
  mideamsmartAddSlotRow({ profile: profile, action: 'on' })
  mideamsmartModified()
})

/* Called by the core before an equipment is saved */
function saveEqLogic(_eqLogic) {
  if (_eqLogic.logicalId == 'scheduler') {
    if (jeeFrontEnd.mideamsmart.profilesLoaded) {
      _eqLogic.configuration.profiles = []
      document.querySelectorAll('#table_mideamsmartProfiles tr.mideamsmartProfile').forEach(function(_tr) {
        _eqLogic.configuration.profiles.push({ id: _tr.getAttribute('data-profile-id'), name: _tr.querySelector('.mideamsmartProfileName').value })
      })
      _eqLogic.configuration.activeProfile = document.getElementById('sel_mideamsmartActiveProfile').value
    }
  } else if (jeeFrontEnd.mideamsmart.slotsLoaded) {
    _eqLogic.configuration.scheduleSlots = mideamsmartGetSlots()
  }
  return _eqLogic
}

/* Called by the core when an equipment is displayed */
function printEqLogic(_eqLogic) {
  const isScheduler = (_eqLogic.logicalId == 'scheduler')
  jeeFrontEnd.mideamsmart.slotsLoaded = false
  jeeFrontEnd.mideamsmart.profilesLoaded = false
  jeeFrontEnd.mideamsmart.scheduleEqLogic = null
  document.querySelectorAll('.mideamsmartDeviceOnly').forEach(function(_element) {
    _element.style.display = isScheduler ? 'none' : ''
  })
  document.querySelectorAll('.mideamsmartSchedulerOnly').forEach(function(_element) {
    _element.style.display = isScheduler ? '' : 'none'
  })
  if (isScheduler) {
    document.querySelector('a[href="#eqlogictab"]')?.click()
    mideamsmartPrintScheduler(_eqLogic)
    return
  }
  mideamsmartPrintSchedule(_eqLogic)
  const img = document.getElementById('img_mideamsmartDevice')
  if (img == null) return
  const deviceType = init(_eqLogic.configuration?.deviceType).toLowerCase()
  img.onerror = function() {
    this.onerror = null
    this.src = jeeFrontEnd.mideamsmart.defaultImage
  }
  img.src = (deviceType != '') ? 'plugins/mideamsmart/desktop/img/' + deviceType + '.png' : jeeFrontEnd.mideamsmart.defaultImage
  mideamsmartUpdateTypeFields()
  const capabilities = _eqLogic.configuration?.capabilities
  const span = document.getElementById('span_mideamsmartCapabilities')
  if (span != null) {
    span.classList.remove('label-default', 'label-success', 'label-warning')
    if (!capabilities || !capabilities.features) {
      span.textContent = '{{Inconnues : appareil pas encore joint}}'
      span.classList.add('label-default')
    } else if (capabilities.complete) {
      span.textContent = '{{Reçues de l\'appareil}}'
      span.classList.add('label-success')
    } else {
      span.textContent = '{{Par défaut : l\'appareil ne les a pas envoyées, nouvel essai automatique}}'
      span.classList.add('label-warning')
    }
  }
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
