var data = [];
var pumpModels = [];
var currentVersionConfigs = [];

async function checkExistingSession() {
    try {
        var res = await fetch('/api/admin/check-session');
        if (res.ok) {
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('admin-content').style.display = 'block';
            loadAdminData();
        }
    } catch(e) {}
}
checkExistingSession();

async function adminLogout() {
    try { await fetch('/api/admin/logout', { method: 'POST' }); } catch(e) {}
    window.location.href = '/dashboard';
}

async function adminLogin() {
    var pw = document.getElementById('admin-password').value;
    var errEl = document.getElementById('login-error');
    try {
        var res = await fetch('/api/admin/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: pw})
        });
        if (res.ok) {
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('admin-content').style.display = 'block';
            loadAdminData();
        } else {
            errEl.style.display = 'block';
            document.getElementById('admin-password').value = '';
            document.getElementById('admin-password').focus();
        }
    } catch(e) {
        errEl.textContent = 'Erreur réseau';
        errEl.style.display = 'block';
    }
}

function loadAdminData() {
    Promise.all([
        fetch('/api/config/devices').then(function(r) { return r.json(); }),
        fetch('/api/config/pump-models').then(function(r) { return r.json(); }),
        fetch('/api/config/current').then(function(r) { return r.json(); })
    ]).then(function(results) {
        data = results[0].devices;
        pumpModels = results[1];
        currentVersionConfigs = results[2].configs || [];
        document.getElementById('loading').style.display = 'none';
        render();
    }).catch(function(e) {
        document.getElementById('loading').textContent = 'Erreur de chargement';
        console.error(e);
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatPumpOption(pump) {
    var flowInfo = pump.flow_rate_hmt8 ? ', ' + pump.flow_rate_hmt8 + ' m3/h si HMT 8' : '';
    return pump.name + ' (' + pump.power_kw.toFixed(2) + ' kW, ' + pump.current_ampere.toFixed(1) + ' A' + flowInfo + ')';
}

function buildPumpSelect(selectId, selectedModelId) {
    var html = '<select id="' + selectId + '" style="flex:2;padding:0.6rem;border:2px solid #e0e0e0;border-radius:8px;font-size:0.95rem;background:white;">';
    html += '<option value="">-- Aucun modèle --</option>';
    pumpModels.forEach(function(pump) {
        var selected = (selectedModelId && selectedModelId == pump.id) ? ' selected' : '';
        html += '<option value="' + pump.id + '"' + selected + '>' + escapeHtml(formatPumpOption(pump)) + '</option>';
    });
    html += '</select>';
    return html;
}

function getVersionConfig(deviceId, channel) {
    return currentVersionConfigs.find(function(c) {
        return c.device_id === deviceId && c.channel === channel;
    });
}

function render() {
    var container = document.getElementById('devices');
    if (data.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:#7f8c8d;padding:2rem;">Aucun device trouvé dans les données.</p>';
        return;
    }
    container.innerHTML = data.map(function(device) {
        var deviceName = escapeHtml(device.device_name || '');
        var safeId = escapeHtml(device.device_id);
        var channelConfigs = device.channel_configs || {};
        var channelNames = device.channel_names || {};

        return '<div class="device-card">' +
            '<div class="device-id">' + safeId + '</div>' +
            '<div class="input-row">' +
                '<label>Nom device:</label>' +
                '<input id="dn-' + safeId + '" value="' + deviceName + '" placeholder="Ex: Client 1">' +
            '</div>' +
            '<div class="channels">' +
                '<div class="col-headers">' +
                    '<div class="col-label"></div>' +
                    '<div class="col-name">Nom</div>' +
                    '<div class="col-model">Modèle</div>' +
                    '<div class="col-type">Type de poste</div>' +
                    '<div class="col-flow">Débit (m3/h)</div>' +
                '</div>' +
                device.channels.map(function(ch) {
                    var safeCh = escapeHtml(ch);
                    var chConfig = channelConfigs[ch] || {};
                    var chName = escapeHtml(chConfig.channel_name || channelNames[ch] || '');
                    var pumpModelId = chConfig.pump_model_id || null;
                    var flowRate = (chConfig.flow_rate != null && !isNaN(chConfig.flow_rate)) ? parseFloat(Number(chConfig.flow_rate).toFixed(2)) : '';
                    var pumpType = chConfig.pump_type || 'relevage';
                    var selectId = 'pm-' + safeId + '-' + safeCh;
                    var typeId = 'pt-' + safeId + '-' + safeCh;

                    return '<div class="input-row">' +
                        '<label>' + safeCh + ':</label>' +
                        '<input id="cn-' + safeId + '-' + safeCh + '" value="' + chName + '" placeholder="Ex: Pompe PR" style="flex:1;">' +
                        buildPumpSelect(selectId, pumpModelId) +
                        '<select id="' + typeId + '" style="width:150px;padding:0.6rem;border:2px solid #e0e0e0;border-radius:8px;font-size:0.95rem;background:white;">' +
                            '<option value="relevage"' + (pumpType === 'relevage' ? ' selected' : '') + '>Relevage</option>' +
                            '<option value="sortie"' + (pumpType === 'sortie' ? ' selected' : '') + '>Sortie</option>' +
                            '<option value="autre"' + (pumpType === 'autre' ? ' selected' : '') + '>Autre</option>' +
                        '</select>' +
                        '<input type="number" id="fr-' + safeId + '-' + safeCh + '" value="' + flowRate + '" step="0.1" min="0" placeholder="Débit" title="Débit effectif (m3/h)" style="width:120px;padding:0.6rem;border:2px solid #e0e0e0;border-radius:8px;font-size:0.95rem;">' +
                    '</div>' +
                    '<div style="margin-left:120px;margin-bottom:15px;">' +
                        '<button class="btn-history" onclick="toggleVersionHistory(\'' + safeId + '\', \'' + safeCh + '\')">&#x1F4DC; Historique des versions</button>' +
                        '<div id="vh-' + safeId + '-' + safeCh + '" style="display:none;"></div>' +
                    '</div>';
                }).join('') +
            '</div>' +
            '<div style="border-top: 2px solid #e5e7eb; margin: 30px 0 20px 0; padding-top: 20px;">' +
                '<h3 style="font-size: 1.05rem; font-weight: 600; color: #2d8659; margin-bottom: 6px;">&#x1F4A7; Qualité des eaux brutes</h3>' +
                '<p style="font-size: 0.85rem; color: #6b7280; margin-bottom: 15px;">Valeurs moyennes estimées des eaux du site</p>' +
            '</div>' +
            '<div class="water-quality-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #2d8659; margin-bottom: 1rem;">' +
                '<div>' +
                    '<label style="display: block; font-weight: 500; color: #374151; margin-bottom: 6px; font-size: 0.9rem;">DBO5 (mg/L)</label>' +
                    '<input type="number" id="dbo5-' + safeId + '" value="' + (device.dbo5_mg_l || 570) + '" min="0" max="5000" step="10" style="width: 100%; padding: 0.6rem; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem;">' +
                '</div>' +
                '<div>' +
                    '<label style="display: block; font-weight: 500; color: #374151; margin-bottom: 6px; font-size: 0.9rem;">DCO (mg/L)</label>' +
                    '<input type="number" id="dco-' + safeId + '" value="' + (device.dco_mg_l || 1250) + '" min="0" max="10000" step="10" style="width: 100%; padding: 0.6rem; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem;">' +
                '</div>' +
                '<div>' +
                    '<label style="display: block; font-weight: 500; color: #374151; margin-bottom: 6px; font-size: 0.9rem;">MES (mg/L)</label>' +
                    '<input type="number" id="mes-' + safeId + '" value="' + (device.mes_mg_l || 650) + '" min="0" max="5000" step="10" style="width: 100%; padding: 0.6rem; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem;">' +
                '</div>' +
            '</div>' +
            '<button class="btn-save" data-device="' + safeId + '" data-channels="' + encodeURIComponent(JSON.stringify(device.channels)) + '" onclick="saveDevice(this.dataset.device, JSON.parse(decodeURIComponent(this.dataset.channels)))">Enregistrer tout</button>' +
        '</div>';
    }).join('');
}

async function saveDevice(deviceId, channels) {
    var deviceNameInput = document.getElementById('dn-' + deviceId);
    var deviceName = deviceNameInput ? deviceNameInput.value.trim() : '';

    var channelData = [];
    for (var i = 0; i < channels.length; i++) {
        var ch = channels[i];
        var nameInput = document.getElementById('cn-' + deviceId + '-' + ch);
        var modelSelect = document.getElementById('pm-' + deviceId + '-' + ch);
        var flowInput = document.getElementById('fr-' + deviceId + '-' + ch);
        var typeSelect = document.getElementById('pt-' + deviceId + '-' + ch);
        var pumpModelId = modelSelect ? modelSelect.value : '';
        var flowVal = flowInput ? flowInput.value.trim() : '';
        var pumpType = typeSelect ? typeSelect.value : 'relevage';

        if (flowVal !== '' && (isNaN(parseFloat(flowVal)) || parseFloat(flowVal) < 0)) {
            flowInput.classList.add('invalid-input');
            flowInput.focus();
            showMsg('error', 'Débit effectif invalide pour ' + (nameInput ? nameInput.value || ch : ch));
            return;
        }
        if (flowInput) flowInput.classList.remove('invalid-input');

        channelData.push({
            channel: ch,
            name: nameInput ? nameInput.value.trim() : '',
            pump_model_id: pumpModelId ? parseInt(pumpModelId) : null,
            flow_rate: flowVal !== '' ? parseFloat(flowVal) : null,
            pump_type: pumpType
        });
    }

    var dbo5Input = document.getElementById('dbo5-' + deviceId);
    var dcoInput = document.getElementById('dco-' + deviceId);
    var mesInput = document.getElementById('mes-' + deviceId);
    var dbo5Val = dbo5Input ? parseInt(dbo5Input.value) || 570 : 570;
    var dcoVal = dcoInput ? parseInt(dcoInput.value) || 1250 : 1250;
    var mesVal = mesInput ? parseInt(mesInput.value) || 650 : 650;

    try {
        var res = await fetch('/api/config/device', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                device_id: deviceId,
                device_name: deviceName,
                channels: channelData,
                dbo5_mg_l: dbo5Val,
                dco_mg_l: dcoVal,
                mes_mg_l: mesVal
            })
        });
        if (!res.ok) {
            var errData = await res.json().catch(function() { return {}; });
            showMsg('error', errData.detail || 'Erreur');
            return;
        }

        var configErrors = [];
        for (var j = 0; j < channelData.length; j++) {
            var cd = channelData[j];
            try {
                var configRes = await fetch('/api/config/current', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        device_id: deviceId,
                        channel: cd.channel,
                        channel_name: cd.name || null,
                        pump_model_id: cd.pump_model_id,
                        flow_rate: cd.flow_rate,
                        pump_type: cd.pump_type,
                        dbo5: dbo5Val,
                        dco: dcoVal,
                        mes: mesVal
                    })
                });
                if (!configRes.ok) {
                    configErrors.push(cd.channel);
                }
            } catch(ce) {
                configErrors.push(cd.channel);
            }
        }

        var openPanels = document.querySelectorAll('[id^="vh-"]');
        openPanels.forEach(function(p) {
            if (p.style.display !== 'none') {
                p.style.display = 'none';
                p.innerHTML = '';
            }
        });

        if (configErrors.length > 0) {
            showMsg('success', 'Device enregistré, mais erreur config versioning pour: ' + configErrors.join(', '));
        } else {
            showMsg('success', 'Configuration enregistrée !');
        }
    } catch(e) {
        showMsg('error', 'Erreur réseau');
    }
}

