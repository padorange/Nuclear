#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
	nuke.py
	----------------
	Extract data from OpenStreetpMap and construct a MySQL data to be used via OpenLayers
	
	Download OSM data from a zone (boudingbox) and parse them according to a polygon area
	to extract specific POI and prepare them to be used in an OpenLayers online map.
	The polygon area is extracted from the OSM's boundary relation (admin_level=8)
	Data are finally formatted for openlayers text layer and upload to a ftp server
	
	Usage :
		python nuke.py [-download]
		- download option force downloading of OSM data, otherwise use existing file (if any)
	
	Informations
		OSM's XAPI specification :
			<http://wiki.openstreetmap.org/wiki/Xapi>
	
	Licence :
		Pierre-Alain Dorange, april 2011
		Code (python and js) : BSD Licence
		OSM Data : CC-BY-SA 2.0
		Icons : Google Map Icons, CC-BY-SA 3.0
			<http://code.google.com/p/google-maps-icons/>
"""

# standard python modules
import os	# some utility functions from the OS (file, directory...)
import sys	# used to recover exception errors and messages
import urllib2	# used to download OSM data through XAPI interface
from xml.etree import ElementTree # used to parse XML data (very fast API)
import ftplib # used to connect to ftp and push the new data file
import webbrowser # used to open the user browser
import codecs # used to read/write text file with the correct encoding
import time, datetime	# used to chronometer functions

import pyOSM
import config

# constants
__version__="0.4"
_debug_=False

# url for the XAPI query
url="http://open.mapquestapi.com/xapi/api/0.6/*[power=generator]"

# file names
xml_filename="./data/power.xml" # osm data file (downloaded or cached)
text_filename="./data/nuke.txt" # openlayer data file (text format)
mysql_filename="./data/nuke.sql" # mysql importer (text format, utf-8)
area_filename="./data/fr_0.xml"

# what to map with openlayers
query= (	("power_source","nuclear","radiation.png",("nuke",)),
			("generator:source","nuclear","radiation.png",("nuke",))
		)
		
sub_query= ( ("disused","yes","radiation-disused.png"),
			 ("end_date","*","radiation-disused.png")
			)

def get_area(relations,ways,nodes,name):
	"""
		get_area
		extract from relations, ways and nodes list an admin boundary (level=8 for city)
		build a way (osm data structure) for this boundary
	"""
	id=-1
	area=pyOSM.Area()
	# scan relations to find the right boundary=administrative (admin_level=8 + name)
	for r in relations:
		is_zone=False
		is_subzone=False
		is_name=False
		for tag in r.getiterator("tag"):	
			k=tag.get("k")
			if k==zone_tag:
				if tag.get("v")==zone_value:
					is_zone=True
			if k==zone_subtag:
				if tag.get("v")==zone_subvalue:
					is_subzone=True
			if k=="name":
				if tag.get("v")==name:
					is_name=True
		# we match the correct relation : handle it
		if is_zone and is_subzone and is_name:
			id=long(r.get("id"))
			if _debug_:
				print "\tfound relation:",id,"build way(s) and node(s)"
			waylist=[]
			nodelist=[]
			# extract members to build in memory the way list and node(s) corresponding (with location)
			for m in r.getiterator("member"):
				if m.get("type")=="way":
					ref=long(m.get("ref"))
					w=pyOSM.Way(ref)
					waylist.append(w)
			if len(waylist)>0:	# scan way list and pre-build nodes
				print "\t\textract",len(waylist),"way(s)"
				for w in ways:
					wid=long(w.get("id"))
					wo=pyOSM.is_in(waylist,wid)
					if wo!=None:
						for t in w.getiterator("tag"):
							name=t.get("name")
							if name!=None:
								wo.name=name
						nb=0
						for n in w.getiterator("nd"):
							nid=long(n.get("ref"))
							nodelist.append((wid,nid))
							n0=pyOSM.Node(nid)
							wo.add_node(n0)
							nb=nb+1
			if len(nodelist)>0:	# complete node informations for way list by scanning all the nodes and extract location
				print "\t\textract",len(nodelist),"node(s)"
				for node in nodes:
					ref=long(node.get("id"))
					for i in nodelist:
						if i[1]==ref:
							wo=pyOSM.is_in(waylist,i[0])
							if wo:
								n=wo.get_node(ref)
								if n!=None:
									ll=float(node.get("lat"))
									lo=float(node.get("lon"))
									n.location=(ll,lo)
			if len(waylist)>0:
				# ordered the way in the logical order to describe the polygon (the last node of a way is the first of the next)
				print "\t\tordering",len(waylist),"ways"
				area.add_sorted_ways(waylist)
				
	return area
	
class Candidate(pyOSM.Node):
	# a candidate (node) for display on final openlayers map
	def __init__(self,id=-1,location=(0.0,0.0)):
		pyOSM.Node.__init__(self,id,location)
		self.operator=""
		self.power=""
		self.start=""
		self.end=""
		self.disused=False
		self.url=""
		self.country=""
		self.name_fr=""
		self.name_en=""
		self.ref=""
	
	def handleTag(self,tag,value):
		# scan tags for a candidate and store required data
		if tag=="ref":
			self.ref=value
		if tag=="name":
			self.name=value
		if tag=="name:fr":
			self.name_fr=value
		if tag=="name:en":
			self.name_en=value
		if tag=="operator":
			self.operator=value
		if tag=="power_rating" or tag=="generator:output" or tag=="generator:output:electricity":
			self.power=value
		if tag=="start_date":
			self.start=value
		if tag=="end_date":
			self.end=value
			self.disused=True
		if tag=="disused":
			if value!='no':
				self.disused=True
		if tag=="url":
			self.url=value
		if tag=="wikipedia":
			v=value.split(":")
			if len(v)==2:
				if v[0]=="http":
					self.url=value
				else:
					self.url="http://%s.wikipedia.org/wiki/%s" % (v[0],v[1])
			else:
				self.url=value
	
	def buildString(self):
		str="id=%d (%s), name=%s" % (self.osm_id,self.osm_id_type,self.name)
		str=str+""
		return str
		
	def buildDescriptor(self):
		desc=u""	# build description text
		prefix=u""
		if len(self.operator)>0:
			desc=desc+prefix+u"opérateur : "+self.operator
			prefix=u"</br>"
		if len(self.ref)>0:
			desc=desc+prefix+u"réf : "+self.ref
			prefix=u"</br>"
		if len(self.start)>0:
			desc=desc+prefix+u"mise en service : "+self.start
			prefix=u"</br>"
		if self.disused:
			desc=desc+prefix+u"arrêt : "+self.end
			prefix=u"</br>"
		if len(self.power)>0:
			desc=desc+prefix+u"puissance : "+self.power
			prefix=u"</br>"
		if len(self.url)>0:
			if self.url.find('wikipedia')>0:
				target=u"wikipedia"
			else:
				target=u"lien"
			desc=desc+prefix+u"<a href='"+self.url+"' target='_blank'>%s</a>" % target
			prefix="</br>"
		if len(desc)==0:
			desc=u"</br>"
		# if more name specify, used french, then english, then locale one
		if len(self.name_en)>0:
			self.name=self.name_en
		if len(self.name_fr)>0:
			self.name=self.name_fr
		return desc

def check_poi(relations,ways,nodes,area=None):
	print "extracting node(s) from area"
	p=check_poi_nodes(nodes,area)
	poi=p
	print "extracting way(s) from area"
	p=check_poi_ways(ways,nodes,area)
	poi.extend(p)
	print "extracting relation(s) from area"
	p=check_poi_relations(relations,ways,nodes,area)
	poi.extend(p)
	return poi
	
def check_poi_relations(relations,ways,nodes,area):
	""" scan relations, looking for tags (query) in the area and return a node list (compute barycenter for relation) """
	t0=time.time()
	poi=[]
	nbTag=0
	nb=len(relations)
	for r in relations:
		id=long(r.get("id"))
		node=Candidate()
		match=None
		for tag in r.getiterator("tag"):
			k=tag.get("k")
			v=tag.get("v")
			if k and v:
				for k0,v0,icon,lname in query:
					if k==k0 and (v0=="*" or v==v0):
						if match==None:
							node.osm_id=id
							node.osm_id_type="relation"
							node.icon=icon
							node.layer_name=lname
							node.rawtags=r.getiterator("tag")
							match=node
						node.tags.append((k,v))
				node.handleTag(k,v)
		if match:	# match query, compute nodes barycentre
			if sub_query:
				for tag in match.rawtags:
					k=tag.get("k")
					v=tag.get("v")
					for k0,v0,icon in sub_query:
						if k==k0 and (v0=="*" or v==v0):
							match.icon=icon
			nodesID=[]
			waysID=[]
			for m in r.getiterator("member"):
				ref=long(m.get("ref"))
				type=m.get("type")
				if type=="node":
					nodesID.append(ref)
				if type=="way":
					waysID.append(ref)
			if len(waysID)>0:
				for w in ways:
					ref=long(w.get("id"))
					if ref in waysID:
						for n in w.getiterator("nd"):
							ref=long(n.get("ref"))
							nodesID.append(ref)
			if len(nodesID)>0:
				nb_nodes=0
				lat,lon=(0.0,0.0)
				for n in nodes:
					ref=long(n.get("id"))
					if ref in nodesID:
						ll=float(n.get("lat"))
						lo=float(n.get("lon"))
						if ll and lo:
							lat=lat+ll
							lon=lon+lo
							nb_nodes=nb_nodes+1
				if nb_nodes>0:
					lat=lat/nb_nodes
					lon=lon/nb_nodes
				match.location=(lat,lon)
				if area:
					if area.node_in(match):
						match.country="france"
				nbTag=nbTag+1
				poi.append(match)
				str=match.buildString()
				print str
				
	t0=time.time()-t0
	print "%d relations scanned (%d with tag, %.1f seconds)" % (nb,nbTag,t0)
	return poi
	
def check_poi_ways(ways,nodes,area):
	""" scan ways, looking for tags (query) in the area and return a node list (compute barycenter for way) """
	t0=time.time()
	poi=[]
	nbTag=0
	nb=len(ways)
	
	for w in ways:
		id=long(w.get("id"))
		node=Candidate()
		match=None
		for tag in w.getiterator("tag"):
			k=tag.get("k")
			v=tag.get("v")
			if k and v:
				for k0,v0,icon,lname in query:
					if k==k0 and (v0=="*" or v==v0):
						if match==None:
							node.osm_id=id
							node.osm_id_type="way"
							node.icon=icon
							node.layer_name=lname
							node.rawtags=w.getiterator("tag")
							match=node
						node.tags.append((k,v))
				node.handleTag(k,v)
		if match:	# match query, compute nodes barycentre
			if sub_query:
				for tag in match.rawtags:
					k=tag.get("k")
					v=tag.get("v")
					for k0,v0,icon in sub_query:
						if k==k0 and (v0=="*" or v==v0):
							match.icon=icon
			nodeWay=[]
			for n in w.getiterator("nd"):	# get nodes references (list)
				ref=long(n.get("ref"))
				nodeWay.append(ref)
			if len(nodeWay)>0:
				lat,lon=(0.0,0.0)
				nb_nodes=0
				for n in nodes:
					ref=long(n.get("id"))
					if ref in nodeWay:	# only candidate nodes	
						ll=float(n.get("lat"))
						lo=float(n.get("lon"))
						if ll and lo:
							lat=lat+ll
							lon=lon+lo
							nb_nodes=nb_nodes+1
				if nb_nodes>0:
					lat=lat/nb_nodes
					lon=lon/nb_nodes
				match.location=(lat,lon)
				if area:
					if area.node_in(match):
						match.country="france"
				nbTag=nbTag+1
				poi.append(match)
				str=match.buildString()
				print str
				
	t0=time.time()-t0
	print "%d ways scanned (%d with tag, %.1f seconds)" % (nb,nbTag,t0)
	return poi
	
def check_poi_nodes(nodes,area):
	""" scan nodes, looking for tags (query) in the area and return a node list """
	t0=time.time()
	poi=[]
	nbTag=0
	nbIn=0
	nb=len(nodes)
	if _debug_:
		log=codecs.open("log_nodes.txt","w",encoding="utf-8")
	else:
		log=None
	if log:
		log.write("lat\tlon\tid\tis_in\ttags...\n")
	for n in nodes:
		ll=float(n.get("lat"))
		lo=float(n.get("lon"))
		if log:
			log.write("%.4f\t%.4f\t" % (ll,lo))
		if ll and lo:
			id=long(n.get("id"))
			if log:
				log.write("%d\t" % id)
			node=Candidate(id,(ll,lo))
			node.osm_id_type="node"
			if area:
				if area.node_in(node):
					node.country="france"
			if log:
				log.write("yes\t")
			nbIn=nbIn+1
			hasTag=False
			for tag in n.getiterator("tag"):
				k=tag.get("k")
				v=tag.get("v")
				if log:
					log.write("%s=%s\t" % (k,v))
				if k and v:
					for k0,v0,icon0,label0 in query:
						if k==k0 and (v0=="*" or v==v0) :
							node.icon=icon0
							node.layer_name=label0
							node.tags.append((k,v))
							hasTag=True
							if sub_query:
								for k1,v1,icon in sub_query:
									if k==k1 and (v1=="*" or v==v1):
										match.icon=icon1
					node.handleTag(k,v)
			if hasTag:
				nbTag=nbTag+1
				poi.append(node)
				str=node.buildString()
				print str
			else:
				if log:
					log.write("no\t")
				for tag in n.getiterator("tag"):
					k=tag.get("k")
					v=tag.get("v")
					if log:
						log.write("%s=%s\t" % (k,v))
	if log:
		log.write("\n")
	if log:
		log.close()
	t0=time.time()-t0
	print "%d nodes scanned (%d with tag, %d in area, %.1f seconds)" % (nb,nbTag,nbIn,t0)
	return poi

class mysqlPOIExporter():
	def __init__(self,filename):
		self.outFileName=filename
	
	def exportData(self,poi):
		file=codecs.open(self.outFileName,"w",encoding="utf-8")
		file.write("-- nuke.py (%s) SQL dump\n\n"% __version__)
		file.write("""CREATE TABLE IF NOT EXISTS `nuke` (
					`osmid` bigint(20) NOT NULL default '0',
					`osmtype` varchar(10) collate utf8_bin NOT NULL default '',
					`longitude` float NOT NULL default '0',
					`latitude` float NOT NULL default '0',
					`name` varchar(80) collate utf8_bin NOT NULL default '',
					`country` varchar(80) collate utf8_bin NOT NULL default '',
					`text` varchar(250) collate utf8_bin NOT NULL default '',
					`active` int(11) NOT NULL default '0',
					PRIMARY KEY  (`osmid`)
					) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_bin;""")
		file.write("\n\n")
		file.write("\n-- Contenu TABLE city\n\n")
		file.write("INSERT INTO `nuke` (`osmid`, `longitude`, `latitude`, `name`, `country`, `text`, `active`) VALUES")
		prefix="\n"
		for p in poi:
			desc=p.buildDescriptor()	# build description text
			if p.disused:
				active=1
			else:
				active=0
			file.write('%s(%d,%.6f,%.6f,"%s","%s","%s",%d)' % (prefix,p.osm_id,p.location[1],p.location[0],p.name,p.country,desc,active))
			prefix=",\n"
		file.write(";\n")
		file.close()
	
class ftpPOIExporter():
	def __init__(self,host,user,password):
		self.host=host
		self.user=user
		self.password=password
		
	def exportData(self,poi):
		# export POI to a text file formatted for OpenLayers Text Layer
		poi_files={}
		size=(32,37)
		offset=(-16,-34)
		for p in poi:
			for layer in p.layer_name:
				# build text files
				f=layer+".txt"
				try:
					file=poi_files[f]
				except:
					file=codecs.open(f,"w",encoding="utf-8")
					poi_files[f]=file
					file.write("point\ttitle\tdescription\ticonSize\ticonOffset\ticon\n")
				desc=p.buildDescriptor()	# build description text
				icon="%s%s" % (config.icons_url,p.icon)	
				file.write("%.7f,%.7f\t%s\t%s\t%d,%d\t%d,%d\t%s\n" % (p.location[0],p.location[1],p.name,desc,size[0],size[1],offset[0],offset[1],icon))
			
		# write and upload text files
		for f,file in poi_files.iteritems():
			self.sendTextFile(config.ftp_directory,f)	
	
	def sendTextFile(self,directory,filename):
		try:
			file=open(filename,"r")
			try:	
				ftp=ftplib.FTP(self.host)
				ftp.login(self.user,self.password)
				ftp.set_pasv(True)
				ftp.storlines("STOR %s/%s" % (directory,filename),file)
				file.close()
				ftp.quit()
			except ftplib.all_errors:
				print "FTP errorcmd :"
				print sys.exc_info()
			except:
				print "error during ftp :",sys.exc_info()
		except:
			print "error reading local file %s :" % filename,sys.exc_info()

def parse_data(fname,ga=False):
	if ga:
		area=pyOSM.Area()
		area.read(area_filename)		
	else:
		area=None

	size=Bytes2Str(os.path.getsize(fname))
	print "Open OSM file :",fname,"(%s)" % size
	t0=time.time()
	tree=ElementTree.parse(fname)
	root=tree.getroot()
	t0=time.time()-t0
	print "Parse XML data (%.1f seconds)" % t0

	t0=time.time()
	nodes=root.getiterator("node")
	ways=root.getiterator("way")
	relations=root.getiterator("relation")
	t0=time.time()-t0
	print "* analyze %d node(s) + %d way(s) + %d relation(s) (%.1f seconds)" % (len(nodes),len(ways),len(relations),t0)
	
	# find the POI inside the boundary
	t0=time.time()
	poi=check_poi(relations,ways,nodes,area)
	t0=time.time()-t0
	print "* extract",len(poi),"POI(s) within boundary and match query (%.1f seconds)" % t0

	print "* export data to FTP host",config.ftp_host
	ftp=ftpPOIExporter(config.ftp_host,config.ftp_user,config.ftp_password)
	ftp.exportData(poi)
	
	print "* export data to mysql database",mysql_filename
	mysql=mysqlPOIExporter(mysql_filename)
	mysql.exportData(poi)
		
# functions

def Bytes2Str(size):
	try:
		units=["B","KB","MB"]
		u=0
		while (size>1024) and (u<2):
			size=size/1024
			u=u+1
		if u==0:
			return "%d %s" % (size, units[u])
		else:
			return "%.2f %s" % (size, units[u])
	except:
		return "*** Bytes2Str error"

def GetData(url,fname):
	print "Download to %s from OSM (via xapi)..." % fname
	try:
		stream=urllib2.urlopen(url, None)
		if stream:
			size=stream.info().getheader("Content-Length")
			file=open(fname,"wb")
			data=stream.read()
			bytes=0
			for line in data:
				bytes=bytes+len(line)
				file.write(line)
			stream.close()
			file.close()
	except:
		print "error can't load over internet : ",sys.exc_info()
			
def main(args):
	print "-------------------------------------------------"
	download=False
	area=False
	for arg in args:
		if arg=="-download" : 
			download=True
	if not download:
		if not os.path.exists(xml_filename):
			download=True
	if download:
		GetData(url,xml_filename)

	parse_data(xml_filename,True)
	
	print "-------------------------------------------------"
		
if __name__ == '__main__' :
    main(sys.argv[1:])
