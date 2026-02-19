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
        const response = await fetch('/api/devices');
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
        alert('Erreur lors du chargement des données : ' + error.message);
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
                document.getElementById('co2e-unit').textContent = 't CO₂e';
            } else {
                document.getElementById('co2e-avoided').textContent = co2eKg.toFixed(1);
                document.getElementById('co2e-unit').textContent = 'kg CO₂e';
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
        alert('Aucune donnée à exporter');
        return;
    }

    var pwd = prompt("Mot de passe requis pour l'export CSV :");
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
        alert('Erreur de vérification');
        return;
    }

    let csv = 'Device;Canal;Date;Heure démarrage;Heure arrêt;Durée (min);Puissance moyenne (W);Courant moyen (A);Voltage moyen (V);Statut\n';

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
        csv += deviceName + ';' + channelName + ';' + dateStr + ';' + startTimeStr + ';' + endTimeStr + ';' + cycle.duration_minutes + ';' + powerW + ';' + currentA + ';' + voltageV + ';' + status + '\n';
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
        alert('La date ne peut pas être dans le futur.');
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
    el.textContent = fmtFr(startDate) + ' — ' + fmtFr(endDate);
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
                console.log('Aucune donnée sur 24h, fallback vers 7 jours');
                showInfoMessage('ℹ️ Aucune donnée sur les dernières 24h. Affichage étendu à 7 jours.', false);
                document.querySelectorAll('.period-btn').forEach(function(b) { b.classList.remove('active'); });
                var btn7d = document.querySelector('.period-btn[data-period="7d"]');
                if (btn7d) btn7d.classList.add('active');
                currentChartPeriod = '7d';
                return await loadChartData('7d');
            }
            if (period === '7d') {
                console.log('Aucune donnée sur 7 jours');
                showInfoMessage('ℹ️ Aucune donnée sur les 7 derniers jours.', true);
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
        showInfoMessage('Erreur de chargement des données', false);
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
    const labelSuffix = isPower ? 'Puissance' : 'Intensité';
    const yAxisTitle = isPower ? 'Puissance (W)' : 'Intensité (A)';
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
        ctx.fillText('Aucune donnée pour cette période', canvas.width / 2, canvas.height / 2);
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
