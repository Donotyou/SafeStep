// Simple route planner UI using Leaflet
var map = L.map('routes-map').setView([30.0444, 31.2357], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);

var startMarker = null, destMarker = null, routeLayers = [];
var problemMarkers = [];
var reportMode = false;

function setMarker(markerVarName, lat, lon){
    if(markerVarName === 'start'){
        if(startMarker){ startMarker.setLatLng([lat,lon]); }
        else { startMarker = L.marker([lat,lon], {draggable:true}).addTo(map); startMarker.on('dragend', onDragEnd); }
    } else {
        if(destMarker){ destMarker.setLatLng([lat,lon]); }
        else { destMarker = L.marker([lat,lon], {draggable:true}).addTo(map); destMarker.on('dragend', onDragEnd); }
    }
}

function onDragEnd(){
    // nothing immediate; user can press Plan Routes
}

map.on('click', function(e){
    if(reportMode){
        // capture coords for report, open modal
        var lat = e.latlng.lat, lon = e.latlng.lng;
        document.getElementById('modal-lat').value = lat;
        document.getElementById('modal-lon').value = lon;
        // show modal programmatically
        var modalEl = document.getElementById('reportModal');
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
        // exit report mode
        reportMode = false;
        document.getElementById('report-btn').classList.remove('btn-warning');
        map.getContainer().style.cursor = '';
        return;
    }

    // if not reportMode: existing behavior to set start/dest markers
    if(!startMarker){ setMarker('start', e.latlng.lat, e.latlng.lng); document.getElementById('search-start').value = '';} 
    else if(!destMarker){ setMarker('dest', e.latlng.lat, e.latlng.lng); document.getElementById('search-dest').value = '';} 
    else {
        // replace dest
        setMarker('dest', e.latlng.lat, e.latlng.lng);
    }
});

document.getElementById('clear-btn').addEventListener('click', function(){
    if(startMarker){ map.removeLayer(startMarker); startMarker=null; }
    if(destMarker){ map.removeLayer(destMarker); destMarker=null; }
    routeLayers.forEach(function(l){ map.removeLayer(l); }); routeLayers = [];
    problemMarkers.forEach(function(m){ map.removeLayer(m); }); problemMarkers = [];
    document.getElementById('routes-list').innerHTML = '';
    document.getElementById('search-start').value = '';
    document.getElementById('search-dest').value = '';
});

function clearProblemMarkers(){
    problemMarkers.forEach(function(m){ map.removeLayer(m); });
    problemMarkers = [];
}

function fetchAndShowProblems(south, north, west, east){
    var url = '/api/problems';
    if(arguments.length === 4){
        url += '?south=' + south + '&north=' + north + '&west=' + west + '&east=' + east;
    }
    return fetch(url).then(function(r){ return r.json(); }).then(function(data){
        clearProblemMarkers();
        if(!data || !data.problems) return;
        data.problems.forEach(function(p){
            var lat = p.lat; var lon = p.lon;
            var color = 'blue';
            var t = (p.problem || '').toLowerCase();
            if(t.includes('stair')) color = 'red';
            else if(t.includes('broken') || t.includes('pothole') || t.includes('sidewalk')) color = 'orange';

            var circle = L.circleMarker([lat, lon], {radius:6, color:color, fill:true, fillOpacity:0.9}).addTo(map);
            var popupHtml = '<b>' + (p.problem || 'problem') + '</b><br/>' + (p.description || '');
            if(p.image_path){
                // take only the filename portion in case the DB contains a path
                var img = p.image_path.replace(/\\/g, '/').split('/').pop();
                popupHtml += '<br><img src="/static/uploads/' + encodeURIComponent(img) + '" style="max-width:160px; max-height:120px; display:block; margin-top:6px;"/>';
            }
            circle.bindPopup(popupHtml);
            problemMarkers.push(circle);
        });
    }).catch(function(err){ console.error('fetch problems failed', err); });
}

// load problems for initial view
var b = map.getBounds();
fetchAndShowProblems(b.getSouth(), b.getNorth(), b.getWest(), b.getEast());

// refresh problems on map move end (debounced simple)
var moveTimeout = null;
map.on('moveend', function(){
    if(moveTimeout) clearTimeout(moveTimeout);
    moveTimeout = setTimeout(function(){
        var bb = map.getBounds();
        fetchAndShowProblems(bb.getSouth(), bb.getNorth(), bb.getWest(), bb.getEast());
    }, 500);
});

// simple nominatim lookup
function geocode(q){
    if(!q) return Promise.reject('empty');
    var url = 'https://nominatim.openstreetmap.org/search?format=json&q=' + encodeURIComponent(q);
    return fetch(url).then(r=>r.json()).then(js=>js);
}

document.getElementById('search-start').addEventListener('change', function(e){
    var q = e.target.value.trim(); if(!q) return;
    geocode(q).then(function(res){ if(res && res[0]){ var r=res[0]; setMarker('start', parseFloat(r.lat), parseFloat(r.lon)); map.setView([r.lat, r.lon], 14); } });
});

