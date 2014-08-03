<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
	<link href="style.css" rel="stylesheet" type="text/css" media="screen" />
  	<link rel="icon" type="image/png" href="./nuke.ico" />
    <script type="text/javascript" src="../OpenLayers/OpenLayers.js" charset="utf-8"></script>
    <script type="text/javascript" src="../osm/OpenStreetMap.js" charset="utf-8"></script>
    <script type="text/javascript" src="./jquery.js" charset="utf-8"></script>
	<script type="text/javascript" src="./heatmap.js" charset="utf-8"></script>
    <script type="text/javascript" src="./nuke_map.js" charset="utf-8"></script>
  	<title>Fili&egrave;res Nucl&eacute;aires autour du monde</title>
</head>
  	<body onLoad="init()">
		<div id="logo">
			<h1>Filières Nucléaires autour du monde</h1>
			<p>Avec un rayon de 100 kilomètres autour des centrales</p>
	</div>
	<div id="map"></div>
	<div id="about">
		<p><em><a href="about.html">A propos de la carte</a> :: Donn&eacute;es extraites de <a href="http://www.openstreetmap.org/">OpenStreetMap</a>
		<script type="text/javascript">
		<!--
			/* get the modification date of the cctv.txt file */
			var request=new XMLHttpRequest();
			request.open("HEAD","http://www.leretourdelautruche.com/map/nuke/nuke.txt",false);
			request.send(null);
			var date=request.getResponseHeader("Last-Modified")
			document.writeln(date)
		-->
		</script>
		<noscript>
		no javascript
		</noscript>
			</em><br>
		r&eacute;alis&eacute; par <a href="http://www.leretourdelautruche.com/map/">Pierre-Alain Dorange</a> avec Javascript+OpenLayers, MySQL, PHP et Python.</p>
  </div>
  <?php
		// UTF-8 enable the PHP and HTML
		mb_language('uni');
		mb_internal_encoding('UTF-8');

		require("./config.php");
		$connect = mysql_connect($server,$login,$pwd) or die("connect error : ".mysql_error());
		mysql_select_db($database,$connect) or die("select db : ".mysql_error()) ;

		$query="select * from nuke where country='france' order by type,name";
					
		$result = mysql_query($query,$connect) or die("select error : ".mysql_error());
		echo "<div id='list'>Filières Françaises<ul>";
		$last="";
		while ($row = mysql_fetch_array($result))
		{
			$lat=$row[latitude];
			$lon=$row[longitude];
			$t=$row[type];
			if ($t!=$last)
			{
				echo '<li><b>'.$t.'</b></li>';
				$last=$t;
			}
			echo '<li><b><a href="http://www.leretourdelautruche.com/map/nuke/index.php?zoom=15&lat='.$lat.'&lon='.$lon.'">'.$row[name].'</a></b></li>';
		}
		echo '</ul></div>';
			
		mysql_close($connect);
	?>
<!-- Start of StatCounter Code -->
	<script type="text/javascript" language="javascript">
	var sc_project=1651860; 
	var sc_invisible=1; 
	var sc_partition=15; 
	var sc_security="9710e8ad"; 
	</script>
	<script type="text/javascript" language="javascript" src="http://www.statcounter.com/counter/counter.js"></script>
	<noscript>
		<a href="http://www.statcounter.com/" target="_blank">
		<img  src="http://c16.statcounter.com/counter.php?sc_project=1651860&amp;java=0&amp;security=9710e8ad&amp;invisible=1" alt="hit counter script" border="0">
		</a>
	</noscript>
	<!-- End of StatCounter Code -->
	</body>
</html>