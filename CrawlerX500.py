# -*- coding: utf-8 -*-
# Author: Yang *
# Date  : 2014-11-03 
#
# Note  : Crawler For X500
#
#

#URL
#http://directory.app.alcatel-lucent.com/Rupi=CV00*****&S=YANG*

import os, sys, re, random
sys.path.append( os.path.dirname( os.path.abspath(__file__) ) )
import socket, urllib, urllib2, pprint, copy, optparse
import pymongo
from bs4 import BeautifulSoup #https://pypi.python.org/pypi/beautifulsoup4/4.3.2


class X500Crawler(object):
	def __init__(self, start_upi = 'CV0023830',home_url='http://directory.app.alcatel-lucent.com'):
		#MongoDB
		self.conn   = pymongo.Connection(host='135.251.224.97',port=27017)
		self.dbname = "ALU_X500"
		self.db     = self.conn[self.dbname]
		self.collect= self.db.normal

		#Directory
		self.rootpath       = os.path.dirname( os.path.abspath(__file__) )
		self.htmlpath       = os.path.join( self.rootpath, "HTML")
		self.facepath       = os.path.join( self.rootpath, "Face")
		if not os.path.exists(self.htmlpath):
			os.makedirs(self.htmlpath)
		if not os.path.exists(self.facepath):
			os.makedirs(self.facepath)
		#URL
		self.url_root       = home_url
		#self.url_startpoint = '%s/Rupi=%s' % (self.url_root, start_upi)  #'http://directory.app.alcatel-lucent.com/Rupi=CV00****'
		#Queue
		self.queue_uncheck    = []
		self.queue_checked    = []
		self.queue_uncheck.append(start_upi)
		self.queue_checked_ok = []
		self.queue_checked_ko = []

		#Infomation Template
		self.colleague_info = { 'UPI'      : '',
		                        'Name'     : '',
		                        'Email'    : '',
		                        'CSL'      : '',
		                        'CostCenter':'',
		                        'UserType' : '',

		                        'OnNET'    : '',
		                        'Phone'    : '',
		                        'Mobile'   : '',
		                        'Assistant': '',

		                        'Department'   :'',
		                        'JobFamily'    :'',
		                        'BusinessTitle':'',
		                        'Supervisor'   :'',
		                        'SupervisorUPI':'',
		                        'AdminApproval':'',
		                        'AdminApprovalUPI':'',
		                        'Company'      :'',
		                        'WorkAddress'  :'',
		                        'Building'     :'',
		                        'Office'       :'',

		                        'FaceUrl'      :'http://faces.all.alcatel-lucent.com/l/',
		                        'X500Url'      :''
		                      }


	def get_html_content(self, url):
		'''
		e.g., http://directory.app.alcatel-lucent.com/Rupi=CV00*****
		'''
		#url
		print "[URL]:", url

		#content
		html_content = ''

		#proxy
		proxy_handler = urllib2.ProxyHandler( {"http" : 'http://%s:%s@135.251.33.15:8080' % ( '****', '******') } )
		opener = urllib2.build_opener(proxy_handler,urllib2.HTTPSHandler(debuglevel=0))
		urllib2.install_opener(opener)
		authheader =  None#"Basic %s" % base64.encodestring('%s:%s' % ('***', '***'))[:-1]
		data=None

		#fetch the content of this url
		try:
			req = urllib2.Request(url,data)
			req.add_header("Authorization", authheader)
			req.add_header('User-Agent' , 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0')
			handle = urllib2.urlopen(req)
			html_content = handle.read()
		except Exception, e:
				print e
		finally:
			req = None
		#some specified characters
		html_content_verified = html_content.replace('&nbsp;','')
		html_content_verified = html_content_verified.replace('&deg','')
		html_content_verified = html_content_verified.replace('&Auml','')
		html_content_verified = html_content_verified.replace(r'Pós Venda','')
		html_content_verified = html_content_verified.replace(r'&eacute;','')
		html_content_verified = html_content_verified.replace(r'Á','')
		html_content_verified = html_content_verified.replace(r'Í','')
		return html_content_verified

	def save_html_content_to_disk(self, html_content, targetfile):
		fp = open(targetfile,'w')
		for line in html_content:
			fp.write( line)
		fp.close()
		return True

	def parse_html_content(self, html_content, current_upi):
		current_upi_info            = copy.deepcopy(self.colleague_info)
		current_upi_info["UPI"]     = current_upi
		current_upi_info["X500Url"] = 'http://directory.app.alcatel-lucent.com/Rupi=' + current_upi
		current_upi_info["FaceUrl"] = 'http://faces.all.alcatel-lucent.com/l/'        + current_upi
		#Prase using BeautifulSoup
		soup                    = BeautifulSoup(html_content, from_encoding="utf-8")
		#print soup.title
		#Name
		flag = False
		retry_times = 0
		Name = None
		while not flag:
			retry_times+=1
			print "[%d] Try to Extract Name! @@@" % retry_times
			try:
				Name =  soup.findAll(attrs={"class":"person_title"})[0].string
			except Exception, e:
				print e
			else:
				flag = True
		#Name =  soup.findAll(attrs={"class":"person_title"})[0].string
		current_upi_info["Name"]   = str(Name)
		print "Name:", Name

		#Persion Items
		divs =  soup.findAll('div',{'class':'person_item'})
		for div in divs:
			#print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
			#print div
			div_html =  '<html>'+str(div)+'</html>'
			div_html = re.sub('<br/>', '', div_html)
			div_soup = BeautifulSoup(div_html)
			if not div.findAll('div',{'class':'person_attr_name'}):
				continue
			person_attr_name  = div_soup.findAll('div',{'class':'person_attr_name'})[0].string
			person_attr_value = div_soup.findAll('div',{'class':'person_attr_value'})[0]
			if not person_attr_name or not person_attr_value:
				continue
			#WorkAddress
			if re.search( 'Work', person_attr_name, re.IGNORECASE):
				person_attr_value = person_attr_value.string#.strip()
				person_attr_name  = person_attr_name#.strip()
				current_upi_info["WorkAddress"]   = str(person_attr_value)
			#OnNET|Company|CSLogin|Email|UPI|Cost|User|Building|Office|Department|Organization|family|title
			elif re.search( 'OnNET|Company|CSLogin|Email|UPI|Cost|User|Building|Office|Department|Organization|family|title', person_attr_name, re.IGNORECASE):
				person_attr_name  = person_attr_name#.strip()
				try:
					person_attr_value = person_attr_value.string#.strip()
				except Exception, e:
						print e
				#finally:
				#	person_attr_value = None
				if "OnNET" in person_attr_name:
					current_upi_info["OnNET"]  = str(person_attr_value)
				elif "Company" in person_attr_name:
					current_upi_info["Company"]  = str(person_attr_value)
				elif "CSLogin" in person_attr_name:
					current_upi_info["CSL"]  = str(person_attr_value)
				elif "Email" in person_attr_name:
					current_upi_info["Email"]  = str(person_attr_value)
				elif "UPI" in person_attr_name:
					assert person_attr_value==current_upi_info["UPI"] 
				elif "Cost" in person_attr_name:
					current_upi_info["CostCenter"]  = str(person_attr_value)										
				elif "User" in person_attr_name:
					current_upi_info["UserType"]  = str(person_attr_value)
				elif "Building" in person_attr_name:
					current_upi_info["Building"]  = str(person_attr_value)
				elif "Office" in person_attr_name:
					current_upi_info["Office"]  = str(person_attr_value)
				elif "Department" in person_attr_name:
					current_upi_info["Department"]  = person_attr_value
				elif "Organization" in person_attr_name:
					current_upi_info["Organization"]  = str(person_attr_value)										
				elif "family" in person_attr_name:
					current_upi_info["JobFamily"]  = str(person_attr_value)
				elif "title" in person_attr_name:
					current_upi_info["BusinessTitle"]  = person_attr_value
			#Supervisor|Administrator
			elif re.search( 'Supervisor|Administrator', person_attr_name, re.IGNORECASE):
				person_attr_name  = person_attr_name#.strip()
				#Admin/Superior UPI
				person_attr_name_upi = ""
				pattern_upi  = re.compile(r'<a href="/en/Rupi=(\w+)">')
				match_upi    = pattern_upi.search(str(person_attr_value))
				if match_upi:
					person_attr_name_upi = match_upi.group(1)
				#Admin/Superior Name
				pattern_adminname = re.compile(r'>\s*(\w+.*)</span')
				match = pattern_adminname.search(str(person_attr_value))
				if match:
					person_attr_value = match.group(1)
				#Save
				if   "Supervisor"    in person_attr_name:
					current_upi_info["Supervisor"]        = str(person_attr_value)
					current_upi_info["SupervisorUPI"]     = str(person_attr_name_upi)
				elif "Administrator" in person_attr_name:
					current_upi_info["AdminApproval"]     = str(person_attr_value)	
					current_upi_info["AdminApprovalUPI"]  = str(person_attr_name_upi)
			#Phone|Mobile|Assistant
			elif re.search( 'Phone|Mobile|Assistant', person_attr_name, re.IGNORECASE):
				pattern = re.compile(r'telnum">(.*)</span')
				match = pattern.search(str(person_attr_value))
				if match:
					person_attr_value = match.group(1)
				person_attr_name  = person_attr_name#.strip()
				if "Phone" in person_attr_name:
					current_upi_info["OnNET"]  = str(person_attr_value)
				elif "Mobile" in person_attr_name:
					current_upi_info["Mobile"]  = str(person_attr_value)
				elif "Assistant" in person_attr_name:
					current_upi_info["Assistant"]  = str(person_attr_value)
			else:
				continue
			#print person_attr_name,"|", person_attr_value
		
		#Add SuperVisor's colleague into unchecked queue
		#<li class="tree"><a href="/en/Rupi=CV00*****">*****</a></li>
		#print soup.findAll(attrs={"class":"tree"})
		for i in soup.findAll('li',{'class':'tree'}):
			colleague_upi = i.a.attrs['href'].split('=')[1]
			if not colleague_upi in self.queue_checked:
				self.queue_uncheck.append( colleague_upi )
				print colleague_upi
		for i in soup.findAll('li',{'class':'last_tree'}):
			colleague_upi = i.a.attrs['href'].split('=')[1]
			if not colleague_upi in self.queue_checked:
				self.queue_uncheck.append( colleague_upi )
				print colleague_upi
                #self.queue_uncheck.append( current_upi_info["SupervisorUPI"] )
		return current_upi_info


	def check_save_upi( self, current_upi ):
		print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
		current_upi_statuscheck = False
		current_upi_info        = self.colleague_info
		#URL
		current_upi_url         = '%s/Rupi=%s' % (self.url_root, current_upi)  #'http://directory.app.alcatel-lucent.com/Rupi=CV00*****'
		current_upi_html_content= None
		#Check
		current_upi_html_content = self.get_html_content(current_upi_url)
		#If None, Return False; else Save to Disk
		if "No entry found" in current_upi_html_content or "Please check and relaunch your query" in current_upi_html_content:
			print "No entry found"
			current_upi_statuscheck = False
		else:
			current_upi_statuscheck = True
			#Save HTML to Disk
			html_file_on_disk = os.path.join(self.htmlpath, current_upi+'.html')
			self.save_html_content_to_disk(current_upi_html_content, html_file_on_disk)
			#Save Face Picture to Disk
			face_pic_url      = "http://faces.all.alcatel-lucent.com/l/" + current_upi
			face_pic_on_disk  = os.path.join(self.facepath, current_upi+'.jpg')
			if not os.path.exists(face_pic_on_disk):
				open( face_pic_on_disk,"wb" ).write( urllib.urlopen(face_pic_url).read() )
			#Parse HTML
			current_upi_info = self.parse_html_content(current_upi_html_content, current_upi)
			#Save into MongoDB
			self.update_mongodb(current_upi_info)
			#Add SuperVisor into Queue Unchecked
			if not current_upi_info["AdminApprovalUPI"] in self.queue_checked:
				self.queue_uncheck.append( current_upi_info["AdminApprovalUPI"] )
			if not current_upi_info["SupervisorUPI"]    in self.queue_checked:
				self.queue_uncheck.append( current_upi_info["SupervisorUPI"] )
		return current_upi_statuscheck

	def run(self):
		while( len(self.queue_uncheck) ):
			self.queue_uncheck.sort()
			#random.shuffle(self.queue_uncheck)
			current_upi     = str(self.queue_uncheck.pop())
			current_upi     = current_upi.upper()
			ALU_UPI_Pattern = re.compile('\w+')
			if not ALU_UPI_Pattern.match(current_upi):
				continue
			if current_upi in self.queue_checked:
				continue
			
			self.queue_checked.append(current_upi)
			status      = self.check_save_upi(current_upi)

			if status:
				self.queue_checked_ok.append(current_upi)
			else:
				self.queue_checked_ko.append(current_upi)
			print "[Unckecked]", len(self.queue_uncheck)
			print "[Ckecked  ]", len(self.queue_checked)
			print "[OK       ]", len(self.queue_checked_ok)
			print "[KO       ]", len(self.queue_checked_ko)


	def test_mongodb(self):
		recs = self.collect.find()
		#for item in recs:
		#	print item

		return recs.count()

		rec_finded    = self.collect.find_one({"UPI": 'CV0023830'})
		rec_finded_id = rec_finded["_id"]
		print rec_finded_id
		self.collect.update( {"_id":rec_finded_id}, rec_finded )


	def insert(self, post_data):
		print "[MongDB Operation] Insert ... ...\n"
		self.collect.insert(post_data)
		#pprint.pprint(item)
		return True

	def update_mongodb(self, current_upi_info):
		rec_finded    = self.collect.find_one({"CSL": current_upi_info["CSL"]})
		rec_finded_id = None

		if rec_finded == None:
			print "[MongDB Insert Operation]  %s ... ... \n" % current_upi_info["CSL"]
			self.collect.insert(current_upi_info)
			for item in self.collect.find({"CSL":current_upi_info["CSL"]}):
				print item
		else:
			return True
			print "[MongDB Update Operation]  %s ... ... \n" % current_upi_info["CSL"]
			rec_finded_id = rec_finded["_id"]
			self.collect.update( {"_id":rec_finded_id}, current_upi_info )


if __name__ == '__main__':
	option_parser = optparse.OptionParser()
	option_parser.add_option('-s','--startupi'           ,  dest="startupi"  , default=None, help="")
	options, args = option_parser.parse_args()

	t = X500Crawler(options.startupi)    
	#t = X500Crawler('CV00*****')
	print t.test_mongodb()
	t.run()
	sys.exit(0)

