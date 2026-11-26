// Initialize map
var map = L.map('map').setView([30.0444, 31.2357], 15);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
}).addTo(map);

// Add markers from DB
problems.forEach(function(p){
    var popupContent = "<b>Problem:</b> " + p.problem;
    if(p.image_path){
    let img_path = p.image_path.replace(/\\/g, "/"); // لو Windows
    popupContent += "<br><img src='/static/uploads/" + img_path + "' width='100'>";
}

    var marker = L.marker([p.lat, p.lon]).addTo(map);
    marker.bindPopup(popupContent);
});
