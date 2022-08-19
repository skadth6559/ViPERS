#This API is used to make interaction with the database easy.

import json
import psutil
import logging
#from memory_profiler import memory_usage
import os
import multiprocessing
import psycopg2
import shutil
from psycopg2.extras import RealDictCursor
import time
import sys
import resource
import datetime
from datetime import datetime as dt, timedelta
import dateutil.parser as parser
import csv

connection = "postgres://postgres:postgres@localhost:5432"
OLDCONNECTION = "postgres://postgres:postgres@localhost:5432"

#Pass in connection string. Connects PSQL to the connection passed in.
def set_conn(con):
    try:
        global OLDCONNECTION
        global connection
        c = psycopg2.connect(con)
        OLDCONNECTION = con
        connection = con
        if c is not None:
            c.close()
    except Exception as e:
        print('Failed to connect')
        print(e)

#Returns array of database names that are available to connect to.
def get_db():
    try:
        con = psycopg2.connect(connection)
        cur = con.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false; ")
        ret = [];
        names = cur.fetchall()
        for name in names:
            ret.append(name.get("datname"))
        if cur is not None:
            cur.close()
        if con is not None:
            con.close()
        return ret
    except Exception as e:
        print(e)

#Pass in database name, and the API will connect to it.
def set_db(name):
    global connection
    connection = OLDCONNECTION
    newCon = ""
    cur = None
    con = None
    try:
        if(isinstance(name, int)):
            newCon = get_db()[int(name) + 1]
        else:
            newCon = name
        con = psycopg2.connect(connection + "/" + newCon)
        cur = con.cursor(cursor_factory=RealDictCursor)
        connection = connection + "/" + newCon
    except Exception as e:
        print('invalid database name or number')
        print(e)
        return False;
    finally:
        if cur is not None:
            cur.close();
        if con is not None:
            con.close();

#Returns array of names of tables in selected database
def get_tables(theconnection):
    ret = []
    try:
        #tried to pass connection in as parameter
        con = psycopg2.connect(theconnection)
        #con = psycopg2.connect(connection)
        cur = con.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        names = cur.fetchall()
        for name in names:
            ret.append(name.get("table_name"))
        if cur is not None:
            cur.close()
        if con is not None:
            con.close()
        return ret
    except Exception as e:
        print(e)

#Returns array of fields of table name passed in
def get_fields(table, theconnection):
    ret = []
    p = False
    try:
        con = psycopg2.connect(theconnection)
        #con = psycopg2.connect(connection)
        cur = con.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT DATA_TYPE, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = \''+table+'\';')
        fields = cur.fetchall()
        for field in fields:
            for key, value in field.items():
                if(p == False):
                    p = True
                    pass
                else:
                    ret.append(value)
                    p = False
        #for field in fields:
        #    for key, value in field.items():
        #        if((str(value) == "integer") or (str(value) == "double precision")):
        #            p = True
        #        elif(p == True):
        #            ret.append(value)
        #            p = False
        if cur is not None:
            cur.close()
        if con is not None:
            con.close()
        return ret
    except Exception as e:
        print(e)

#Pass in a table name, field, start time, and end time. The API will write a PostgreSQL query and run it, and return the data requested. 
#Optionally pass in a Boolean value (True = Automatic resolution, False = User chooses resolution). If False is passed in, a value for reso must be passed in (resolution of data).
#Automatic resolution will sample the data with equal distribution and choose an averaging interval automatically. 50 points will be generated.
def db_retrieve(table, field, start, end, theconnection, auto = True, reso = 0):
    try:
        con = psycopg2.connect(theconnection)
        #con = psycopg2.connect(connection)
        cur = con.cursor(cursor_factory=RealDictCursor)
        ret = None
        if(auto == False):
            query = "SELECT time_bucket('" + str(reso) + ".000s',time) AS time, avg("+field+") FROM "+str(table)+" WHERE time BETWEEN '"+str(parser.parse(start).isoformat().replace('+00:00', 'Z'))+"' AND '"+str(parser.parse(end).isoformat().replace('+00:00', 'Z'))+"'GROUP BY 1 ORDER BY 1;"
            cur.execute(query)
            ret = cur.fetchall()
        else:
            #This number can be changed, depending on how many points wanted in the final graph.
            graphPoints = 50
            totalPoints = (parser.parse(end) - parser.parse(start)).total_seconds()
            interval = totalPoints/graphPoints;
            #cur.execute("DROP TYPE tester;")
            cur.execute("CREATE TYPE tester AS (" + str(field) + " double precision, time TIMESTAMP);")
            #+ '"+str((interval/2))+"s'
            cur.execute("SELECT time_bucket('"+str(interval)+"s', (((q.t)::tester).time)) AS \"time\", avg(((q.t)::tester)." + str(field) + ") AS \"" + str(field) + "\" FROM"\
            + " (SELECT (SELECT (" + str(field) + ", time)::tester AS t FROM " + str(table) + " WHERE time>=series.gen AND time<=series.gen + INTERVAL \'"+str(interval/50)+" seconds\' LIMIT 1) FROM (SELECT gen FROM generate_series(timestamp \'"+str(parser.parse(start).isoformat().replace('+00:00', 'Z'))+"\', \'"+str((parser.parse(end)).isoformat().replace('+00:00', 'Z'))+"\', INTERVAL \'"+str(interval/50)+"seconds\') gen) series) q GROUP BY 1 ORDER BY 1;")
            ret = cur.fetchall()
            
            #logger.info(*ret)
            
            cur.execute("DROP TYPE tester;")
        if cur is not None:
            cur.close()
        if con is not None:
            con.close()
        
        return ret
    except Exception as e:
        print(e)
        

