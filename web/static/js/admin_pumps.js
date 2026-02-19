async function adminLogout() {
    try { await fetch('/api/admin/logout', { method: 'POST' }); } catch(e) {}
    window.location.href = '/dashboard';
}

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
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Aucun modèle de pompe</td></tr>';
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
            showMsg('success', pumpId ? 'Modèle modifié !' : 'Modèle créé !');
            resetForm();
            loadPumps();
        } else {
            showMsg('error', data.error || 'Erreur');
        }
    } catch(e) {
        showMsg('error', 'Erreur réseau');
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
    if (!confirm('Supprimer ce modèle ?')) return;
    try {
        var res = await fetch('/api/config/pump-model/' + id, { method: 'DELETE' });
        var data = await res.json();
        if (res.ok && data.success) {
            showMsg('success', 'Modèle supprimé !');
            loadPumps();
        } else {
            showMsg('error', data.detail || data.error || 'Erreur');
        }
    } catch(e) {
        showMsg('error', 'Erreur réseau');
    }
}

function resetForm() {
    document.getElementById('pump-id').value = '';
    document.getElementById('pump-name').value = '';
    document.getElementById('pump-power').value = '';
    document.getElementById('pump-current').value = '';
    document.getElementById('pump-flow').value = '';
    document.getElementById('form-title').textContent = 'Ajouter un nouveau modèle';
}

function showMsg(type, text) {
    var el = document.getElementById('msg');
    el.className = 'msg ' + type;
    el.textContent = text;
    el.style.display = 'block';
    setTimeout(function() { el.style.display = 'none'; }, 3000);
}
