#! /usr/bin/python
#
#
#  Copyright (C) Lafayette College. All rights reserved.
#
#  This code may be used under the GPLv2 license.
#  https://github.com/tjsail33/webformpymigrate/blob/master/LICENSE
#
#  Written by Tim Costa
#
#

import MySQLdb
import getpass
import collections
import json
import sys

if len(sys.argv)>2 and sys.argv[2]=="--debug":
	debug = True
	print "------------------------DEBUG MODE ON--------------------------"
else:
	debug = False


def convert(input):
    if isinstance(input, dict):
        return {convert(key): convert(value) for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [convert(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def checkTableExists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = '{0}'
        """.format(tablename.replace('\'', '\'\'')))
    if dbcur.fetchone()[0] == 1:
        dbcur.close()
        return True

    dbcur.close()
    return False

if len(sys.argv) < 2:
	exit("Must supply at least one argument (e,i)")

if sys.argv[1] == '-e':

	print "Welcome to the Webform Export script written by Tim Costa"
	print "Let's get started. Please provide the following information:"

	host = raw_input("Database Server: ")
	username = raw_input("Username: ")
	password = getpass.getpass()
	databaseName = raw_input("Database Name: ")
	databasePrefix = raw_input("Database Prefix (Leave blank for none): ")

	print "Thanks for that information. Let me make sure I can connect to your database..."

	try:
		db = MySQLdb.connect(host=host,user=username,passwd=password,db=databaseName)
	except Exception,e:
		print "Something went wrong..."
		print e
		exit(0)

	print "The connection to "+databaseName+"@"+host+" was successful!"

	cur = db.cursor()

	exportData = collections.OrderedDict()

	# get all tables from database
	if checkTableExists(db,"webform"):
		sql = "SELECT * FROM node WHERE type='webform';"
		print "Fetching the list of webforms..."
		cur.execute(sql)
		count = 1
		for row in cur.fetchall():
			print "{}: {}".format(row[0],row[4])
			count = count + 1
		formToExport = raw_input("Select a form to export: ")

		sql = "SELECT * FROM "+databasePrefix+"node WHERE nid="+formToExport
		cur.execute(sql)
		exportData['node'] = cur.fetchall()
		formName = exportData['node'][0][4]

		sql = "SELECT * FROM "+databasePrefix+"field_data_body WHERE entity_id="+formToExport
		cur.execute(sql)
		exportData['field_data_body'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"field_revision_body WHERE entity_id="+formToExport
		cur.execute(sql)
		exportData['field_revision_body'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"variable WHERE name=\'webform_addmore_"+formToExport+"\'"
		cur.execute(sql)
		exportData['variable'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"node_comment_statistics WHERE nid="+formToExport
		cur.execute(sql)
		exportData['node_comment_statistics'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"node_revision WHERE nid="+formToExport
		cur.execute(sql)
		exportData['node_revision'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"webform WHERE nid="+formToExport
		cur.execute(sql)
		exportData['webform'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"webform_component WHERE nid="+formToExport
		cur.execute(sql)
		exportData['webform_component'] = cur.fetchall()

		sql = "SELECT * FROM "+databasePrefix+"webform_roles WHERE nid="+formToExport
		cur.execute(sql)
		exportData['webform_roles'] = cur.fetchall()

		if checkTableExists(db,databasePrefix+"webform_validation_rule"):

			sql = "SELECT * FROM "+databasePrefix+"webform_validation_rule WHERE nid="+formToExport
			cur.execute(sql)
			data = cur.fetchall()
			exportData['webform_validation_rule'] = data

			rule_components = []
			for row in data:
				sql = "{}{}".format( "SELECT * FROM "+databasePrefix+"webform_validation_rule_components WHERE ruleid=",row[0])
				cur.execute(sql)
				for rowi in cur.fetchall():
					rule_components.append([rowi[0],rowi[1]])

			exportData['webform_validation_rule_components'] = rule_components
		else:
			print "No Webform Validations module detected. Saving your form without any validations from Webform Validations."
		
		with open(formName.replace(" ","_")+".json", 'w') as outfile:
			json.dump(exportData, outfile, indent=4)
			print "Webform saved to "+formName.replace(" ","_")+".json"
	else:
		print "Webform Table not detected in your database. This script has no purpose if there is no webform table."
	

elif sys.argv[1] == '-i':
	# For insert, use 0 or NULL as the nid for the `node` insert. Then fetch based on name and catch the nid given.

	print "Welcome to the Webform Import script written by Tim Costa"
	print "Let's get started. Please provide the following information:"

	host = raw_input("Database Server: ")
	username = raw_input("Username: ")
	password = getpass.getpass()
	databaseName = raw_input("Database Name: ")
	databasePrefix = raw_input("Database Prefix (Leave blank for none): ")
	webformPath = raw_input("Path to Webform JSON: ")

	print "Thanks for that information. Let me make sure I can connect to your database and read that file..."

	try:
		db = MySQLdb.connect(host=host,user=username,passwd=password,db=databaseName)
		print "The connection to "+databaseName+"@"+host+" was successful!"
		with open(webformPath) as data_file:    
			webformJSON = json.load(data_file)
			webformJSON = convert(webformJSON)
		if not checkTableExists(db,databasePrefix+"webform"):
			exit("Webform table not found in database. Please make sure you have the Webform module installed and the right database settings, and try again.")

	except Exception,e:
		print "Something went wrong..."
		print e
		exit(0)

	cur = db.cursor()

	node = tuple(webformJSON['node'][0])
	node = "(NULL,NULL,"+str(node[2:])[1:]
	cur.execute("INSERT INTO node VALUES "+str(node))
	nid = int(db.insert_id())
	webformJSON['field_data_body'][0][3] = nid
	webformJSON['field_revision_body'][0][3] = nid
	webformJSON['node_comment_statistics'][0][0] = nid
	webformJSON['node_revision'][0][0] = nid
	webformJSON['webform'][0][0] = nid
	webformJSON['webform'][0][2] = "NULL"
	for component in webformJSON['webform_component']:
		component[0] = nid
	for role in webformJSON['webform_roles']:
		role[0] = nid
	if webformJSON['webform_validation_rule'] and checkTableExists(db,"webform_validation_rule"):
		for validation in webformJSON['webform_validation_rule']:
			validation[2] = nid

	fieldDataBody = tuple(webformJSON['field_data_body'][0])
	sql = "INSERT INTO "+databasePrefix+"field_data_body VALUES "+str(fieldDataBody)
	if debug:
		print sql
	cur.execute(sql)

	fieldRevisionBody = tuple(webformJSON['field_revision_body'][0])
	sql = "INSERT INTO "+databasePrefix+"field_revision_body VALUES "+str(fieldRevisionBody)
	if debug:
		print sql
	cur.execute(sql)

	nodeCommentStatistics = tuple(webformJSON['node_comment_statistics'][0])
	nodeCommentStatistics = "("+str(nodeCommentStatistics[0:3])[1:-1]+",NULL,"+str(nodeCommentStatistics[4:])[1:]
	sql = "INSERT INTO "+databasePrefix+"node_comment_statistics VALUES "+str(nodeCommentStatistics)
	if debug:
		print sql
	cur.execute(sql)

	nodeRevision = tuple(webformJSON['node_revision'][0])
	nodeRevision = "("+str(nodeRevision[0:1])[1:-1]+"0,"+str(nodeRevision[2:4])[1:-1]+",'',"+str(nodeRevision[5:])[1:]
	sql = "INSERT INTO "+databasePrefix+"node_revision VALUES "+str(nodeRevision)
	if debug:
		print sql
	cur.execute(sql)
	cur.execute("UPDATE "+databasePrefix+"node SET vid={} WHERE nid={}".format(db.insert_id(),nid))

	webform = tuple(webformJSON['webform'][0])
	sql = "INSERT INTO "+databasePrefix+"webform VALUES "+str(webform)
	if debug:
		print sql
	cur.execute(sql)

	webformComponent = ""
	for component in webformJSON['webform_component']:
		if component[3]=="ticket_queue":
			print "Integration with RT detected..."
			component[6] = raw_input("Please enter the name of the RT queue you would \nlike this form to feed into: ")
		webformComponent = webformComponent + str(tuple(component))+","
	webformComponent = webformComponent[0:-1]
	sql = "INSERT INTO "+databasePrefix+"webform_component VALUES "+str(webformComponent)
	if debug:
		print sql
	cur.execute(sql)

	if len(webformJSON['variable']) > 0:
		sql = "INSERT INTO "+databasePrefix+"variable VALUES (\'webform_addmore_"+str(nid)+"\',\'"+webformJSON['variable'][0][1]+"\')"
		if debug:
			print sql
		cur.execute(sql)

	webformRoles = ""
	for role in webformJSON['webform_roles']:
		webformRoles = webformRoles + str(tuple(role))+","
	webformRoles = webformRoles[0:-1]
	sql = "INSERT INTO "+databasePrefix+"webform_roles VALUES "+str(webformRoles)
	if debug:
		print sql
	cur.execute(sql)

	if len(webformJSON['webform_validation_rule']) > 0 and checkTableExists(db,"webform_validation_rule"):

		newRuleIds = {}
		for validation in webformJSON['webform_validation_rule']:
			validation = tuple(validation)
			sql = "INSERT INTO "+databasePrefix+"webform_validation_rule VALUES (" + "NULL,"+str(validation[1:5])[1:-1]+",NULL,"+str(validation[6:])[1:-2]+")"
			if debug:
				print sql
			cur.execute( sql)
			newRuleIds[validation[0]] = int(db.insert_id())

		webformValidationComponent = ""
		for validationComp in webformJSON['webform_validation_rule_components']:
			webformValidationComponent = webformValidationComponent + "({},{}),".format(newRuleIds[validationComp[0]],validationComp[1])
		webformValidationComponent = webformValidationComponent[0:-1]
		sql = "INSERT INTO "+databasePrefix+"webform_validation_rule_components VALUES "+str(webformValidationComponent)
		if debug:
			print sql
		cur.execute(sql)

	cur.close()

	db.commit()

	print "Well, I think its done."

	exit(0)

else:
	print "Valid arguments are -e to export a webform and -i to import a webform."
	exit(0)


