<?php
# Generate a text output (UTF-8 encoded) that match OpenLayers Layer data format :
#	- latitude and longitude (lat,lon)
#	- icon picture url (url)
#	- icon size (x,y)
#	- icon offset (x,y)
#	- title (text, html accepted)
#	- description (text, html accepted)
#
# Output is generate for the 2 layers (city data and cctv localisation), 
# data are extracted from the local MySQL database
# parameters (html url) :
#	- l : left (latitude)
#	- r : right (longitude)
#	- t : top
#	- b : bottom
#	- z : zoom level
#	- tt : type of data

# debug :
# http://www.leretourdelautruche.com/map/nuke/nuke_request.php?z=8&l=-131.5&t=64.9&r=-53.8&b=11.7&tt=all

#header to define the texte file as UTF8 encoded
header("Content-type: text/plain; charset=UTF-8");

// UTF-8 enable this script
mb_language('uni');
mb_internal_encoding('UTF-8');

#include config file (define serveur and paths)
require("./config.php");

#$dbg=True;
$canedit=True;

function write_header()
{
#       lat  lon  icon  iconSize  iconOffset  title  description
 print("lat\tlon\ticon\ticonSize\ticonOffset\ttitle\tdescription\n");
}

function write_line_osm($row,$z)
{
	# lat  lon
    echo $row["lat"]."\t".$row["lon"]."\t";
	#  icon url, size and offset
	if ($row["active"]==0)
	{
		$icon="./nuke-20x20.png\t20,20\t-10,-10\t";
		if ($row["type"]=="power")
		{
			$icon="./power-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="mine")
		{
			$icon="./mine-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="waste")
		{
			$icon="./waste-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="explosion")
		{
			$icon="./explosion-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="factory")
		{
			$icon="./factory-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="military")
		{
			$icon="./military-20x20.png\t20,20\t-10,-10\t";
		}
	}
	else
	{
		$icon="./nuke-disused-20x20.png\t20,20\t-10,-10\t";
		if ($row["type"]=="power")
		{
			$icon="./power-disused-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="mine")
		{
			$icon="./mine-disused-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="waste")
		{
			$icon="./waste-disused-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="explosion")
		{
			$icon="./explosion-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="factory")
		{
			$icon="./factory-disused-20x20.png\t20,20\t-10,-10\t";
		}
		if ($row["type"]=="military")
		{
			$icon="./military-disused-20x20.png\t20,20\t-10,-10\t";
		}
	}
	echo $icon;
	#  title
 	echo utf8_encode("<h2>".$row["name"]."</h2>\t");
	#  description
 	echo utf8_encode("<p>".$row["text"]."<br>latitude=".$row["lat"]."<br>longitude=".$row["lon"]."</p>");
 	echo "\n";
}

function fetch_poi_osm($query,$connect,$z,$dbg)
{
	global $dbg;
	
    $res = mysql_query($query,$connect) or die("select error : ".mysql_error());

	$nb=mysql_num_rows($res);
	if ($dbg) { echo("Nb ligne(s) : ".$nb."\n"); }
	if ($nb > 0)
    {
    	while ($row = mysql_fetch_array ($res))
    	{
            write_line_osm($row,$z);
        }
    }
    mysql_free_result($res);
}

# get box (longitude, latitude) and zoom level (as parameters)
$left = $_GET["l"];
$top = $_GET["t"];
$right = $_GET["r"];
$bottom = $_GET["b"];
$zoom = $_GET["z"];
$type = $_GET["tt"];

if ($left>$right)
{
    $temp =$left;
    $left=$right;
    $right=$temp;
}

if ($bottom>$top)
{
    $temp =$top;
    $top=$bottom;
    $bottom=$temp;
}

# connect to MySQL database
$connect = mysql_connect($server,$login,$pwd) or die("connect error : ".mysql_error());
mysql_select_db($database,$connect) or die("select db : ".mysql_error()) ;

# write the output text 
write_header();

# query geolocalisation from database
$query = "SELECT nuke.latitude as lat, nuke.longitude as lon, nuke.type as type, nuke.name as name, nuke.text as text, nuke.active as active\n";
$query .= " FROM nuke WHERE\n";
if ($type=="all")
{
	$query .= " nuke.longitude>=$left AND nuke.longitude<$right AND nuke.latitude>=$bottom AND nuke.latitude<$top\n";
}
else
{
	$query .= " nuke.longitude>=$left AND nuke.longitude<$right AND nuke.latitude>=$bottom AND nuke.latitude<$top AND nuke.type='$type'\n";
}

if ($dbg) {
    echo($query."\n"); }

fetch_poi_osm($query,$connect,$z,$dbg);

mysql_close($connect);

?>