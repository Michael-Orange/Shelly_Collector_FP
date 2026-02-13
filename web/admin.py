def render_admin() -> str:
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FiltrePlante - Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; color: #2c3e50; }
        .header { background: linear-gradient(135deg, #2d8659 0%, #1a5738 100%); color: white; padding: 2rem; margin-bottom: 2rem; }
        .header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
        .header a { color: white; text-decoration: none; opacity: 0.8; }
        .header a:hover { opacity: 1; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }
        .device-card { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.05); border-left: 4px solid #2d8659; }
        .device-id { font-family: monospace; color: #7f8c8d; margin-bottom: 1rem; font-size: 0.9rem; }
        .input-row { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; }
        .input-row label { min-width: 120px; font-weight: 600; color: #1a5738; font-size: 0.95rem; }
        .input-row input { flex: 1; padding: 0.6rem; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95rem; }
        .input-row input:focus { outline: none; border-color: #2d8659; }
        button { padding: 0.6rem 1.2rem; border: none; border-radius: 6px; cursor: pointer; transition: all 0.3s; }
        .btn-save { background: #2d8659; color: white; font-size: 0.9rem; }
        .btn-save:hover { background: #1a5738; }
        .channels { margin-left: 2rem; }
        .msg { padding: 0.8rem; border-radius: 6px; margin-bottom: 1rem; display: none; text-align: center; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .loading { text-align: center; padding: 3rem; color: #7f8c8d; }
        @media (max-width: 768px) {
            .container { padding: 0 1rem; }
            .input-row { flex-direction: column; align-items: stretch; }
            .input-row label { min-width: unset; }
            .channels { margin-left: 0; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌱 FiltrePlante - Configuration</h1>
        <p><a href="/dashboard">&#8592; Retour au dashboard</a></p>
    </div>

    <div class="container">
        <div id="msg" class="msg"></div>
        <div id="loading" class="loading">Chargement...</div>
        <div id="devices"></div>
    </div>

    <script>
        let data = [];

        fetch('/api/config/devices')
            .then(r => r.json())
            .then(d => {
                data = d.devices;
                document.getElementById('loading').style.display = 'none';
                render();
            })
            .catch(e => {
                document.getElementById('loading').textContent = 'Erreur de chargement';
            });

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function render() {
            const container = document.getElementById('devices');
            if (data.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#7f8c8d;padding:2rem;">Aucun device trouve dans les donnees.</p>';
                return;
            }
            container.innerHTML = data.map(device => {
                const deviceName = escapeHtml(device.device_name || '');
                const safeId = escapeHtml(device.device_id);
                return '<div class="device-card">' +
                    '<div class="device-id">' + safeId + '</div>' +
                    '<div class="input-row">' +
                        '<label>Nom device:</label>' +
                        '<input id="dn-' + safeId + '" value="' + deviceName + '" placeholder="Ex: Client 1">' +
                        '<button class="btn-save" onclick="saveDev(\\'' + safeId + '\\')">Enregistrer</button>' +
                    '</div>' +
                    '<div class="channels">' +
                        device.channels.map(ch => {
                            var chName = escapeHtml((device.channel_names && device.channel_names[ch]) || '');
                            var safeCh = escapeHtml(ch);
                            return '<div class="input-row">' +
                                '<label>' + safeCh + ':</label>' +
                                '<input id="cn-' + safeId + '-' + safeCh + '" value="' + chName + '" placeholder="Ex: Pompe PR">' +
                                '<button class="btn-save" onclick="saveCh(\\'' + safeId + '\\',\\'' + safeCh + '\\')">Enregistrer</button>' +
                            '</div>';
                        }).join('') +
                    '</div>' +
                '</div>';
            }).join('');
        }

        async function saveDev(deviceId) {
            var input = document.getElementById('dn-' + deviceId);
            var name = input ? input.value.trim() : '';
            try {
                var res = await fetch('/api/config/device', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_id: deviceId, device_name: name})
                });
                showMsg(res.ok ? 'success' : 'error', res.ok ? 'Enregistre !' : 'Erreur');
            } catch(e) {
                showMsg('error', 'Erreur reseau');
            }
        }

        async function saveCh(deviceId, channel) {
            var input = document.getElementById('cn-' + deviceId + '-' + channel);
            var name = input ? input.value.trim() : '';
            try {
                var res = await fetch('/api/config/channel', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_id: deviceId, channel: channel, channel_name: name})
                });
                showMsg(res.ok ? 'success' : 'error', res.ok ? 'Enregistre !' : 'Erreur');
            } catch(e) {
                showMsg('error', 'Erreur reseau');
            }
        }

        function showMsg(type, text) {
            var el = document.getElementById('msg');
            el.className = 'msg ' + type;
            el.textContent = text;
            el.style.display = 'block';
            setTimeout(function() { el.style.display = 'none'; }, 2000);
        }
    </script>
</body>
</html>
    """