document.getElementById('search-dest').addEventListener('change', function(e){
    var q = e.target.value.trim(); if(!q) return;
    geocode(q).then(function(res){ if(res && res[0]){ var r=res[0]; setMarker('dest', parseFloat(r.lat), parseFloat(r.lon)); map.setView([r.lat, r.lon], 14); } });
});

document.getElementById('plan-btn').addEventListener('click', function(){
    if(!startMarker || !destMarker){ alert('Please select both start and destination (click map or search).'); return; }
    var s = startMarker.getLatLng(); var d = destMarker.getLatLng();
    var payload = { start: [s.lat, s.lng], dest: [d.lat, d.lng] };
    fetch(window.ROUTES_API, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) })
        .then(r=>r.json())
        .then(renderRoutes)
        .catch(e=>{ console.error(e); alert('Route planning failed'); });
});

// Report mode: click Report button then click the map to choose location
document.getElementById('report-btn').addEventListener('click', function(){
    reportMode = true;
    // give visual hint
    this.classList.add('btn-warning');
    map.getContainer().style.cursor = 'crosshair';
});

// Handle modal form submission via AJAX to /api/report
var reportForm = document.getElementById('report-form');
if(reportForm){
    reportForm.addEventListener('submit', function(ev){
        ev.preventDefault();
        var formData = new FormData(reportForm);
        fetch(window.REPORT_API, { method: 'POST', body: formData })
            .then(function(r){ return r.json(); })
            .then(function(resp){
                if(resp && resp.problem){
                    // add marker immediately
                    var p = resp.problem;
                    var lat = p.lat, lon = p.lon;
                    var color = 'blue';
                    var t = (p.problem || '').toLowerCase();
                    if(t.includes('stair')) color = 'red';
                    else if(t.includes('broken') || t.includes('pothole') || t.includes('sidewalk')) color = 'orange';
                    var circle = L.circleMarker([lat, lon], {radius:7, color:color, fill:true, fillOpacity:0.95}).addTo(map);
                    var popupHtml = '<b>' + (p.problem || 'problem') + '</b><br/>' + (p.description || '');
                    if(p.image_path){
                        var img = (p.image_path || '').replace(/\\/g, '/').split('/').pop();
                        popupHtml += '<br><img src="/static/uploads/' + encodeURIComponent(img) + '" style="max-width:160px; max-height:120px; display:block; margin-top:6px;"/>';
                    }
                    if(p.created_at) popupHtml += '<div class="small text-muted">' + p.created_at + '</div>';
                    circle.bindPopup(popupHtml);
                    problemMarkers.push(circle);

                    // close modal
                    var modalEl = document.getElementById('reportModal');
                    var modalInst = bootstrap.Modal.getInstance(modalEl);
                    if(modalInst) modalInst.hide();
                    // reset form
                    reportForm.reset();
                } else {
                    alert('Report failed');
                }
            })
            .catch(function(err){ console.error('report failed', err); alert('Report failed'); });
    });
}

function renderRoutes(data){
    // clear previous
    routeLayers.forEach(function(l){ map.removeLayer(l); }); routeLayers = [];
    var list = document.getElementById('routes-list'); list.innerHTML = '';
    if(!data.routes) return;
    data.routes.forEach(function(rt, idx){
        var coords = rt.coords.map(function(p){ return [p[0], p[1]]; });
        // color by score
        var score = rt.score;
        var color = score >= 70 ? 'green' : (score >= 40 ? 'gold' : 'red');
        var poly = L.polyline(coords, {color: color, weight:6, opacity:0.85}).addTo(map);
        poly.bindTooltip('Score: ' + score + '%\nProblems: ' + (rt.problems_count||0), {sticky:true});
        // hover highlight
        poly.on('mouseover', function(){ this.setStyle({weight:10}); });
        poly.on('mouseout', function(){ this.setStyle({weight:6}); });
        routeLayers.push(poly);
        var problems = rt.problems_count || 0;
        var status = score >= 70 ? 'Safe' : (score >=40 ? 'Moderate' : 'Unsafe');
        var item = document.createElement('div');
        item.className = 'route-item';
        item.innerHTML = '<div class="d-flex justify-content-between align-items-center"><div><b>Route '+(idx+1)+'</b><div class="small text-muted">Problems: '+problems+'</div></div><div><span class="badge" style="background:'+color+'; color:#fff;">'+score+'%</span></div></div>';
        item.addEventListener('click', function(){
            // zoom to route and highlight
            map.fitBounds(poly.getBounds(), {padding:[40,40]});
            routeLayers.forEach(r=>r.setStyle({opacity:0.3}));
            poly.setStyle({opacity:1, weight:10});
        });
        list.appendChild(item);
    });

    // after rendering routes, fetch problems within the routes bbox for clearer context
    try{
        var allCoords = [].concat.apply([], data.routes.map(function(r){ return r.coords; }));
        var lats = allCoords.map(function(c){ return c[0]; });
        var lons = allCoords.map(function(c){ return c[1]; });
        var south = Math.min.apply(null, lats);
        var north = Math.max.apply(null, lats);
        var west = Math.min.apply(null, lons);
        var east = Math.max.apply(null, lons);
        // pad a little
        var pad = 0.002;
        fetchAndShowProblems(south - pad, north + pad, west - pad, east + pad);
    }catch(e){/* ignore */}
}
