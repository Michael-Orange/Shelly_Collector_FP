def render_dashboard_legacy() -> str:
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>FiltrePlante - Monitoring Pompes</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
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

        .stats-card {
            background: linear-gradient(135deg, #2d8659 0%, #1e5d3f 100%);
            border-radius: 12px;
            padding: 25px 30px;
            margin-bottom: 1.5rem;
            color: white;
            box-shadow: 0 8px 25px rgba(45, 134, 89, 0.4);
        }

        .stats-card h3 {
            margin: 0 0 20px 0;
            font-size: 18px;
            font-weight: 600;
            opacity: 0.95;
            letter-spacing: 0.5px;
        }

        .stats-separator {
            border: 0;
            border-top: 1px solid rgba(255, 255, 255, 0.25);
            margin: 20px 0;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        .stat-box {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .stat-box-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            opacity: 0.9;
            margin-bottom: 10px;
        }

        .stat-box-line {
            font-size: 16px;
            line-height: 1.6;
        }

        .stat-value {
            font-weight: bold;
            font-size: 18px;
        }

        .stat-subtitle {
            font-size: 13px;
            opacity: 0.85;
        }

        .treatment-card {
            background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .treatment-card h3 {
            margin: 0 0 25px 0;
            font-size: 1.3rem;
            font-weight: 600;
        }

        .treatment-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }

        .treatment-box {
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }

        .treatment-box-label {
            color: rgba(255,255,255,0.9);
            font-size: 0.85rem;
            margin-bottom: 8px;
        }

        .treatment-box-value {
            color: white;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .treatment-box-unit {
            color: rgba(255,255,255,0.8);
            font-size: 0.85rem;
        }

        .treatment-info {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.2);
            color: rgba(255,255,255,0.85);
            font-size: 0.9rem;
        }

        .table-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }

        #table-wrapper {
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
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

        #chart-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .chart-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .chart-title {
            margin: 0;
            color: #2c3e50;
            font-size: 1rem;
        }

        .chart-date-range {
            color: #666;
            font-size: 0.85rem;
            font-weight: normal;
        }

        .controls-right {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }

        .date-picker-group {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .date-picker-group label {
            font-size: 0.85rem;
            color: #555;
            white-space: nowrap;
        }

        .chart-date-input {
            padding: 7px 10px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 0.85rem;
            background: #f8f9fa;
            color: #333;
            transition: border-color 0.3s;
        }

        .chart-date-input:focus {
            outline: none;
            border-color: #2d5a3d;
        }

        .btn-reset-date {
            padding: 6px 10px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            line-height: 1;
            transition: all 0.3s;
            color: #555;
        }

        .btn-reset-date:hover {
            background: #f0f0f0;
            border-color: #2d5a3d;
            color: #2d5a3d;
        }

        .period-selector {
            display: flex;
            gap: 8px;
        }

        .period-btn {
            padding: 7px 14px;
            border: 2px solid #2d5a3d;
            background: white;
            color: #2d5a3d;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
            font-size: 0.85rem;
        }

        .period-btn:hover {
            background: #f0f7f3;
        }

        .period-btn.active {
            background: #2d5a3d;
            color: white;
        }

        .btn-chart-export {
            padding: 7px 14px;
            background: #2d5a3d;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
            font-size: 0.85rem;
        }

        .btn-chart-export:hover {
            background: #234a30;
        }

        .chart-info-banner {
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
            color: #004085;
        }

        .chart-info-banner span {
            flex: 1;
        }

        .btn-try-30 {
            padding: 6px 12px;
            background: #2d5a3d;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            margin-left: 15px;
            white-space: nowrap;
        }

        .btn-try-30:hover {
            background: #234a30;
        }

        .chart-tabs {
            display: flex;
            gap: 0;
            margin-bottom: 0;
        }

        .chart-tab {
            padding: 10px 20px;
            border: 2px solid #2d5a3d;
            background: white;
            color: #2d5a3d;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.3s;
            flex: 1;
            text-align: center;
        }

        .chart-tab:first-child {
            border-radius: 8px 0 0 0;
            border-right: 1px solid #2d5a3d;
        }

        .chart-tab:last-child {
            border-radius: 0 8px 0 0;
            border-left: 1px solid #2d5a3d;
        }

        .chart-tab:hover:not(.active) {
            background: #f0f7f3;
        }

        .chart-tab.active {
            background: #2d5a3d;
            color: white;
        }

        .chart-container {
            position: relative;
            height: 400px;
            border: 2px solid #2d5a3d;
            border-top: none;
            border-radius: 0 0 8px 8px;
            padding: 15px;
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

            .stats-grid {
                gap: 15px;
            }

            .stat-value {
                font-size: 16px;
            }

            .treatment-box-value {
                font-size: 1.5rem;
            }

            .chart-controls {
                flex-direction: column;
                align-items: stretch;
            }

            .controls-right {
                flex-direction: column;
                align-items: stretch;
            }

            .date-picker-group {
                width: 100%;
            }

            .chart-date-input {
                flex: 1;
            }

            .period-selector {
                justify-content: center;
            }

            .chart-tab {
                padding: 8px 10px;
                font-size: 0.8rem;
            }
        }

        @media (max-width: 767px) {
            table {
                min-width: 900px;
            }

            #table-wrapper::before {
                content: '\\1F449 Faites defiler pour voir toutes les colonnes';
                display: block;
                text-align: center;
                font-size: 11px;
                color: #666;
                background: #f9f9f9;
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }

            .treatment-grid {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>🌱</span> FiltrePlante - Suivi des Stations</h1>
        <p>Analyse des cycles de pompage et impact environnemental | <a href="/admin" style="color:white;opacity:0.8;">Configuration</a></p>
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
                    <label for="start-date">Date d&#233;but</label>
                    <input type="date" id="start-date">
                </div>

                <div class="filter-group">
                    <label for="end-date">Date fin</label>
                    <input type="date" id="end-date">
                </div>
            </div>

            <div class="buttons">
                <button class="btn-primary" onclick="loadCycles()">Rafra&#238;chir</button>
                <button class="btn-secondary" onclick="exportCSV()">Exporter CSV</button>
            </div>
        </div>

        <div class="stats-card">
            <h3>SYNTH&#200;SE DES CYCLES</h3>

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-box-title">&#x1F4CA; CYCLES</div>
                    <div class="stat-box-line">
                        <span class="stat-value" id="stat-total">-</span> total
                    </div>
                    <div class="stat-box-line">
                        <span class="stat-value" id="stat-ongoing">-</span> en cours
                    </div>
                </div>

                <div class="stat-box">
                    <div class="stat-box-title">&#x23F1;&#xFE0F; DUR&#201;E MOYENNE</div>
                    <div class="stat-box-line">
                        <span class="stat-value" id="stat-avg-duration">-</span>
                    </div>
                    <div class="stat-subtitle">(par cycle)</div>
                </div>
            </div>

            <hr class="stats-separator">

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-box-title">&#x1F4AA; PUISSANCE (W)</div>
                    <div class="stat-box-line">
                        <span class="stat-value" id="stat-median-power">-</span> (m&#233;diane)
                    </div>
                    <div class="stat-box-line stat-subtitle">
                        Plage: <span id="stat-power-range">-</span>
                    </div>
                </div>

                <div class="stat-box">
                    <div class="stat-box-title">&#x1F4C8; INTENSIT&#201; (A)</div>
                    <div class="stat-box-line">
                        <span class="stat-value" id="stat-median-ampere">-</span> (m&#233;diane)
                    </div>
                    <div class="stat-box-line stat-subtitle">
                        Plage: <span id="stat-ampere-range">-</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="treatment-card">
            <h3>&#x1F4A7; TRAITEMENT &amp; IMPACT ENVIRONNEMENTAL</h3>
            <div class="treatment-grid">
                <div class="treatment-box">
                    <div class="treatment-box-label">&#x1F4CA; Eau us&#233;e trait&#233;e (p&#233;riode)</div>
                    <div class="treatment-box-value" id="treated-water-value">--</div>
                    <div class="treatment-box-unit">m&sup3;</div>
                </div>
                <div class="treatment-box">
                    <div class="treatment-box-label">&#x1F4C5; Traitement journalier</div>
                    <div class="treatment-box-value" id="treated-water-per-day">--</div>
                    <div class="treatment-box-unit">m&sup3;/jour</div>
                </div>
                <div class="treatment-box">
                    <div class="treatment-box-label">&#x1F331; CO&#x2082;e &#233;vit&#233; (p&#233;riode)</div>
                    <div class="treatment-box-value" id="co2e-avoided">--</div>
                    <div class="treatment-box-unit" id="co2e-unit">kg CO&sup2;e</div>
                </div>
                <div class="treatment-box">
                    <div class="treatment-box-label">&#x2705; R&#233;duction</div>
                    <div class="treatment-box-value" id="reduction-percent">--</div>
                    <div class="treatment-box-unit">%</div>
                </div>
            </div>
            <div class="treatment-info">
                &#x2139;&#xFE0F; R&#233;duction d'&#233;missions par rapport &#224; une fosse standard (PRG CH&#x2084; = 28, GIEC AR5)
            </div>
        </div>

        <div id="chart-section" style="display:none;">
            <div class="chart-controls">
                <div>
                    <h3 class="chart-title" id="chart-main-title">&#x1F4CA; Activit&#233; &#233;lectrique</h3>
                    <span id="chart-date-range" class="chart-date-range"></span>
                </div>
                <div class="controls-right">
                    <div class="date-picker-group">
                        <label>Jusqu'au :</label>
                        <input type="date" id="chart-end-date" class="chart-date-input" onchange="onChartDateChange()">
                        <button class="btn-reset-date" onclick="resetChartDate()" title="Revenir &#224; aujourd'hui">&#x21BB;</button>
                    </div>
                    <div class="period-selector">
                        <button class="period-btn active" data-period="24h" onclick="setChartPeriod('24h', this)">24h</button>
                        <button class="period-btn" data-period="7d" onclick="setChartPeriod('7d', this)">7 jours</button>
                        <button class="period-btn" data-period="30d" onclick="setChartPeriod('30d', this)">30 jours</button>
                    </div>
                    <button class="btn-chart-export" onclick="exportChartPNG()">&#128247; PNG</button>
                </div>
            </div>
            <div class="chart-tabs">
                <button class="chart-tab active" onclick="switchChartType('power', this)">&#x26A1; Consommation &#233;lectrique (W)</button>
                <button class="chart-tab" onclick="switchChartType('current', this)">&#x1F50C; Courant (A)</button>
            </div>
            <div class="chart-container">
                <canvas id="powerChart"></canvas>
            </div>
        </div>

        <div class="table-container">
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p>Chargement des donn&#233;es...</p>
            </div>

            <div id="table-wrapper" style="display: none;">
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortTable('device_id', 0)">Device <span class="sort-icon"></span></th>
                            <th onclick="sortTable('channel', 1)">Canal <span class="sort-icon"></span></th>
                            <th onclick="sortTable('start_time', 2)">Date <span class="sort-icon"></span></th>
                            <th onclick="sortTable('start_time', 3)">D&#233;marrage <span class="sort-icon"></span></th>
                            <th onclick="sortTable('end_time', 4)">Arr&#234;t <span class="sort-icon"></span></th>
                            <th onclick="sortTable('duration_minutes', 5)">Dur&#233;e <span class="sort-icon"></span></th>
                            <th onclick="sortTable('avg_power_w', 6)">Puissance moy. <span class="sort-icon"></span></th>
                            <th onclick="sortTable('avg_current_a', 7)">Courant moy. <span class="sort-icon"></span></th>
                            <th onclick="sortTable('avg_voltage_v', 8)">Voltage moy. <span class="sort-icon"></span></th>
                        </tr>
                    </thead>
                    <tbody id="cycles-tbody">
                    </tbody>
                </table>
            </div>

            <div id="empty" class="empty" style="display: none;">
                <p>Aucun cycle trouv&#233; pour cette p&#233;riode</p>
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
            startDate.setDate(today.getDate() - 30);

            function pad(n) { return n < 10 ? '0' + n : '' + n; }
            function toYMD(d) { return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
            document.getElementById('start-date').value = toYMD(startDate);
            document.getElementById('end-date').value = toYMD(today);

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
            if (cfg && cfg.channels && cfg.channels[channel]) {
                var chInfo = cfg.channels[channel];
                if (typeof chInfo === 'object' && chInfo.channel_name) return chInfo.channel_name;
                if (typeof chInfo === 'string') return chInfo;
            }
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
                loadChartData();
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
            syncChartDateWithMainFilter();
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
                loadChartData();

            } catch (error) {
                console.error('Erreur:', error);
                document.getElementById('loading').style.display = 'none';
                alert('Erreur lors du chargement des donn\u00e9es : ' + error.message);
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
                const powerStr = (cycle.avg_power_w != null ? parseFloat(cycle.avg_power_w).toFixed(1) : '-') + ' W';
                const currentStr = cycle.avg_current_a ? parseFloat(cycle.avg_current_a).toFixed(1) + ' A' : '-';
                const voltageStr = cycle.avg_voltage_v != null ? parseFloat(cycle.avg_voltage_v).toFixed(1) + ' V' : '-';

                row.innerHTML =
                    deviceCell +
                    channelCell +
                    '<td>' + dateStr + '</td>' +
                    '<td>' + startTimeStr + '</td>' +
                    '<td>' + endTimeStr + '</td>' +
                    '<td>' + durationStr + '</td>' +
                    '<td>' + powerStr + '</td>' +
                    '<td>' + currentStr + '</td>' +
                    '<td>' + voltageStr + '</td>';

                tbody.appendChild(row);
            });
        }

        function calculateMedian(values) {
            if (values.length === 0) return 0;
            var sorted = values.slice().sort(function(a, b) { return a - b; });
            var mid = Math.floor(sorted.length / 2);
            if (sorted.length % 2 === 0) {
                return (sorted[mid - 1] + sorted[mid]) / 2;
            } else {
                return sorted[mid];
            }
        }

        function updateStats(cycles) {
            var total = cycles.length;
            var ongoing = cycles.filter(function(c) { return c.is_ongoing; }).length;
            var completedCycles = cycles.filter(function(c) { return !c.is_ongoing; });

            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-ongoing').textContent = ongoing;

            var avgDuration = completedCycles.length > 0
                ? Math.round(completedCycles.reduce(function(sum, c) { return sum + c.duration_minutes; }, 0) / completedCycles.length)
                : 0;
            document.getElementById('stat-avg-duration').textContent = avgDuration + ' min';

            var allPowerValues = completedCycles
                .map(function(c) { return c.avg_power_w; })
                .filter(function(p) { return p != null && p > 0; });
            var medianPower = allPowerValues.length > 0 ? calculateMedian(allPowerValues).toFixed(1) : '0.0';
            document.getElementById('stat-median-power').textContent = medianPower + ' W';

            var allAmpereValues = completedCycles
                .map(function(c) { return c.avg_current_a; })
                .filter(function(a) { return a != null && a > 0; });
            var medianAmpere = allAmpereValues.length > 0 ? calculateMedian(allAmpereValues).toFixed(1) : '0.0';
            document.getElementById('stat-median-ampere').textContent = medianAmpere + ' A';

            if (currentData && currentData.stats) {
                var s = currentData.stats;
                document.getElementById('stat-power-range').textContent = parseFloat(s.min_power).toFixed(1) + ' - ' + parseFloat(s.max_power).toFixed(1) + ' W';
                document.getElementById('stat-ampere-range').textContent = parseFloat(s.min_current).toFixed(1) + ' - ' + parseFloat(s.max_current).toFixed(1) + ' A';
            } else {
                document.getElementById('stat-power-range').textContent = '-';
                document.getElementById('stat-ampere-range').textContent = '-';
            }

            if (currentData && currentData.treatment_stats) {
                document.getElementById('treated-water-value').textContent = currentData.treatment_stats.treated_water_m3;
                document.getElementById('treated-water-per-day').textContent = currentData.treatment_stats.treated_water_per_day;

                if (currentData.co2e_impact) {
                    var co2eKg = currentData.co2e_impact.co2e_avoided_kg;
                    if (co2eKg >= 1000) {
                        document.getElementById('co2e-avoided').textContent = (co2eKg / 1000).toFixed(2);
                        document.getElementById('co2e-unit').textContent = 't CO\\u2082e';
                    } else {
                        document.getElementById('co2e-avoided').textContent = co2eKg.toFixed(1);
                        document.getElementById('co2e-unit').textContent = 'kg CO\\u2082e';
                    }
                    document.getElementById('reduction-percent').textContent = currentData.co2e_impact.reduction_percent.toFixed(1);
                }
            } else {
                document.getElementById('treated-water-value').textContent = '-';
                document.getElementById('treated-water-per-day').textContent = '-';
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

        async function exportCSV() {
            if (!currentData || currentData.cycles.length === 0) {
                alert('Aucune donn\u00e9e \u00e0 exporter');
                return;
            }

            var pwd = prompt("Mot de passe requis pour l\\u0027export CSV :");
            if (!pwd) return;
            try {
                var res = await fetch('/api/verify-export-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password: pwd})
                });
                if (!res.ok) {
                    alert('Mot de passe incorrect');
                    return;
                }
            } catch(e) {
                alert('Erreur de v\u00e9rification');
                return;
            }

            let csv = 'Device;Canal;Date;Heure d\\u00E9marrage;Heure arr\\u00EAt;Dur\\u00E9e (min);Puissance moyenne (W);Courant moyen (A);Voltage moyen (V);Statut\\n';

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

                var powerW = cycle.avg_power_w != null ? parseFloat(cycle.avg_power_w).toFixed(1) : '';
                var currentA = cycle.avg_current_a ? parseFloat(cycle.avg_current_a).toFixed(1) : '';
                var voltageV = cycle.avg_voltage_v != null ? parseFloat(cycle.avg_voltage_v).toFixed(1) : '';
                csv += deviceName + ';' + channelName + ';' + dateStr + ';' + startTimeStr + ';' + endTimeStr + ';' + cycle.duration_minutes + ';' + powerW + ';' + currentA + ';' + voltageV + ';' + status + '\\n';
            });

            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'cycles_pompes_filtreplante_' + new Date().toISOString().split('T')[0] + '.csv';
            link.click();
        }
        let powerChart = null;
        let currentChartPeriod = '24h';
        let currentChartType = 'power';
        let lastChartData = null;
        let userPickedDate = false;
        let chartTimeBounds = null;
        const channelColors = [
            {bg: 'rgba(45, 134, 89, 0.3)', border: '#2d8659'},
            {bg: 'rgba(52, 152, 219, 0.3)', border: '#3498db'},
            {bg: 'rgba(243, 156, 18, 0.3)', border: '#f39c12'},
            {bg: 'rgba(231, 76, 60, 0.3)', border: '#e74c3c'}
        ];

        function syncChartDateWithMainFilter() {
            const mainEndDate = document.getElementById('end-date');
            const chartEndDate = document.getElementById('chart-end-date');
            const today = new Date().toISOString().split('T')[0];
            chartEndDate.max = today;
            if (mainEndDate && mainEndDate.value) {
                chartEndDate.value = mainEndDate.value;
                userPickedDate = (mainEndDate.value !== today);
            } else {
                chartEndDate.value = today;
                userPickedDate = false;
            }
        }
        syncChartDateWithMainFilter();

        function onChartDateChange() {
            const input = document.getElementById('chart-end-date');
            const today = new Date().toISOString().split('T')[0];
            if (input.value > today) {
                alert('La date ne peut pas \\u00eatre dans le futur.');
                input.value = today;
            }
            userPickedDate = true;
            loadChartData();
        }

        function resetChartDate() {
            const input = document.getElementById('chart-end-date');
            const today = new Date().toISOString().split('T')[0];
            input.value = today;
            input.max = today;
            userPickedDate = false;
            loadChartData();
        }

        function setChartPeriod(period, btn) {
            currentChartPeriod = period;
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            hideInfoMessage();
            loadChartData();
        }

        function switchChartType(type, btn) {
            currentChartType = type;
            document.querySelectorAll('.chart-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (lastChartData) {
                renderChart(lastChartData);
            } else {
                loadChartData();
            }
        }

        function updateChartTitle(startDate, endDate) {
            const el = document.getElementById('chart-date-range');
            if (!startDate || !endDate) { el.textContent = ''; return; }
            function fmtFr(dateStr) {
                const parts = dateStr.split('-');
                return parts[2] + '/' + parts[1] + '/' + parts[0];
            }
            el.textContent = fmtFr(startDate) + ' \\u2014 ' + fmtFr(endDate);
        }

        function showInfoMessage(message, showTry30Button) {
            let infoDiv = document.getElementById('chart-info-message');
            if (!infoDiv) {
                infoDiv = document.createElement('div');
                infoDiv.id = 'chart-info-message';
                infoDiv.className = 'chart-info-banner';
                const chartContainer = document.querySelector('.chart-container');
                chartContainer.parentElement.insertBefore(infoDiv, chartContainer);
            }
            infoDiv.innerHTML = '<span>' + message + '</span>' +
                (showTry30Button ? '<button onclick="tryPeriod30Days()" class="btn-try-30">Essayer 30 jours</button>' : '');
            infoDiv.style.display = 'flex';
        }

        function hideInfoMessage() {
            const infoDiv = document.getElementById('chart-info-message');
            if (infoDiv) infoDiv.style.display = 'none';
        }

        async function tryPeriod30Days() {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            const btn30 = document.querySelector('.period-btn[data-period="30d"]');
            if (btn30) btn30.classList.add('active');
            currentChartPeriod = '30d';
            await loadChartData();
        }

        async function loadChartData(periodOverride) {
            const deviceId = document.getElementById('device-filter').value;
            const section = document.getElementById('chart-section');

            if (!deviceId) {
                section.style.display = 'none';
                return;
            }
            section.style.display = 'block';

            const period = periodOverride || currentChartPeriod;
            const channel = document.getElementById('channel-filter').value;
            let url = '/api/power-chart-data?device_id=' + encodeURIComponent(deviceId) + '&period=' + period;
            if (channel) url += '&channel=' + encodeURIComponent(channel);
            if (userPickedDate) {
                const endDate = document.getElementById('chart-end-date').value;
                if (endDate) url += '&end_date=' + encodeURIComponent(endDate);
            }

            console.log('Chart request:', url, 'userPickedDate:', userPickedDate);

            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error('HTTP ' + response.status);
                const result = await response.json();

                const hasData = Object.values(result.data || {}).some(function(ch) {
                    return ch.timestamps && ch.timestamps.length > 1;
                });

                if (!hasData) {
                    if (!periodOverride && currentChartPeriod === '24h') {
                        console.log('Aucune donn\\u00e9e sur 24h, fallback vers 7 jours');
                        showInfoMessage('\\u2139\\uFE0F Aucune donn\\u00e9e sur les derni\\u00e8res 24h. Affichage \\u00e9tendu \\u00e0 7 jours.', false);
                        document.querySelectorAll('.period-btn').forEach(function(b) { b.classList.remove('active'); });
                        var btn7d = document.querySelector('.period-btn[data-period="7d"]');
                        if (btn7d) btn7d.classList.add('active');
                        currentChartPeriod = '7d';
                        return await loadChartData('7d');
                    }
                    if (period === '7d') {
                        console.log('Aucune donn\\u00e9e sur 7 jours');
                        showInfoMessage('\\u2139\\uFE0F Aucune donn\\u00e9e sur les 7 derniers jours.', true);
                    }
                } else {
                    hideInfoMessage();
                }

                updateChartTitle(result.start_date, result.end_date);
                chartTimeBounds = {
                    min: new Date(result.start_time_iso),
                    max: new Date(result.end_time_iso)
                };
                console.log('Chart bounds:', chartTimeBounds.min.toISOString(), '->', chartTimeBounds.max.toISOString());
                lastChartData = result.data;
                renderChart(result.data);
            } catch (e) {
                console.error('Chart error:', e);
                showInfoMessage('Erreur de chargement des donn\\u00e9es', false);
            }
        }

        function renderChart(data) {
            const canvas = document.getElementById('powerChart');
            if (powerChart) {
                powerChart.destroy();
                powerChart = null;
            }

            const datasets = [];
            let colorIdx = 0;
            const isPower = currentChartType === 'power';
            const dataKey = isPower ? 'power_w' : 'current_a';
            const unit = isPower ? 'W' : 'A';
            const labelSuffix = isPower ? 'Puissance' : 'Intensit\\u00e9';
            const yAxisTitle = isPower ? 'Puissance (W)' : 'Intensit\\u00e9 (A)';
            const yAxisColor = isPower ? '#2d8659' : '#3498db';

            Object.keys(data).sort().forEach(ch => {
                const chData = data[ch];
                const color = channelColors[colorIdx % channelColors.length];
                const chLabel = getChannelName(document.getElementById('device-filter').value, ch);

                datasets.push({
                    label: chLabel + ' (' + unit + ')',
                    data: chData.timestamps.map((t, i) => ({x: new Date(t), y: chData[dataKey][i]})),
                    borderColor: color.border,
                    backgroundColor: 'transparent',
                    fill: false,
                    stepped: true,
                    tension: 0,
                    pointRadius: 0,
                    borderWidth: 2.5,
                    spanGaps: false
                });

                colorIdx++;
            });

            if (datasets.length === 0) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '16px sans-serif';
                ctx.fillStyle = '#999';
                ctx.textAlign = 'center';
                ctx.fillText('Aucune donn\\u00e9e pour cette p\\u00e9riode', canvas.width / 2, canvas.height / 2);
                return;
            }

            let xTimeConfig = {};
            let xTicksConfig = {};

            if (currentChartPeriod === '24h') {
                xTimeConfig = {
                    unit: 'hour',
                    displayFormats: { hour: 'HH:mm' }
                };
                xTicksConfig = {
                    autoSkip: true,
                    maxTicksLimit: 12,
                    maxRotation: 0,
                    callback: function(value, index, ticks) {
                        const d = new Date(value);
                        const prevDate = index > 0 ? new Date(ticks[index - 1].value) : null;
                        const timePart = d.toLocaleTimeString('fr-FR', {timeZone:'UTC', hour:'2-digit', minute:'2-digit'});
                        if (index === 0 || (prevDate && d.getUTCDate() !== prevDate.getUTCDate())) {
                            const datePart = d.toLocaleDateString('fr-FR', {timeZone:'UTC', day:'2-digit', month:'2-digit'});
                            return datePart + ' ' + timePart;
                        }
                        return timePart;
                    }
                };
            } else if (currentChartPeriod === '7d') {
                xTimeConfig = {
                    unit: 'hour',
                    displayFormats: { hour: 'dd/MM HH:mm' }
                };
                xTicksConfig = {
                    autoSkip: true,
                    maxTicksLimit: 14,
                    maxRotation: 45
                };
            } else {
                xTimeConfig = {
                    unit: 'day',
                    displayFormats: { day: 'dd/MM' }
                };
                xTicksConfig = {
                    autoSkip: true,
                    maxTicksLimit: 15,
                    maxRotation: 0
                };
            }

            const xScaleConfig = {
                type: 'time',
                time: xTimeConfig,
                grid: { display: false },
                ticks: xTicksConfig
            };
            if (chartTimeBounds) {
                xScaleConfig.min = chartTimeBounds.min.getTime();
                xScaleConfig.max = chartTimeBounds.max.getTime();
            }

            powerChart = new Chart(canvas, {
                type: 'line',
                data: { datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { usePointStyle: true, padding: 20 }
                        },
                        tooltip: {
                            callbacks: {
                                title: function(items) {
                                    if (!items.length) return '';
                                    const d = new Date(items[0].parsed.x);
                                    return d.toLocaleString('fr-FR', {timeZone: 'UTC', day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'});
                                }
                            }
                        }
                    },
                    scales: {
                        x: xScaleConfig,
                        y: {
                            type: 'linear',
                            position: 'left',
                            title: { display: true, text: yAxisTitle, color: yAxisColor },
                            beginAtZero: true,
                            grace: '10%',
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        }
                    }
                }
            });
        }

        function exportChartPNG() {
            if (!powerChart) return;
            const link = document.createElement('a');
            const typeLabel = currentChartType === 'power' ? 'puissance' : 'courant';
            link.download = 'filtreplante_' + typeLabel + '_' + currentChartPeriod + '_' + new Date().toISOString().split('T')[0] + '.png';
            link.href = document.getElementById('powerChart').toDataURL('image/png');
            link.click();
        }

        document.getElementById('device-filter').addEventListener('change', function() {
            currentChartType = 'power';
            currentChartPeriod = '24h';
            document.querySelectorAll('.chart-tab').forEach(b => b.classList.remove('active'));
            document.querySelector('.chart-tab[onclick*="power"]').classList.add('active');
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            var btn24 = document.querySelector('.period-btn[data-period="24h"]');
            if (btn24) btn24.classList.add('active');
            hideInfoMessage();
            loadChartData();
        });
        document.getElementById('channel-filter').addEventListener('change', function() { loadChartData(); });
    </script>
</body>
</html>
    """
