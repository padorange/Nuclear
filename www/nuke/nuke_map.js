/*
	nuke.js
	-----------
	use Openlayers to display nuclear power plant on a OpenStreetMap map
	the data are stored in an mySQL database
		
	OpenStreetMap : <http://openstreetmap.org/>
	OpenLayers : <http://openlayers.org/>
*/

// URL (PHP script) called to retrieve data (from MySQL)
var request_url="http://www.leretourdelautruche.com/map/nuke/nuke_request.php";

// complex map object
var map;
 
// Start position for the map (get from URL params)
// or start zooming on France
var theArgs = getArgs();
var lat = theArgs.lat ? theArgs.lat : 46.88;
var lon = theArgs.lon ? theArgs.lon : 2.76;
var zoom = theArgs.zoom ? theArgs.zoom : 6;

var rayonNuke = 100000; // radius around nuke (kilometers)
var heat; // the heat map layer
var previousZoomLevel; // previous zoom

var nuke_markers;
var my_markers = new Array();

function getArgs() {
	var args = new Object();
	var query = location.search.substring(1);  // Get query string.
	var pairs = query.split("&");              // Break at ampersand. //+pjl

	for(var i = 0; i < pairs.length; i++) {
		var pos = pairs[i].indexOf('=');       // Look for "name=value".
		if (pos == -1) continue;               // If not found, skip.
		var argname = pairs[i].substring(0,pos);  // Extract the name.
		var value = pairs[i].substring(pos+1); // Extract the value.
		args[argname] = unescape(value);          // Store as a property.
	}
	return args;                               // Return the object.
}

// build a request to get raw data from the SQL database (through a PHP script)
function getNukeHeatMap() {

	  zoom=map.getZoom();
	  if (zoom != previousZoomLevel) {
	  	if ((zoom<4) || (zoom>9))
	  	{
			heat.defaultRadius = 0;
			heat.setVisibility(false);
	  	}
	  	else
	  	{
			heat.setVisibility(true);
			heat.defaultRadius = 5*rayonNuke / (3*map.getResolution());
			//console.log("\tres :"+map.getResolution());
			//console.log("heat radius : "+heat.defaultRadius);
		}
		previousZoomLevel = zoom;
	  }
	  bbox=map.getExtent().transform(map.projection, map.displayProjection);
	  bbox.top=bbox.top-rayonNuke;
	  bbox.left=bbox.left-rayonNuke;
	  bbox.bottom=bbox.bottom+rayonNuke;
	  bbox.right=bbox.right+rayonNuke;
	  type="power";
	  OpenLayers.Request.GET({ 
		  			params: {"t" : bbox.top, "l":bbox.left, "b":bbox.bottom, "r":bbox.right, "z":zoom, "tt":type},
		  			url: request_url,
		  			success : parseNukeResponse
		   });
  }

// parse the return raw data (text layer format) to build the sources list for the heat map
function parseNukeResponse(response) {
	  format = new OpenLayers.Format.Text();
	  nukes = format.read(response.responseText);
	  
	  //console.log("response:"+nukes.length);
	  //console.log(nukes);
	  heat.points=[];
	  for (var i = 0; i < nukes.length; i++) {
			pt=new OpenLayers.LonLat(nukes[i].geometry.x, nukes[i].geometry.y).transform(map.displayProjection,  map.projection);
			heat.addSource(new Heatmap.Source(pt));
	  }

	  heat.redraw();
}

function set_cookie(c_key, c_val) {
      var c = c_key + '=' + c_val;

      // cookie expires in 1 month
      var dt = new Date();
      dt.setTime(dt.getTime() + (30 * 24 * 60 * 60 * 1000));
      c = c + '; expires=' + dt.toGMTString();
      c = c + '; path=/';
      document.cookie = c;
    }

function get_cookie(c_key) {
      var c_key_eq = c_key + "=";
      var cookies = document.cookie.split(';');
      var i;
      for(i = 0; i < cookies.length; i++) {
        var cookie = cookies[i];
        while (cookie.charAt(0)==' ') { 
          cookie = cookie.substring(1, cookie.length);
        }

        if (cookie.indexOf(c_key_eq) == 0) {
          return cookie.substring(c_key_eq.length, cookie.length);
        }
      }

      return null;
    }
	
// Determines if the marker is within the bounds of the visible part of the map at the current zoom level
function marker_is_in_view(marker) {
      var tlLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(1,1)).
            transform(map.getProjectionObject(),map.displayProjection);
      var mapsize = map.getSize();
      var brLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(mapsize.w - 1, mapsize.h - 1)).
            transform(map.getProjectionObject(),map.displayProjection);

      var tlLonLatF = new OpenLayers.LonLat(tlLonLat.lon, tlLonLat.lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
      var brLonLatF = new OpenLayers.LonLat(brLonLat.lon, brLonLat.lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());

      if (tlLonLatF.lon <= marker.lonlat.lon && marker.lonlat.lon <= brLonLatF.lon &&
          tlLonLatF.lat >= marker.lonlat.lat && marker.lonlat.lat >= brLonLatF.lat) {
        return 1;
      } else {
        return 0;
      }
    }

// Determines if the parameter is in the my_markers array
function marker_in_my_markers(marker) {
      for (var i = 0; i < my_markers.length; i++) {
        if (my_markers[i].lonlat.lon == marker.lonlat.lon && my_markers[i].lonlat.lat == marker.lonlat.lat) {
          return 1;
        }
      }
      return 0;
    }
	
