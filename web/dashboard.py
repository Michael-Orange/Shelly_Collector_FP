def render_dashboard() -> str:
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FiltrePlante - Monitoring Pompes</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8f9fa;
            color: #2c3e50;
            line-height: 1.6;
        }

        .header {
            background: linear-gradient(135deg, #2d8659 0%, #1a5738 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .header p {
            opacity: 0.9;
            font-size: 0.95rem;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .filters {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }

        .filters-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .filter-group label {
            display: block;
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: #1a5738;
        }

        .filter-group select,
        .filter-group input {
            width: 100%;
            padding: 0.6rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 0.95rem;
            transition: border-color 0.3s;
        }

        .filter-group select:focus,
        .filter-group input:focus {
            outline: none;
            border-color: #2d8659;
        }

        .buttons {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }

        button {
            padding: 0.7rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-primary {
            background: #2d8659;
            color: white;
        }

        .btn-primary:hover {
            background: #1a5738;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(45, 134, 89, 0.3);
        }

        .btn-secondary {
            background: white;
            color: #2d8659;
            border: 2px solid #2d8659;
        }

        .btn-secondary:hover {
            background: #f0f8f4;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            border-left: 4px solid #2d8659;
        }

        .stat-card .label {
            font-size: 0.85rem;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #2d8659;
            margin-top: 0.5rem;
        }

        .table-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: #1a5738;
            color: white;
        }

        th {
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        tbody tr {
            border-bottom: 1px solid #ecf0f1;
            transition: background 0.2s;
        }

        tbody tr:hover {
            background: #f0f8f4;
        }

        tbody tr:nth-child(even) {
            background: #fafafa;
        }

        tbody tr:nth-child(even):hover {
            background: #f0f8f4;
        }

        td {
            padding: 1rem;
            font-size: 0.95rem;
        }

        .channel-badge {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .channel-switch-0 { background: #e3f2fd; color: #1976d2; }
        .channel-switch-1 { background: #f3e5f5; color: #7b1fa2; }
        .channel-switch-2 { background: #fff3e0; color: #f57c00; }

        .ongoing {
            color: #2d8659;
            font-weight: 600;
        }

        .loading {
            text-align: center;
            padding: 3rem;
            color: #7f8c8d;
        }

        .spinner {
            border: 3px solid #ecf0f1;
            border-top: 3px solid #2d8659;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .empty {
            text-align: center;
            padding: 3rem;
            color: #7f8c8d;
        }

        .sort-icon {
            opacity: 0.3;
            font-size: 0.8rem;
            margin-left: 4px;
        }

        .sort-icon::after {
            content: '\\2195';
        }

        th {
            cursor: pointer;
            user-select: none;
        }

        th:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        th.sorted-asc .sort-icon { opacity: 1; }
        th.sorted-asc .sort-icon::after { content: '\\25B2'; }

        th.sorted-desc .sort-icon { opacity: 1; }
        th.sorted-desc .sort-icon::after { content: '\\25BC'; }

        .device-id-cell {
            font-size: 0.85rem;
            color: #7f8c8d;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .header {
                padding: 1.5rem;
            }

            .header h1 {
                font-size: 1.3rem;
            }

            .filters-grid {
                grid-template-columns: 1fr;
            }

            .buttons {
                flex-direction: column;
            }

            button {
                width: 100%;
            }

            table {
                font-size: 0.85rem;
            }

            th, td {
                padding: 0.7rem 0.5rem;
            }

            .stat-card .value {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>🌱</span> FiltrePlante - Monitoring des Pompes</h1>
        <p>Suivi en temps reel des cycles de demarrage et d'arret | <a href="/admin" style="color:white;opacity:0.8;">Configuration</a></p>
    </div>

    <div class="container">
        <div class="filters">
            <div class="filters-grid">
                <div class="filter-group">
                    <label for="device-filter">Device</label>
                    <select id="device-filter" onchange="loadChannelOptions()">
                        <option value="">Tous les devices</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="channel-filter">Canal</label>
                    <select id="channel-filter">
                        <option value="">Tous les canaux</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="start-date">Date debut</label>
                    <input type="date" id="start-date">
                </div>

                <div class="filter-group">
                    <label for="end-date">Date fin</label>
                    <input type="date" id="end-date">
                </div>
            </div>

            <div class="buttons">
                <button class="btn-primary" onclick="loadCycles()">Rafraichir</button>
                <button class="btn-secondary" onclick="exportCSV()">Exporter CSV</button>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="label">Total cycles</div>
                <div class="value" id="stat-total">-</div>
            </div>
            <div class="stat-card">
                <div class="label">En cours</div>
                <div class="value" id="stat-ongoing">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Duree moyenne</div>
                <div class="value" id="stat-avg-duration">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Puissance moy.</div>
                <div class="value" id="stat-avg-power">-</div>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="label">Max Amperes</div>
                <div class="value" id="stat-max-current">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Min Amperes</div>
                <div class="value" id="stat-min-current">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Max Watts</div>
                <div class="value" id="stat-max-power">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Min Watts</div>
                <div class="value" id="stat-min-power">-</div>
            </div>
        </div>

        <div class="table-container">
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p>Chargement des donnees...</p>
            </div>

            <div id="table-wrapper" style="display: none;">
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortTable('device_id', 0)">Device <span class="sort-icon"></span></th>
                            <th onclick="sortTable('channel', 1)">Canal <span class="sort-icon"></span></th>
                            <th onclick="sortTable('start_time', 2)">Date <span class="sort-icon"></span></th>
                            <th onclick="sortTable('start_time', 3)">Demarrage <span class="sort-icon"></span></th>
                            <th onclick="sortTable('end_time', 4)">Arret <span class="sort-icon"></span></th>
                            <th onclick="sortTable('duration_minutes', 5)">Duree <span class="sort-icon"></span></th>
                            <th onclick="sortTable('avg_power_w', 6)">Puissance moy. <span class="sort-icon"></span></th>
                        </tr>
                    </thead>
                    <tbody id="cycles-tbody">
                    </tbody>
                </table>
            </div>

            <div id="empty" class="empty" style="display: none;">
                <p>Aucun cycle trouve pour cette periode</p>
            </div>
        </div>
    </div>

    <script>
        let currentData = null;
        let originalCycles = null;
        let currentSort = { column: null, direction: 'asc' };

        document.addEventListener('DOMContentLoaded', () => {
            const today = new Date();
            const startDate = new Date(today);
            startDate.setDate(today.getDate() - 45);

            document.getElementById('start-date').valueAsDate = startDate;
            document.getElementById('end-date').valueAsDate = today;

            loadCycles();
            loadDevices();
        });

        function getDeviceName(deviceId) {
            var configs = (currentData && currentData.configs) || {};
            var cfg = configs[deviceId];
            return (cfg && cfg.device_name) ? cfg.device_name : deviceId;
        }

        function getChannelName(deviceId, channel) {
            var configs = (currentData && currentData.configs) || {};
            var cfg = configs[deviceId];
            if (cfg && cfg.channels && cfg.channels[channel]) return cfg.channels[channel];
            return channel;
        }

        let allDevicesData = [];

        async function loadDevices() {
            try {
                const response = await fetch('/api/config/devices');
                if (!response.ok) return;
                const data = await response.json();

                allDevicesData = data.devices || [];

                if (allDevicesData.length > 0) {
                    const select = document.getElementById('device-filter');
                    allDevicesData.forEach(device => {
                        const option = document.createElement('option');
                        option.value = device.device_id;
                        option.textContent = device.device_name || device.device_id;
                        select.appendChild(option);
                    });
                }

                loadChannelOptions();
            } catch (e) {
                console.error('Error loading devices:', e);
            }
        }

        function loadChannelOptions() {
            const select = document.getElementById('channel-filter');
            const selectedDeviceId = document.getElementById('device-filter').value;

            select.innerHTML = '<option value="">Tous les canaux</option>';

            if (allDevicesData.length === 0) return;

            const devices = selectedDeviceId
                ? allDevicesData.filter(d => d.device_id === selectedDeviceId)
                : allDevicesData;

            devices.forEach(device => {
                const channelNames = device.channel_names || {};

                device.channels.forEach(channel => {
                    const option = document.createElement('option');
                    option.value = channel;
                    const displayName = channelNames[channel] || channel;
                    option.textContent = (devices.length > 1 && !selectedDeviceId)
                        ? '[' + (device.device_name || device.device_id) + '] ' + displayName
                        : displayName;
                    select.appendChild(option);
                });
            });
        }

        async function loadCycles() {
            const channel = document.getElementById('channel-filter').value;
            const deviceId = document.getElementById('device-filter').value;
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;

            document.getElementById('loading').style.display = 'block';
            document.getElementById('table-wrapper').style.display = 'none';
            document.getElementById('empty').style.display = 'none';

            try {
                let url = '/api/pump-cycles?';
                if (deviceId) url += `device_id=${deviceId}&`;
                if (channel) url += `channel=${channel}&`;
                if (startDate) url += `start_date=${startDate}T00:00:00Z&`;
                if (endDate) url += `end_date=${endDate}T23:59:59Z&`;

                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const data = await response.json();

                currentData = data;
                originalCycles = data.cycles.slice();

                document.getElementById('loading').style.display = 'none';

                if (data.cycles.length === 0) {
                    document.getElementById('empty').style.display = 'block';
                    updateStats([]);
                    return;
                }

                document.getElementById('table-wrapper').style.display = 'block';
                renderTable(data.cycles);
                updateStats(data.cycles);

            } catch (error) {
                console.error('Erreur:', error);
                document.getElementById('loading').style.display = 'none';
                alert('Erreur lors du chargement des donnees: ' + error.message);
            }
        }

        function formatDate(isoStr) {
            try {
                const d = new Date(isoStr);
                if (isNaN(d.getTime())) return 'N/A';
                const day = String(d.getUTCDate()).padStart(2, '0');
                const month = String(d.getUTCMonth() + 1).padStart(2, '0');
                const year = d.getUTCFullYear();
                return day + '/' + month + '/' + year;
            } catch (e) {
                return 'N/A';
            }
        }

        function formatTime(isoStr) {
            try {
                const d = new Date(isoStr);
                if (isNaN(d.getTime())) return 'N/A';
                const hours = String(d.getUTCHours()).padStart(2, '0');
                const minutes = String(d.getUTCMinutes()).padStart(2, '0');
                return hours + 'h' + minutes;
            } catch (e) {
                return 'N/A';
            }
        }

        function renderTable(cycles) {
            const tbody = document.getElementById('cycles-tbody');
            tbody.innerHTML = '';

            cycles.forEach(cycle => {
                const row = document.createElement('tr');

                const deviceId = cycle.device_id || 'N/A';
                const deviceName = getDeviceName(deviceId);
                const deviceCell = '<td class="device-id-cell" title="' + deviceId + '">' + deviceName + '</td>';

                const channelName = getChannelName(deviceId, cycle.channel);
                const channelClass = 'channel-' + cycle.channel.replace(':', '-');
                const channelCell = '<td><span class="channel-badge ' + channelClass + '" title="' + cycle.channel + '">' + channelName + '</span></td>';

                const dateStr = formatDate(cycle.start_time);
                const startTimeStr = formatTime(cycle.start_time);

                let endTimeStr;
                if (cycle.is_ongoing) {
                    endTimeStr = '<span class="ongoing">En cours</span>';
                } else if (cycle.end_time) {
                    endTimeStr = formatTime(cycle.end_time);
                } else {
                    endTimeStr = '-';
                }

                const durationStr = cycle.duration_minutes + ' min';
                const powerStr = cycle.avg_power_w + ' W';

                row.innerHTML =
                    deviceCell +
                    channelCell +
                    '<td>' + dateStr + '</td>' +
                    '<td>' + startTimeStr + '</td>' +
                    '<td>' + endTimeStr + '</td>' +
                    '<td>' + durationStr + '</td>' +
                    '<td>' + powerStr + '</td>';

                tbody.appendChild(row);
            });
        }

        function updateStats(cycles) {
            const total = cycles.length;
            const ongoing = cycles.filter(c => c.is_ongoing).length;

            let totalDuration = 0;
            let totalPower = 0;
            cycles.forEach(c => {
                totalDuration += c.duration_minutes;
                totalPower += c.avg_power_w;
            });

            const avgDuration = total > 0 ? Math.round(totalDuration / total) : 0;
            const avgPower = total > 0 ? Math.round(totalPower / total) : 0;

            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-ongoing').textContent = ongoing;
            document.getElementById('stat-avg-duration').textContent = avgDuration + ' min';
            document.getElementById('stat-avg-power').textContent = avgPower + ' W';

            if (currentData && currentData.stats) {
                var s = currentData.stats;
                document.getElementById('stat-max-current').textContent = s.max_current + ' A';
                document.getElementById('stat-min-current').textContent = s.min_current + ' A';
                document.getElementById('stat-max-power').textContent = s.max_power + ' W';
                document.getElementById('stat-min-power').textContent = s.min_power + ' W';
            } else {
                document.getElementById('stat-max-current').textContent = '-';
                document.getElementById('stat-min-current').textContent = '-';
                document.getElementById('stat-max-power').textContent = '-';
                document.getElementById('stat-min-power').textContent = '-';
            }
        }

        function sortTable(column, thIndex) {
            if (!currentData || !currentData.cycles.length) return;

            if (currentSort.column === column && currentSort.thIndex === thIndex) {
                if (currentSort.direction === 'desc') {
                    currentSort.direction = 'asc';
                } else {
                    currentSort.column = null;
                    currentSort.thIndex = null;
                    currentSort.direction = 'asc';
                    renderTable(originalCycles || currentData.cycles);
                    updateSortIcons();
                    return;
                }
            } else {
                currentSort.column = column;
                currentSort.thIndex = thIndex;
                currentSort.direction = 'desc';
            }

            var sorted = (originalCycles || currentData.cycles).slice().sort(function(a, b) {
                var valA = a[column];
                var valB = b[column];
                if (valA == null) return 1;
                if (valB == null) return -1;
                var mult = currentSort.direction === 'asc' ? 1 : -1;
                return valA > valB ? mult : valA < valB ? -mult : 0;
            });

            renderTable(sorted);
            updateSortIcons();
        }

        function updateSortIcons() {
            document.querySelectorAll('thead th').forEach(function(th) {
                th.classList.remove('sorted-asc', 'sorted-desc');
            });
            if (currentSort.thIndex != null) {
                var ths = document.querySelectorAll('thead th');
                if (ths[currentSort.thIndex]) {
                    ths[currentSort.thIndex].classList.add('sorted-' + currentSort.direction);
                }
            }
        }

        function exportCSV() {
            if (!currentData || currentData.cycles.length === 0) {
                alert('Aucune donnee a exporter');
                return;
            }

            let csv = 'Device;Canal;Date;Heure demarrage;Heure arret;Duree (min);Puissance moyenne (W);Statut\\n';

            currentData.cycles.forEach(cycle => {
                const deviceId = cycle.device_id || 'N/A';
                const deviceName = getDeviceName(deviceId);
                const channelName = getChannelName(deviceId, cycle.channel);
                const dateStr = formatDate(cycle.start_time);
                const startTimeStr = formatTime(cycle.start_time);

                let endTimeStr = '';
                let status = 'Termine';
                if (cycle.is_ongoing) {
                    endTimeStr = '-';
                    status = 'En cours';
                } else if (cycle.end_time) {
                    endTimeStr = formatTime(cycle.end_time);
                } else {
                    endTimeStr = '-';
                }

                csv += deviceName + ';' + channelName + ';' + dateStr + ';' + startTimeStr + ';' + endTimeStr + ';' + cycle.duration_minutes + ';' + cycle.avg_power_w + ';' + status + '\\n';
            });

            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'cycles_pompes_filtreplante_' + new Date().toISOString().split('T')[0] + '.csv';
            link.click();
        }
    </script>
</body>
</html>
    """