async function toggleVersionHistory(deviceId, channel) {
    var panel = document.getElementById('vh-' + deviceId + '-' + channel);
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        panel.innerHTML = '<p style="color:#7f8c8d;padding:10px;">Chargement...</p>';
        await loadVersionHistory(deviceId, channel);
    } else {
        panel.style.display = 'none';
    }
}

async function loadVersionHistory(deviceId, channel) {
    var panel = document.getElementById('vh-' + deviceId + '-' + channel);
    try {
        var response = await fetch('/api/config/history?device_id=' + encodeURIComponent(deviceId) + '&channel=' + encodeURIComponent(channel));
        var result = await response.json();
        var history = result.history || [];

        var html = '<div class="version-panel">';

        if (history.length === 0) {
            html += '<p class="no-data">Aucune version historique</p>';
        } else {
            html += '<table class="version-table">';
            html += '<thead><tr><th>Période</th><th>Débit</th><th>Type</th><th>DBO5/DCO/MES</th><th>V.</th><th>Statut</th></tr></thead>';
            html += '<tbody>';
            history.forEach(function(v) {
                var fromDate = v.effective_from ? new Date(v.effective_from + 'T00:00:00').toLocaleDateString('fr-FR') : '?';
                var toDate = v.effective_to ? new Date(v.effective_to + 'T00:00:00').toLocaleDateString('fr-FR') : '';
                var period = fromDate + ' → ' + (toDate || 'Actuel');
                var flow = v.flow_rate ? v.flow_rate + ' m³/h' : '-';
                var ptype = v.pump_type || '-';
                var water = (v.dbo5 || '-') + ' / ' + (v.dco || '-') + ' / ' + (v.mes || '-');
                var badge = v.effective_to ? '<span class="closed-badge">Clôturé</span>' : '<span class="active-badge">Actif</span>';

                html += '<tr>' +
                    '<td><strong>' + period + '</strong></td>' +
                    '<td>' + flow + '</td>' +
                    '<td>' + ptype + '</td>' +
                    '<td>' + water + '</td>' +
                    '<td>v' + v.version + '</td>' +
                    '<td>' + badge + '</td>' +
                '</tr>';
            });
            html += '</tbody></table>';
        }

        var vc = getVersionConfig(deviceId, channel);
        var prefillFlow = (vc && vc.flow_rate != null) ? vc.flow_rate : '';
        var prefillType = (vc && vc.pump_type) ? vc.pump_type : 'relevage';
        var prefillDbo5 = (vc && vc.dbo5 != null) ? vc.dbo5 : '';
        var prefillDco = (vc && vc.dco != null) ? vc.dco : '';
        var prefillMes = (vc && vc.mes != null) ? vc.mes : '';

        html += '<div class="add-version-form">' +
            '<h4>Créer une nouvelle version historique</h4>' +
            '<div class="warning-note">&#x26A0;&#xFE0F; Ceci crée un changement de configuration à partir d\'une date donnée. La version précédente sera clôturée.</div>' +
            '<div class="info-note">&#x1F4A1; Formulaire pré-rempli avec les valeurs actuelles. Modifiez seulement ce qui change.</div>' +

            '<div class="version-form-grid">' +
                '<div class="full-width">' +
                    '<label>Date d\'effet *</label>' +
                    '<input type="date" id="nv-date-' + deviceId + '-' + channel + '" required>' +
                '</div>' +

                '<div>' +
                    '<label>Débit (m³/h)</label>' +
                    '<input type="number" id="nv-flow-' + deviceId + '-' + channel + '" step="0.1" min="0.1" value="' + prefillFlow + '">' +
                '</div>' +
                '<div>' +
                    '<label>Type de poste</label>' +
                    '<select id="nv-type-' + deviceId + '-' + channel + '">' +
                        '<option value="relevage"' + (prefillType === 'relevage' ? ' selected' : '') + '>Relevage</option>' +
                        '<option value="sortie"' + (prefillType === 'sortie' ? ' selected' : '') + '>Sortie</option>' +
                        '<option value="autre"' + (prefillType === 'autre' ? ' selected' : '') + '>Autre</option>' +
                    '</select>' +
                '</div>' +

                '<div class="full-width"><p class="section-title">Qualité des eaux brutes</p></div>' +
                '<div>' +
                    '<label>DBO5 (mg/L)</label>' +
                    '<input type="number" id="nv-dbo5-' + deviceId + '-' + channel + '" value="' + prefillDbo5 + '">' +
                '</div>' +
                '<div>' +
                    '<label>DCO (mg/L)</label>' +
                    '<input type="number" id="nv-dco-' + deviceId + '-' + channel + '" value="' + prefillDco + '">' +
                '</div>' +
                '<div>' +
                    '<label>MES (mg/L)</label>' +
                    '<input type="number" id="nv-mes-' + deviceId + '-' + channel + '" value="' + prefillMes + '">' +
                '</div>' +
            '</div>' +
            '<button class="btn-create-version" onclick="addConfigVersion(\'' + deviceId + '\', \'' + channel + '\')">&#x2795; Créer cette version</button>' +
        '</div>';

        html += '</div>';
        panel.innerHTML = html;
    } catch(e) {
        panel.innerHTML = '<p style="color:#dc3545;padding:10px;">Erreur de chargement</p>';
        console.error(e);
    }
}

