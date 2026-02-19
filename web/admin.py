def render_admin() -> str:
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>FiltrePlante - Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; color: #2c3e50; }
        .header { background: linear-gradient(135deg, #2d8659 0%, #1a5738 100%); color: white; padding: 2rem; margin-bottom: 2rem; }
        .header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
        .header-links { display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap; }
        .header a { color: white; text-decoration: none; opacity: 0.8; }
        .header a:hover { opacity: 1; }
        .btn-manage-pumps { background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; opacity: 1 !important; }
        .btn-manage-pumps:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }
        .device-card { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.05); border-left: 4px solid #2d8659; }
        .device-id { font-family: monospace; color: #7f8c8d; margin-bottom: 1rem; font-size: 0.9rem; }
        .input-row { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; }
        .input-row label { min-width: 120px; font-weight: 600; color: #1a5738; font-size: 0.95rem; }
        .input-row input, .input-row select { flex: 1; padding: 0.6rem; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem; }
        .input-row select { background: white; }
        .input-row input:focus, .input-row select:focus { outline: none; border-color: #2d8659; }
        button { padding: 0.6rem 1.2rem; border: none; border-radius: 6px; cursor: pointer; transition: all 0.3s; }
        .btn-save { background: #2d8659; color: white; font-size: 0.9rem; margin-top: 1rem; }
        .btn-save:hover { background: #1a5738; }
        .channels { margin-left: 2rem; }
        .msg { padding: 0.8rem; border-radius: 6px; margin-bottom: 1rem; display: none; text-align: center; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .loading { text-align: center; padding: 3rem; color: #7f8c8d; }
        .invalid-input { border: 2px solid #dc3545 !important; background-color: #fff5f5 !important; }
        .col-headers { display: flex; gap: 1rem; align-items: center; margin-bottom: 0.3rem; font-size: 0.75rem; color: #888; font-weight: 600; text-transform: uppercase; }
        .col-headers .col-label { min-width: 120px; }
        .col-headers .col-name { flex: 1; }
        .col-headers .col-model { flex: 2; }
        .col-headers .col-type { width: 150px; }
        .col-headers .col-flow { width: 120px; text-align: center; }

        .btn-history { background: #6c757d; color: white; padding: 6px 14px; border-radius: 6px; font-size: 0.85rem; margin-top: 8px; margin-right: 8px; }
        .btn-history:hover { background: #5a6268; }
        .version-panel { margin-top: 15px; padding: 15px; background: #f0f2f5; border-radius: 8px; border: 1px solid #dee2e6; }
        .version-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 0.9rem; }
        .version-table th { background: #e9ecef; padding: 8px 10px; text-align: left; font-weight: 600; color: #495057; }
        .version-table td { padding: 6px 10px; border-bottom: 1px solid #dee2e6; }
        .version-table tr:hover { background: #f8f9fa; }
        .add-version-form { background: white; padding: 15px; border-radius: 8px; border: 2px solid #ffc107; margin-top: 15px; }
        .add-version-form h4 { margin: 0 0 5px 0; color: #495057; font-size: 1rem; }
        .add-version-form .warning-note { background: #fff3cd; color: #856404; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; margin-bottom: 12px; }
        .add-version-form .info-note { background: #e7f3ff; color: #004085; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; margin-bottom: 12px; }
        .version-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .version-form-grid label { display: block; font-weight: 500; color: #495057; font-size: 0.85rem; margin-bottom: 3px; }
        .version-form-grid input, .version-form-grid select { width: 100%; padding: 6px 8px; border: 1px solid #ced4da; border-radius: 4px; font-size: 0.9rem; }
        .version-form-grid .full-width { grid-column: 1 / -1; }
        .btn-create-version { background: #e67e22; color: white; padding: 8px 18px; border-radius: 6px; font-size: 0.9rem; font-weight: 500; margin-top: 8px; }
        .btn-create-version:hover { background: #d35400; }
        .no-data { color: #6c757d; font-style: italic; padding: 15px; text-align: center; }
        .section-title { font-size: 0.85rem; font-weight: 600; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; margin: 10px 0 5px 0; }
        .active-badge { background: #d4edda; color: #155724; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 600; }
        .closed-badge { background: #e2e3e5; color: #6c757d; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; }
        @media (max-width: 768px) {
            .container { padding: 0 1rem; }
            .input-row { flex-direction: column; align-items: stretch; }
            .input-row label { min-width: unset; }
            .channels { margin-left: 0; }
            .water-quality-grid { grid-template-columns: 1fr !important; }
            .version-form-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>FiltrePlante - Configuration</h1>
        <div class="header-links">
            <a href="/dashboard">&#8592; Retour au dashboard</a>
            <a href="/admin/pumps" class="btn-manage-pumps">G&#233;rer les mod&#232;les de pompes</a>
        </div>
    </div>

    <div class="container">
        <div id="msg" class="msg"></div>
        <div id="loading" class="loading">Chargement...</div>
        <div id="devices"></div>
    </div>

    <script>
        var data = [];
        var pumpModels = [];
        var currentVersionConfigs = [];

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
            html += '<option value="">-- Aucun mod\\u00e8le --</option>';
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
                container.innerHTML = '<p style="text-align:center;color:#7f8c8d;padding:2rem;">Aucun device trouv\\u00e9 dans les donn\\u00e9es.</p>';
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
                            '<div class="col-model">Mod\\u00e8le</div>' +
                            '<div class="col-type">Type de poste</div>' +
                            '<div class="col-flow">D\\u00e9bit (m3/h)</div>' +
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
                                '<input type="number" id="fr-' + safeId + '-' + safeCh + '" value="' + flowRate + '" step="0.1" min="0" placeholder="D\\u00e9bit" title="D\\u00e9bit effectif (m3/h)" style="width:120px;padding:0.6rem;border:2px solid #e0e0e0;border-radius:8px;font-size:0.95rem;">' +
                            '</div>' +
                            '<div style="margin-left:120px;margin-bottom:15px;">' +
                                '<button class="btn-history" onclick="toggleVersionHistory(\\'' + safeId + '\\', \\'' + safeCh + '\\')">&#x1F4DC; Historique des versions</button>' +
                                '<div id="vh-' + safeId + '-' + safeCh + '" style="display:none;"></div>' +
                            '</div>';
                        }).join('') +
                    '</div>' +
                    '<div style="border-top: 2px solid #e5e7eb; margin: 30px 0 20px 0; padding-top: 20px;">' +
                        '<h3 style="font-size: 1.05rem; font-weight: 600; color: #2d8659; margin-bottom: 6px;">&#x1F4A7; Qualit\\u00e9 des eaux brutes</h3>' +
                        '<p style="font-size: 0.85rem; color: #6b7280; margin-bottom: 15px;">Valeurs moyennes estim\\u00e9es des eaux du site</p>' +
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
                    showMsg('error', 'D\\u00e9bit effectif invalide pour ' + (nameInput ? nameInput.value || ch : ch));
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
                    showMsg('success', 'Device enregistr\\u00e9, mais erreur config versioning pour: ' + configErrors.join(', '));
                } else {
                    showMsg('success', 'Configuration enregistr\\u00e9e !');
                }
            } catch(e) {
                showMsg('error', 'Erreur r\\u00e9seau');
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
                    html += '<thead><tr><th>P\\u00e9riode</th><th>D\\u00e9bit</th><th>Type</th><th>DBO5/DCO/MES</th><th>V.</th><th>Statut</th></tr></thead>';
                    html += '<tbody>';
                    history.forEach(function(v) {
                        var fromDate = v.effective_from ? new Date(v.effective_from + 'T00:00:00').toLocaleDateString('fr-FR') : '?';
                        var toDate = v.effective_to ? new Date(v.effective_to + 'T00:00:00').toLocaleDateString('fr-FR') : '';
                        var period = fromDate + ' \\u2192 ' + (toDate || 'Actuel');
                        var flow = v.flow_rate ? v.flow_rate + ' m\\u00b3/h' : '-';
                        var ptype = v.pump_type || '-';
                        var water = (v.dbo5 || '-') + ' / ' + (v.dco || '-') + ' / ' + (v.mes || '-');
                        var badge = v.effective_to ? '<span class="closed-badge">Cl\\u00f4tur\\u00e9</span>' : '<span class="active-badge">Actif</span>';

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
                    '<h4>Cr\\u00e9er une nouvelle version historique</h4>' +
                    '<div class="warning-note">&#x26A0;&#xFE0F; Ceci cr\\u00e9e un changement de configuration \\u00e0 partir d\\u0027une date donn\\u00e9e. La version pr\\u00e9c\\u00e9dente sera cl\\u00f4tur\\u00e9e.</div>' +
                    '<div class="info-note">&#x1F4A1; Formulaire pr\\u00e9-rempli avec les valeurs actuelles. Modifiez seulement ce qui change.</div>' +

                    '<div class="version-form-grid">' +
                        '<div class="full-width">' +
                            '<label>Date d\\u0027effet *</label>' +
                            '<input type="date" id="nv-date-' + deviceId + '-' + channel + '" required>' +
                        '</div>' +

                        '<div>' +
                            '<label>D\\u00e9bit (m\\u00b3/h)</label>' +
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

                        '<div class="full-width"><p class="section-title">Qualit\\u00e9 des eaux brutes</p></div>' +
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
                    '<button class="btn-create-version" onclick="addConfigVersion(\\'' + deviceId + '\\', \\'' + channel + '\\')">&#x2795; Cr\\u00e9er cette version</button>' +
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
                showMsg('error', 'Date d\\u0027effet requise');
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

                showMsg('success', 'Nouvelle version cr\\u00e9\\u00e9e avec succ\\u00e8s');

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
                showMsg('error', 'Erreur r\\u00e9seau');
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
    </script>
</body>
</html>
    """


def render_pumps_admin() -> str:
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>FiltrePlante - Mod&#232;les de pompes</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; color: #2c3e50; }
        .header { background: linear-gradient(135deg, #2d8659 0%, #1a5738 100%); color: white; padding: 2rem; margin-bottom: 2rem; }
        .header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
        .header a { color: white; text-decoration: none; opacity: 0.8; }
        .header a:hover { opacity: 1; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }
        .card { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.05); border-left: 4px solid #2d8659; }
        .card h2 { color: #1a5738; margin-bottom: 1rem; font-size: 1.3rem; }
        .form-row { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; }
        .form-row label { min-width: 180px; font-weight: 600; color: #1a5738; font-size: 0.95rem; }
        .form-row input { flex: 1; padding: 0.6rem; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem; }
        .form-row input:focus { outline: none; border-color: #2d8659; }
        .form-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
        button { padding: 0.6rem 1.2rem; border: none; border-radius: 6px; cursor: pointer; transition: all 0.3s; font-size: 0.9rem; }
        .btn-primary { background: #2d8659; color: white; }
        .btn-primary:hover { background: #1a5738; }
        .btn-cancel { background: #6c757d; color: white; }
        .btn-cancel:hover { background: #545b62; }
        .btn-edit { background: #f0ad4e; color: white; padding: 0.4rem 0.8rem; font-size: 0.85rem; }
        .btn-edit:hover { background: #ec971f; }
        .btn-delete { background: #d9534f; color: white; padding: 0.4rem 0.8rem; font-size: 0.85rem; }
        .btn-delete:hover { background: #c9302c; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f1f8f4; color: #1a5738; padding: 0.8rem; text-align: left; font-weight: 600; border-bottom: 2px solid #2d8659; }
        td { padding: 0.8rem; border-bottom: 1px solid #e0e0e0; }
        tr:hover { background: #f9f9f9; }
        .actions { display: flex; gap: 0.5rem; }
        .msg { padding: 0.8rem; border-radius: 6px; margin-bottom: 1rem; display: none; text-align: center; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .empty { text-align: center; padding: 2rem; color: #7f8c8d; }
        @media (max-width: 768px) {
            .container { padding: 0 1rem; }
            .form-row { flex-direction: column; align-items: stretch; }
            .form-row label { min-width: unset; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>FiltrePlante - Mod&#232;les de pompes</h1>
        <a href="/admin">&#8592; Retour &#224; la configuration</a>
    </div>

    <div class="container">
        <div id="msg" class="msg"></div>

        <div class="card">
            <h2 id="form-title">Ajouter un nouveau mod&#232;le</h2>
            <form id="pump-form" onsubmit="handleSubmit(event)">
                <input type="hidden" id="pump-id" value="">
                <div class="form-row">
                    <label>Nom du mod&#232;le *</label>
                    <input type="text" id="pump-name" required placeholder="Ex: Pedrollo VXM 10/35">
                </div>
                <div class="form-row">
                    <label>Puissance (kW) *</label>
                    <input type="number" id="pump-power" step="0.01" min="0" required placeholder="Ex: 0.75">
                </div>
                <div class="form-row">
                    <label>Intensit&#233; &#224; 230V (A) *</label>
                    <input type="number" id="pump-current" step="0.1" min="0" required placeholder="Ex: 4.8">
                </div>
                <div class="form-row">
                    <label>D&#233;bit &#224; HMT=8 (m3/h)</label>
                    <input type="number" id="pump-flow" step="0.1" min="0" placeholder="Ex: 18.0 (vide si N/A)">
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Enregistrer</button>
                    <button type="button" class="btn-cancel" onclick="resetForm()">Annuler</button>
                </div>
            </form>
        </div>

        <div class="card">
            <h2>Mod&#232;les existants</h2>
            <table>
                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>Puissance (kW)</th>
                        <th>Intensit&#233; (A)</th>
                        <th>D&#233;bit (m3/h)</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="pumps-tbody">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        var pumps = [];

        loadPumps();

        async function loadPumps() {
            try {
                var response = await fetch('/api/config/pump-models');
                pumps = await response.json();
                renderTable();
            } catch(e) {
                showMsg('error', 'Erreur de chargement');
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function renderTable() {
            var tbody = document.getElementById('pumps-tbody');
            if (pumps.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty">Aucun mod\\u00e8le de pompe</td></tr>';
                return;
            }
            tbody.innerHTML = pumps.map(function(pump) {
                var flow = pump.flow_rate_hmt8 ? pump.flow_rate_hmt8.toFixed(1) : '-';
                return '<tr>' +
                    '<td>' + escapeHtml(pump.name) + '</td>' +
                    '<td>' + pump.power_kw.toFixed(2) + '</td>' +
                    '<td>' + pump.current_ampere.toFixed(1) + '</td>' +
                    '<td>' + flow + '</td>' +
                    '<td class="actions">' +
                        '<button class="btn-edit" onclick="editPump(' + pump.id + ')">Modifier</button>' +
                        '<button class="btn-delete" onclick="deletePump(' + pump.id + ')">Supprimer</button>' +
                    '</td>' +
                '</tr>';
            }).join('');
        }

        async function handleSubmit(e) {
            e.preventDefault();
            var pumpId = document.getElementById('pump-id').value;
            var flowVal = document.getElementById('pump-flow').value;
            var body = {
                name: document.getElementById('pump-name').value.trim(),
                power_kw: parseFloat(document.getElementById('pump-power').value),
                current_ampere: parseFloat(document.getElementById('pump-current').value),
                flow_rate_hmt8: flowVal ? parseFloat(flowVal) : null
            };

            try {
                var url, method;
                if (pumpId) {
                    url = '/api/config/pump-model/' + pumpId;
                    method = 'PUT';
                } else {
                    url = '/api/config/pump-model';
                    method = 'POST';
                }
                var res = await fetch(url, {
                    method: method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                var data = await res.json();
                if (res.ok && data.success) {
                    showMsg('success', pumpId ? 'Mod\\u00e8le modifi\\u00e9 !' : 'Mod\\u00e8le cr\\u00e9\\u00e9 !');
                    resetForm();
                    loadPumps();
                } else {
                    showMsg('error', data.error || 'Erreur');
                }
            } catch(e) {
                showMsg('error', 'Erreur r\\u00e9seau');
            }
        }

        function editPump(id) {
            var pump = pumps.find(function(p) { return p.id === id; });
            if (!pump) return;
            document.getElementById('pump-id').value = pump.id;
            document.getElementById('pump-name').value = pump.name;
            document.getElementById('pump-power').value = pump.power_kw;
            document.getElementById('pump-current').value = pump.current_ampere;
            document.getElementById('pump-flow').value = pump.flow_rate_hmt8 || '';
            document.getElementById('form-title').textContent = 'Modifier : ' + pump.name;
            window.scrollTo({top: 0, behavior: 'smooth'});
        }

        async function deletePump(id) {
            if (!confirm('Supprimer ce mod\\u00e8le ?')) return;
            try {
                var res = await fetch('/api/config/pump-model/' + id, { method: 'DELETE' });
                var data = await res.json();
                if (res.ok && data.success) {
                    showMsg('success', 'Mod\\u00e8le supprim\\u00e9 !');
                    loadPumps();
                } else {
                    showMsg('error', data.detail || data.error || 'Erreur');
                }
            } catch(e) {
                showMsg('error', 'Erreur r\\u00e9seau');
            }
        }

        function resetForm() {
            document.getElementById('pump-id').value = '';
            document.getElementById('pump-name').value = '';
            document.getElementById('pump-power').value = '';
            document.getElementById('pump-current').value = '';
            document.getElementById('pump-flow').value = '';
            document.getElementById('form-title').textContent = 'Ajouter un nouveau mod\\u00e8le';
        }

        function showMsg(type, text) {
            var el = document.getElementById('msg');
            el.className = 'msg ' + type;
            el.textContent = text;
            el.style.display = 'block';
            setTimeout(function() { el.style.display = 'none'; }, 3000);
        }
    </script>
</body>
</html>
    """
