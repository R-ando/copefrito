import psycopg2
import sys


def main():
	conn_string = "host='localhost' dbname='dirtest' user='postgres' password=''"
	# print the connection string we will use to connect
	print "Connecting to database\n	->%s" % (conn_string)

	# get a connection, if a connect cannot be made an exception will be raised here
	conn = psycopg2.connect(conn_string)