function listener(evt) {
      var zoom = map.getZoom();
      var tlLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(1,1)).
            transform(map.getProjectionObject(),map.displayProjection);
      var mapsize = map.getSize();
      var brLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(mapsize.w - 1, mapsize.h - 1)).
            transform(map.getProjectionObject(),map.displayProjection);

      var url = request_url
           + "?z=" + zoom
           + "&l=" + tlLonLat.lon
           + "&t=" + tlLonLat.lat
           + "&r=" + brLonLat.lon
           + "&b=" + brLonLat.lat
		   + "&tt=all";
	  //console.log(url);

      // GET and process some markers
      $.get(url, function(data) { 
        // Remove markers that aren't within the bounds of the visible part of the map at the current zoom level
        // Keep markers that are within the bounds of the visible part of the map at the current zoom level
		//console.log(my_markers.length);
        var my_markers_2 = new Array();
        while (my_markers.length > 0) {
          var current_marker = my_markers.pop();
          if (last_zoom < map.getZoom() && marker_is_in_view(current_marker) == 1) {
            my_markers_2.push(current_marker);
          } else {
            nuke_markers.removeMarker(current_marker);
            current_marker.destroy();
          }
        }
        my_markers = my_markers_2;
        last_zoom = map.getZoom();
		
		lines=data.split("\n");
		
		for (i=1;i<lines.length-1;i++)
		{
			records=lines[i].split("\t");
			lat=records[0];
			lon=records[1];
			//console.log("\t["+i+"] "+lat+","+lon);
			iconurl=records[2];
			iconsize=records[3].split(",");
			iconoffset=records[4].split(",");
			title=records[5];
			desc=records[6];

          // Build a new marker
          var size = new OpenLayers.Size(iconsize[0], iconsize[1]);
          var offset = new OpenLayers.Pixel(iconoffset[0], iconoffset[1]);
          var icon = new OpenLayers.Icon(iconurl, size, offset);
          var lonLatMarker = new OpenLayers.LonLat(lon,lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
          var marker = new OpenLayers.Marker(lonLatMarker, icon);

          if (marker_in_my_markers(marker) == 1) {
            // if we already have this marker on the map, don't try to re-add it
            marker.destroy();
          } else {
            // Add the marker to the map
            var feature = new OpenLayers.Feature(nuke_markers, lonLatMarker);
            feature.closeBox = true;
            feature.popupClass = OpenLayers.Class(OpenLayers.Popup.AnchoredBubble, {autoSize:true, closeOnMove:true, minSize: new OpenLayers.Size(300, 180) } );
            feature.data.popupContentHTML = title+desc;
            feature.data.overflow = "auto";
            marker.feature = feature;

            var markerClick = function(evt) {
              if (this.popup == null) {
                this.popup = this.createPopup(this.closeBox);
                map.addPopup(this.popup);
                this.popup.show();
              } else {
                this.popup.toggle();
              }
              OpenLayers.Event.stop(evt);
            };

            marker.events.register("mousedown", feature, markerClick);

            nuke_markers.addMarker(marker);
            my_markers.push(marker);
          } 
        }
      });

      var centerLonLat = map.getLonLatFromPixel(new OpenLayers.Pixel(mapsize.w / 2, mapsize.h / 2)). transform(map.getProjectionObject(),map.displayProjection);

      set_cookie('lon', centerLonLat.lon);
      set_cookie('lat', centerLonLat.lat);
      set_cookie('zoom', map.getZoom());
    }

// init the OpenLayers Map objects
function init(){
	// the map
    map = new OpenLayers.Map('map',
		{ 	maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
			numZoomLevels: 19,
			maxResolution: 156543.0399,
			units: 'm',
			projection: new OpenLayers.Projection("EPSG:900913"),
			displayProjection: new OpenLayers.Projection("EPSG:4326"),
		  	controls:[
						new OpenLayers.Control.Permalink(),	// permalink option (enable user to get a direct to the current view)
						new OpenLayers.Control.Navigation(), // navigation option (enable mouse dragging)
						new OpenLayers.Control.LayerSwitcher(), // layer option (enable layer popup to change display)
						new OpenLayers.Control.Attribution(), // attribution option (display attribution licence)
						new OpenLayers.Control.ScaleLine(), // add a scale bar
						new OpenLayers.Control.PanZoomBar() // panzoom option (enable zooming)
				  ]
		});
 			
	// get map rendered layers (from OSM : mapnik and tiles@Home + from OpenMapQuest)
	var layerMapnik = new OpenLayers.Layer.OSM.Mapnik("Mapnik");
	var mapquest = new OpenLayers.Layer.OSM.OpenMapQuest("OpenMapQuest");
	
	var style = new OpenLayers.Style({
						pointRadius:5						
									 });
	
	// create a marker layer from text data using the correct projection (from map display)
	nuke_markers = new OpenLayers.Layer.Markers("Filières");
	nuke_markers.setIsBaseLayer(false);
	nuke_markers.setVisibility(true);	

	// create layer to display heatmap (colored circle from source points)
	heat = new Heatmap.Layer("Autour des centrales",{projection:map.displayProjection});
	heat.defaultIntensity = 1.0;
	heat.setOpacity(0.5);
	heat.setIsBaseLayer(false);
	heat.setVisibility(true);	
	
	// register the heatmap updater for each updates of the current view
	map.events.register("moveend", this, getNukeHeatMap);
	map.events.register("moveend", this, listener);

	// add the layers to the map
	map.addLayers([layerMapnik,mapquest,heat,nuke_markers]);
 
 	// position the map to the default view
	var lonLat = new OpenLayers.LonLat(lon, lat).transform(map.displayProjection,  map.projection);
	if (!map.getCenter()) map.setCenter (lonLat, zoom);
}