function parseFloatOrNull(val) {
    var parsed = parseFloat(val);
    return isNaN(parsed) ? null : parsed;
}

function parseIntOrNull(val) {
    var parsed = parseInt(val);
    return isNaN(parsed) ? null : parsed;
}

async function addConfigVersion(deviceId, channel) {
    var dateInput = document.getElementById('nv-date-' + deviceId + '-' + channel);
    var effectiveDate = dateInput ? dateInput.value : '';

    if (!effectiveDate) {
        showMsg('error', 'Date d\'effet requise');
        return;
    }

    var flowRate = parseFloatOrNull(document.getElementById('nv-flow-' + deviceId + '-' + channel).value);
    var pumpType = document.getElementById('nv-type-' + deviceId + '-' + channel).value || null;
    var dbo5 = parseIntOrNull(document.getElementById('nv-dbo5-' + deviceId + '-' + channel).value);
    var dco = parseIntOrNull(document.getElementById('nv-dco-' + deviceId + '-' + channel).value);
    var mes = parseIntOrNull(document.getElementById('nv-mes-' + deviceId + '-' + channel).value);

    var payload = {
        device_id: deviceId,
        channel: channel,
        effective_from: effectiveDate,
        flow_rate: flowRate,
        pump_type: pumpType,
        dbo5: dbo5,
        dco: dco,
        mes: mes
    };

    try {
        var res = await fetch('/api/config/version', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            var errData = await res.json().catch(function() { return {}; });
            showMsg('error', errData.detail || 'Erreur');
            return;
        }

        showMsg('success', 'Nouvelle version créée avec succès');

        var updatedRes = await fetch('/api/config/current');
        var updatedData = await updatedRes.json();
        currentVersionConfigs = updatedData.configs || [];

        var flowInput = document.getElementById('fr-' + deviceId + '-' + channel);
        var typeSelect = document.getElementById('pt-' + deviceId + '-' + channel);
        var vc = getVersionConfig(deviceId, channel);
        if (vc && flowInput) flowInput.value = vc.flow_rate || '';
        if (vc && typeSelect) typeSelect.value = vc.pump_type || 'relevage';

        await loadVersionHistory(deviceId, channel);
    } catch(e) {
        showMsg('error', 'Erreur réseau');
        console.error(e);
    }
}

function showMsg(type, text) {
    var el = document.getElementById('msg');
    el.className = 'msg ' + type;
    el.textContent = text;
    el.style.display = 'block';
    setTimeout(function() { el.style.display = 'none'; }, 3000);
}
