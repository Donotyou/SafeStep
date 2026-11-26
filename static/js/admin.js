// Admin dashboard JS: fetch problems, render table and map, handle resolve
var adminMap = L.map('admin-map').setView([30.0444, 31.2357], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(adminMap);

var adminMarkers = {}; // id -> marker

function fetchProblems(region){
    var url = window.ADMIN_PROBLEMS_API;
    if(region && region !== 'all') url += '?region=' + encodeURIComponent(region);
    return fetch(url).then(r=>r.json()).then(function(data){ return data.problems || []; });
}

function renderTable(problems){
    var tbody = document.querySelector('#problems-table tbody');
    tbody.innerHTML = '';
    problems.forEach(function(p){
        var tr = document.createElement('tr');
        tr.dataset.id = p.id;
        var statusBadge = (p.status && p.status === 'resolved') ? '<span class="badge bg-secondary">Resolved</span>' : '<span class="badge bg-danger">Active</span>';
        var imgHtml = p.image_path ? ('<img src="/static/uploads/' + encodeURIComponent(p.image_path) + '" style="width:48px;height:36px;object-fit:cover;border-radius:4px;margin-right:6px;"/>') : '';
        tr.innerHTML = '<td>' + imgHtml + (p.problem || '') + '</td>' +
                       '<td>' + (p.lat.toFixed(5) + ',' + p.lon.toFixed(5)) + '</td>' +
                       '<td>' + statusBadge + '</td>' +
                       '<td>' + (p.created_at || '') + '</td>' +
                       '<td><button class="btn btn-sm btn-outline-success resolve-btn">Mark Resolved</button></td>';
        tbody.appendChild(tr);

        // hover row -> highlight marker
        tr.addEventListener('mouseover', function(){
            var m = adminMarkers[p.id]; if(m) m.setStyle({radius:10, color:'#333'});
        });
        tr.addEventListener('mouseout', function(){
            var m = adminMarkers[p.id]; if(m) m.setStyle({radius:7, color: markerColorFor(p)});
        });
        tr.addEventListener('click', function(){
            var m = adminMarkers[p.id]; if(m) { m.openPopup(); adminMap.panTo([p.lat, p.lon]); }
        });
    });
}

function markerColorFor(p){
    return (p.status && p.status === 'resolved') ? 'gray' : ( (p.problem||'').toLowerCase().includes('stair') ? 'red' : 'orange');
}

function plotProblems(problems){
    // clear existing
    Object.values(adminMarkers).forEach(function(m){ adminMap.removeLayer(m); });
    adminMarkers = {};
    problems.forEach(function(p){
        var color = markerColorFor(p);
        var marker = L.circleMarker([p.lat, p.lon], {radius:7, color:color, fill:true, fillOpacity:0.95}).addTo(adminMap);
        var popup = '<b>' + (p.problem||'') + '</b><br/>' + (p.description || '');
        if(p.image_path){ popup += '<br><img src="/static/uploads/' + encodeURIComponent(p.image_path) + '" style="max-width:200px;max-height:120px;display:block;margin-top:6px;"/>' }
        if(p.created_at) popup += '<div class="small text-muted">' + p.created_at + '</div>';
        marker.bindPopup(popup);
        marker.on('click', function(){
            // highlight corresponding row
            var row = document.querySelector('#problems-table tbody tr[data-id="' + p.id + '"]');
            if(row) row.scrollIntoView({behavior:'smooth', block:'center'});
        });
        adminMarkers[p.id] = marker;
    });
}

// initial load
function loadForRegion(region){
    fetchProblems(region).then(function(problems){
        renderTable(problems);
        plotProblems(problems);
    });
}

document.getElementById('region-select').addEventListener('change', function(e){
    loadForRegion(e.target.value);
});

// handle resolve button via event delegation
document.querySelector('#problems-table tbody').addEventListener('click', function(e){
    if(e.target.classList.contains('resolve-btn')){
        var tr = e.target.closest('tr');
        var id = tr.dataset.id;
        if(!confirm('Mark problem #' + id + ' as resolved?')) return;
        fetch(window.ADMIN_RESOLVE_API, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id: parseInt(id)}) })
            .then(r=>r.json()).then(function(resp){
                if(resp && resp.ok){
                    // update UI row and marker
                    tr.querySelector('td:nth-child(3)').innerHTML = '<span class="badge bg-secondary">Resolved</span>';
                    var marker = adminMarkers[id]; if(marker) marker.setStyle({color:'gray', fillOpacity:0.6});
                } else {
                    alert('Failed: ' + (resp.error||'unknown'));
                }
            }).catch(function(err){ console.error(err); alert('Request failed'); });
    }
});

// load all initially
loadForRegion('all');

// expose a refresh function
window.adminRefresh = function(){ loadForRegion(document.getElementById('region-select').value); };
