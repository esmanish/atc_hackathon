// map.js - Enhanced aircraft visualization for Air Traffic Command Center

// Define aircraft icons based on altitude ranges
const aircraftIcons = {
    createIcon: function(altitude, heading, category) {
        // Determine color based on altitude
        let color = '#3388ff'; // Default blue
        
        if (altitude < 10000) {
            color = '#ff4444'; // Red for low altitude
        } else if (altitude < 20000) {
            color = '#ff8800'; // Orange for medium-low altitude
        } else if (altitude < 30000) {
            color = '#ffcc00'; // Yellow for medium-high altitude
        } else {
            color = '#44ff44'; // Green for high altitude
        }
        
        // Create SVG for aircraft icon with rotation
        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" style="transform: rotate(${heading}deg);">
                <path d="M12,2L4.5,20.29L5.21,21L12,18L18.79,21L19.5,20.29L12,2Z" fill="${color}"/>
            </svg>
        `;
        
        // Convert SVG to data URL
        const svgBase64 = btoa(svg);
        const dataUrl = 'data:image/svg+xml;base64,' + svgBase64;
        
        // Create the icon
        return L.icon({
            iconUrl: dataUrl,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            popupAnchor: [0, -12]
        });
    }
};

class AircraftMap {
    constructor(mapElementId, config = {}) {
        this.mapElementId = mapElementId;
        this.config = Object.assign({
            center: [14.5, 74.0],
            zoom: 7,
            maxZoom: 12,
            minZoom: 5,
            updateInterval: 5 // seconds
        }, config);
        
        this.aircraftMarkers = {};
        this.aircraftData = {};
        this.flightPaths = {};
        this.filters = {
            minAltitude: 0,
            maxAltitude: 50000,
            showPaths: false
        };
        
        this.heatmapLayer = null;
        this.heatmapData = [];
        
        this.init();
    }
    
    init() {
        // Initialize the Leaflet map
        this.map = L.map(this.mapElementId).setView(this.config.center, this.config.zoom);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: this.config.maxZoom,
            minZoom: this.config.minZoom
        }).addTo(this.map);
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize the heatmap
        this.initHeatmap();
    }
    
    initHeatmap() {
        // Only initialize if the heatmap plugin is available
        if (typeof L.heatLayer !== 'undefined') {
            this.heatmapLayer = L.heatLayer([], {
                radius: 25,
                blur: 15,
                maxZoom: 10,
                max: 1.0,
                gradient: {
                    0.4: 'blue',
                    0.6: 'cyan',
                    0.8: 'lime',
                    0.9: 'yellow',
                    1.0: 'red'
                }
            }).addTo(this.map);
        }
    }
    
    setupEventListeners() {
        // Add map zoom end event to scale aircraft icons
        this.map.on('zoomend', () => {
            this.updateIconSize();
        });
    }
    
    updateIconSize() {
        // Scale aircraft icons based on zoom level
        const zoomLevel = this.map.getZoom();
        const baseSize = 24;
        const scale = 1 + (zoomLevel - this.config.minZoom) * 0.1;
        const newSize = Math.max(baseSize * scale, baseSize);
        
        Object.values(this.aircraftMarkers).forEach(marker => {
            const icon = marker.getIcon();
            icon.options.iconSize = [newSize, newSize];
            icon.options.iconAnchor = [newSize / 2, newSize / 2];
            marker.setIcon(icon);
        });
    }
    
    updateAircraftData(data) {
        // Store previous positions for flight path
        const previousPositions = {};
        Object.keys(this.aircraftData).forEach(hex => {
            if (this.aircraftData[hex] && this.aircraftData[hex].lat && this.aircraftData[hex].lon) {
                previousPositions[hex] = {
                    lat: this.aircraftData[hex].lat,
                    lon: this.aircraftData[hex].lon
                };
            }
        });
        
        // Update aircraft data
        this.aircraftData = {};
        if (data && data.aircraft) {
            data.aircraft.forEach(aircraft => {
                this.aircraftData[aircraft.hex] = aircraft;
                
                // Add to heatmap data
                if (aircraft.lat && aircraft.lon) {
                    this.heatmapData.push([aircraft.lat, aircraft.lon, 0.5]);
                    
                    // Limit heatmap data to prevent performance issues
                    if (this.heatmapData.length > 1000) {
                        this.heatmapData.shift();
                    }
                }
                
                // Update flight paths if necessary
                if (this.filters.showPaths && previousPositions[aircraft.hex] && 
                    aircraft.lat && aircraft.lon) {
                    this.updateFlightPath(aircraft.hex, previousPositions[aircraft.hex], {
                        lat: aircraft.lat,
                        lon: aircraft.lon
                    });
                }
            });
        }
        
        // Update the map visuals
        this.updateMap();
        
        // Update heatmap
        this.updateHeatmap();
    }
    
    updateMap() {
        // Apply filters
        const filteredAircraft = Object.values(this.aircraftData).filter(aircraft => {
            return aircraft.altitude >= this.filters.minAltitude && 
                   aircraft.altitude <= this.filters.maxAltitude;
        });
        
        // Add/update markers for each aircraft
        filteredAircraft.forEach(aircraft => {
            if (!aircraft.lat || !aircraft.lon) return;
            
            const position = [aircraft.lat, aircraft.lon];
            const rotationAngle = aircraft.track || aircraft.heading || 0;
            
            if (this.aircraftMarkers[aircraft.hex]) {
                // Update existing marker with animation
                this.aircraftMarkers[aircraft.hex].setLatLng(position);
                
                // Update icon based on current data
                const newIcon = aircraftIcons.createIcon(
                    aircraft.altitude,
                    rotationAngle,
                    aircraft.category
                );
                this.aircraftMarkers[aircraft.hex].setIcon(newIcon);
            } else {
                // Create new marker
                const icon = aircraftIcons.createIcon(
                    aircraft.altitude,
                    rotationAngle,
                    aircraft.category
                );
                
                const marker = L.marker(position, { 
                    icon: icon,
                    rotationAngle: rotationAngle,
                    rotationOrigin: 'center center'
                }).addTo(this.map);
                
                // Add popup with basic info
                const callsign = aircraft.flight ? aircraft.flight.trim() : 'N/A';
                marker.bindPopup(`
                    <strong>Flight:</strong> ${callsign}<br>
                    <strong>Hex:</strong> ${aircraft.hex}<br>
                    <strong>Altitude:</strong> ${aircraft.altitude} ft<br>
                    <strong>Speed:</strong> ${aircraft.speed} knots<br>
                    <strong>Heading:</strong> ${rotationAngle}°
                `);
                
                // Add click event
                marker.on('click', () => {
                    this.onAircraftClick(aircraft.hex);
                });
                
                this.aircraftMarkers[aircraft.hex] = marker;
            }
        });
        
        // Remove markers for aircraft that are no longer visible
        Object.keys(this.aircraftMarkers).forEach(hex => {
            if (!filteredAircraft.some(a => a.hex === hex)) {
                this.map.removeLayer(this.aircraftMarkers[hex]);
                delete this.aircraftMarkers[hex];
                
                // Remove flight path if it exists
                if (this.flightPaths[hex]) {
                    this.map.removeLayer(this.flightPaths[hex]);
                    delete this.flightPaths[hex];
                }
            }
        });
    }
    
    updateFlightPath(hex, prevPos, newPos) {
        if (!this.flightPaths[hex]) {
            // Create new path
            this.flightPaths[hex] = L.polyline([[prevPos.lat, prevPos.lon]], {
                color: this.getAltitudeColor(this.aircraftData[hex].altitude),
                weight: 2,
                opacity: 0.6,
                smoothFactor: 1
            }).addTo(this.map);
        }
        
        // Add point to existing path
        const currentPath = this.flightPaths[hex].getLatLngs();
        currentPath.push([newPos.lat, newPos.lon]);
        
        // Limit path length to prevent performance issues
        if (currentPath.length > 100) {
            currentPath.shift();
        }
        
        this.flightPaths[hex].setLatLngs(currentPath);
    }
    
    updateHeatmap() {
        if (this.heatmapLayer && this.heatmapData.length > 0) {
            this.heatmapLayer.setLatLngs(this.heatmapData);
        }
    }
    
    getAltitudeColor(altitude) {
        if (altitude < 10000) {
            return '#ff4444'; // Red
        } else if (altitude < 20000) {
            return '#ff8800'; // Orange
        } else if (altitude < 30000) {
            return '#ffcc00'; // Yellow
        } else {
            return '#44ff44'; // Green
        }
    }
    
    setFilters(filters) {
        this.filters = {...this.filters, ...filters};
        
        // Update flight paths visibility
        if (this.filters.showPaths) {
            Object.keys(this.flightPaths).forEach(hex => {
                if (!this.map.hasLayer(this.flightPaths[hex])) {
                    this.map.addLayer(this.flightPaths[hex]);
                }
            });
        } else {
            Object.keys(this.flightPaths).forEach(hex => {
                if (this.map.hasLayer(this.flightPaths[hex])) {
                    this.map.removeLayer(this.flightPaths[hex]);
                }
            });
        }
        
        this.updateMap();
    }
    
    // Callback for when an aircraft is clicked
    onAircraftClick(hex) {
        // Default implementation - override this in the application
        console.log(`Aircraft clicked: ${hex}`);
    }
    
    zoomToAircraft(hex) {
        const aircraft = this.aircraftData[hex];
        if (aircraft && aircraft.lat && aircraft.lon) {
            this.map.setView([aircraft.lat, aircraft.lon], this.config.zoom + 2, {
                animate: true,
                duration: 1 // 1 second animation
            });
            
            if (this.aircraftMarkers[hex]) {
                this.aircraftMarkers[hex].openPopup();
            }
        }
    }
    
    zoomToAllAircraft() {
        // Create bounds that include all visible aircraft
        const positions = Object.values(this.aircraftData)
            .filter(a => a.lat && a.lon)
            .map(a => [a.lat, a.lon]);
        
        if (positions.length > 0) {
            const bounds = L.latLngBounds(positions);
            this.map.fitBounds(bounds, {
                padding: [50, 50],
                animate: true,
                duration: 1
            });
        }
    }
    
    toggleHeatmap(show) {
        if (!this.heatmapLayer) return;
        
        if (show && !this.map.hasLayer(this.heatmapLayer)) {
            this.map.addLayer(this.heatmapLayer);
        } else if (!show && this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
        }
    }
}

// Export the AircraftMap class
window.AircraftMap = AircraftMap;