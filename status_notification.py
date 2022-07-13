
from flask import (
    Blueprint,
    flash,
    request,
    redirect,
    url_for,
    render_template,
    Markup,
    Flask,
    jsonify
)
from flask_login import login_required

import json
import logging
import os
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import date
from datetime import datetime, timedelta
import pytz
from dotenv import dotenv_values

from configparser import ConfigParser
import time

from webapp.views import graphs

from bokeh.embed import components, server_session
from bokeh.util.session_id import generate_session_id

elapsed_timeq = 0
elapsed_timecal = 0
elapsed_timep = 0

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

fileHandler = logging.FileHandler('plots.log')
fileHandler.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)

logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)

CONNECTION = "postgres://postgres:postgres@localhost:5432/main"
blueprint = Blueprint("notifications", __name__, template_folder="templates")
PAGES = [
    {
        "title": "Notifications",
        "route": ".notifications.subscribe",
        "image": "fa-bell",
        "admin_only": False,
    }
]

SUBPAGES = {
    "SUBSECTION_TITLE" : "Notifications", 
    "SUBSECTION_ROUTE" : ".notifications",
    "PAGES" : [
        {
            "title" : "Subscribe to Notifications", 
            "route" : ".subscribe", 
            "image" : "fa-bell", 
            "help_folder": "subscribe", 
            "help_file": "subscribe",
            "active": False, 
            "admin_only": False, 
        }, 
        {
            "title" : "Daily Reports", 
            "route" : ".daily_report", 
            "image": "fas fa-newspaper", 
            "help_folder": "daily_report", 
            "help_file": "daily_report", 
            "active": False, 
            "admin_only": False, 
        },
    ],
} 


BASE_DIR = "/home/snickerdoodle/vipers/emails"
config = dotenv_values('/home/snickerdoodle/vipers/.env'); 
if 'TIME_ZONE' not in config: 
    config['TIME_ZONE'] = 'America/New_York'; 
    


def create_phase_objects():
    phasea = {
        'time': [],
        'avg_power' : [],
        'min_power' : [],
        'max_power': [],
        'avg_volt': [],
        'min_volt': [],
        'max_volt': [],
        'avg_thd': [],
        'min_thd': [],
        'max_thd': []
    }
    
    phaseb = {
        'time': [],
        'avg_power' : [],
        'min_power' : [],
        'max_power': [],
        'avg_volt': [],
        'min_volt': [],
        'max_volt': [],
        'avg_thd': [],
        'min_thd': [],
        'max_thd': []
    }
    phasec = {
        'time': [],
        'avg_power' : [],
        'min_power' : [],
        'max_power': [],
        'avg_volt': [],
        'min_volt': [],
        'max_volt': [],
        'avg_thd': [],
        'min_thd': [],
        'max_thd': []
    }
    
    return (phasea, phaseb, phasec)
    
def store_data(phase, phaseobject, resolution, day):
    with psycopg2.connect(CONNECTION) as conn:
        tz = pytz.timezone(str(config['TIME_ZONE'])); 
        cursor = conn.cursor(cursor_factory=RealDictCursor);
        
        query = "SELECT time_bucket(" + resolution + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM " + phase + " WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '24 hours' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"
        cursor.execute(query);
        
        length = 0
        
        for r in cursor.fetchall(): 
            #make time in local timezone.
            t = r['bucket'].replace(tzinfo=pytz.utc).astimezone(tz); 
            phaseobject['time'].append(t);
            phaseobject['avg_power'].append(r['avg_power']);
            phaseobject['min_power'].append(r['min_power']);
            phaseobject['max_power'].append(r['max_power']);
            phaseobject['avg_volt'].append(r['avg_volt']);
            phaseobject['min_volt'].append(r['min_volt']);
            phaseobject['max_volt'].append(r['max_volt']); 
            phaseobject['avg_thd'].append(r['avg_thd']);
            phaseobject['min_thd'].append(r['min_thd']);
            phaseobject['max_thd'].append(r['max_thd']); 
            length += 1; 
        if phase != "phasec":
            for key, value in phaseobject.items(): 
                phaseobject[key] = [i if i is not None else 0.0 for i in value];  #replace nones with 0. 
                phaseobject[key] = np.asarray(phaseobject[key]); 
            
        return (phaseobject, length)
        
