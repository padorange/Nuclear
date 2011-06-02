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
		echo "./nuke-central-20x20.png\t20,20\t-10,-10\t";
	}
	else
	{
		echo "./nuke-disused-20x20.png\t20,20\t-10,-10\t";
	}
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
$query = "SELECT nuke.latitude as lat, nuke.longitude as lon, nuke.name as name, nuke.text as text, nuke.active as active\n";
$query .= " FROM nuke WHERE\n";
$query .= " nuke.longitude>=$left AND nuke.longitude<$right AND nuke.latitude>=$bottom AND nuke.latitude<$top\n";

if ($dbg) {
    echo($query."\n"); }

fetch_poi_osm($query,$connect,$z,$dbg);

mysql_close($connect);

?>