def array_calculations(phasea, phaseb, phasec, len_a, len_b, len_c, split_phase, month_avg):
    if not split_phase: 
            
        last_idx = np.min([len_a, len_b, len_c]); 
        max_power_array = np.sum([phasea['max_power'][:last_idx], phaseb['max_power'][:last_idx], phasec['max_power'][:last_idx]], axis=0)
        min_power_array = np.sum([phasea['min_power'][:last_idx], phaseb['min_power'][:last_idx], phasec['min_power'][:last_idx]], axis=0)
        avg_power_array = np.sum([phasea['avg_power'][:last_idx], phaseb['avg_power'][:last_idx], phasec['avg_power'][:last_idx]], axis=0)
    else: 
        last_idx = np.min([len_a, len_b]); 
        max_power_array = np.sum([phasea['max_power'][:last_idx], phaseb['max_power'][:last_idx]], axis=0)
        min_power_array = np.sum([phasea['min_power'][:last_idx], phaseb['min_power'][:last_idx]], axis=0)
        avg_power_array = np.sum([phasea['avg_power'][:last_idx], phaseb['avg_power'][:last_idx]], axis=0)

    if(len(max_power_array) > 0) :
        max_idx = np.argmax(max_power_array);
        max_power = str(round(max_power_array[max_idx],2)) + " W at " + phasea['time'][max_idx].strftime("%I:%M %p") ;
    else : 
        max_power = "NO DATA"
    
    
    if(len(min_power_array) > 0) : 
        min_idx = np.argmin(min_power_array);
        min_power = str(round(min_power_array[min_idx],2)) + " W at " + phasea['time'][min_idx].strftime("%I:%M %p"); 
    else : 
        min_power = "NO DATA"

    logger.info('avg power array'); 

    if len(avg_power_array) > 0 : 
        
        total_avg = round(np.mean(avg_power_array),2);
        
        
        total_power = total_avg*24/1000;

        
        
        if(month_avg < 0.001): #if this is true, then our unit has likely been unplugged and we're getting a divide by 0 error in numpy.
            power_msg = Markup("<br><p> Not enough data gathered for monthly comparison calculations</p>");
            
        else : 
            #create the string for the increasing decreasing message. 

            increasing= (total_power/month_avg) > 1; 
            change = str(round((((total_power/month_avg) -1)*100),2));
            power_msg = Markup("<br><p> Your energy use <strong style = 'color:" + ("red" if (increasing) else "green") + ";'>" + ("increased" if (increasing) else "decreased ") + "</strong> by " + change + "% in comparison to your monthly average.</p>");
            
        amount = round(total_power*0.13,2); 
        total_power = str(round(total_power,2)) + " kW-hr ($" + "${:,.2f}".format(amount) + ")";
        
        phasea_avg = round(np.mean(phasea['avg_power']),2);
        phaseb_avg = round(np.mean(phaseb['avg_power']),2);
        phasec_avg = round(np.mean(phasec['avg_power']), 2); 

        a_percent = str(round((phasea_avg/total_avg)*100,2));
        b_percent = str(round((phaseb_avg/total_avg)*100,2));
        c_percent = str(round((phasec_avg/total_avg)*100,2));
        
        phasea_avg = str(phasea_avg) + " W : " + str(round(phasea_avg*24/1000,2)) + " kW-hr"; 
        phaseb_avg = str(phaseb_avg) + " W : " + str(round(phaseb_avg*24/1000,2)) + " kW-hr"; 
        phasec_avg = str(phasec_avg) + " W : " + str(round(phasec_avg*24/1000,2)) + " kW-hr"; 

    else: 
        total_power = 'NO DATA';
        power_msg = Markup("<br><p> NO DATA gathered for " + str(day)[:10] + "</p>");
        phasea_avg = "NO DATA";
        phaseb_avg = "NO DATA";
        phasec_avg = "NO DATA";
        
        a_percent = "0";
        b_percent = "0";
        c_percent = "0";
        
    return (last_idx, max_power_array, min_power_array, avg_power_array, max_idx, max_power, min_idx, min_power, total_avg, total_power, power_msg, amount, total_power, phasea_avg, phaseb_avg, phasec_avg, a_percent, b_percent, c_percent)