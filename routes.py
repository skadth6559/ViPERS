
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
from . import forms

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

import status_notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#log file stuff
fileHandler = logging.FileHandler('plots.log')
fileHandler.setLevel(logging.INFO)

#consoleHandler = logging.StreamHandler()
#consoleHandler.setLevel(logging.INFO)

logger.addHandler(fileHandler)
#logger.addHandler(consoleHandler)

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
def set_active_page(route=None):
    """ Set an active page based on the route field """
    for page in SUBPAGES["PAGES"]:
        if page["route"] == route:
            page["active"] = True
        else:
            page["active"] = False

@blueprint.route('/notifications/', methods = ["GET"])
@login_required
def notifications(): 
    set_active_page(); 
    return render_template('subpages.html', SUBPAGES=SUBPAGES); 

@blueprint.route("/subscribe", methods=["GET", "POST"])            
@login_required 
def subscribe(): 
    subscribe_form = forms.EmailForm(request.form);
    text_form = forms.TextForm(request.form);
    if request.method == "POST": 
        if text_form.validate_on_submit():

            #if the BASE_DIR doesn't exist, create it.  
            if not os.path.exists(BASE_DIR): 
                try: 
                    os.mkdir(BASE_DIR); 
                except OSError as error: 
                    logger.info('Could not create base directory.');
            if request.form["btn"] == "Subscribe": 
                try: 
                    #first add the correct sms gateway domain to the end of the number.
                    email_file = os.path.join(BASE_DIR, "emails.json"); 
                    if os.path.exists(email_file):
                        #if the file exists, then we need to append to it, otherwise just create a new file. 
                        with open(email_file, 'r') as f: 
                            data = json.load(f);
                            already_subscribed = False; 
                            for i in range(len(data)):
                                if "phone" in data[i] and data[i]["phone"] == text_form.data["number"] + text_form.data['carrier']: 
                                    #if this user is already subscribed to emails. 
                                    already_subscribed = True; 
                                    flash(text_form.data["number"] + ' is already subscribed to text notifications.', 'warning'); 
                                    break; 
                            if not already_subscribed: 
                                data.append({'phone': (str(text_form.data["number"]) + text_form.data['carrier'])});
                                with open(email_file, 'w') as f: 
                                    json.dump(data, f); 
                                flash(text_form.data["number"] + ' subscribed to text notifications', 'success');
                    else: 
                        #if the email file does not exist, then create it. 
                        with open(email_file, 'w') as f:
                            data = []; 
                            data.append({'phone': text_form.data['number'] + text_form.data['carrier']});
                            json.dump(data, f); 
                            flash(subscribe_form.data["email"] + ' subscribed to e-mail notifications', 'success');
                except Exception as err:
                    logger.info('error!!!!!!!!!');
                    flash('Error! Could not subscribe to emails.', 'danger'); 
                    logger.info(err); 
                
                
            elif request.form["btn"] == "Unsubscribe": 
                try: 
                    email_file = os.path.join(BASE_DIR, "emails.json"); 
                    if os.path.exists(email_file):
                        #if the file exists, then we need to append to it, otherwise just create a new file. 
                        with open(email_file, 'r') as f: 
                            data = json.load(f); 
                            deleted = False; 
                            for i in range(len(data)) : 
                                #delete the appropriate user's email so that they no longer receive notifications. 
                                if "phone" in data[i] and data[i]['phone'] == text_form.data["number"] + text_form.data['carrier']: 
                                    del data[i]; 
                                    deleted= True; 
                                    break;
                            with open(email_file, 'w') as f: 
                                json.dump(data, f); 
                        if deleted: 
                            flash(text_form.data["number"] + ' unsubscribed from text notifications', 'success');
                        else : 
                            flash(text_form.data["number"] + ' is not subscribed to text notifications', 'warning');
                    else:   
                        flash(text_form.data["number"] + ' is not subscribed to text notifications', 'warning');
                except Exception as err:
                    logger.info('error!!!!!!!!!');
                    flash('Error! Could not unsubscribe from text notifications.', 'danger'); 
                    logger.info(err); 
                    
                    
                    
        elif subscribe_form.validate_on_submit(): 
            if request.form["btn"] == "Subscribe": 
                try: 
                    email_file = os.path.join(BASE_DIR, "emails.json"); 
                    if os.path.exists(email_file):
                        #if the file exists, then we need to append to it, otherwise just create a new file. 
                        with open(email_file, 'r') as f: 
                            data = json.load(f);
                            already_subscribed = False; 
                            for i in range(len(data)): 
                                if "email" in data[i] and data[i]["email"] == subscribe_form.data["email"]: 
                                    #if this user is already subscribed to emails. 
                                    already_subscribed = True; 
                                    flash(subscribe_form.data["email"] + ' is already subscribed to emails.', 'warning'); 
                                    break; 
                            if not already_subscribed: 
                                
                                data.append({'email': subscribe_form.data["email"]});
                                with open(email_file, 'w') as f: 
                                    json.dump(data, f); 
                                flash(subscribe_form.data["email"] + ' subscribed to e-mail notifications', 'success');
                    else:         
                        with open(email_file, 'w') as f:
                            data = []; 
                            data.append({'email': subscribe_form.data["email"]});
                            json.dump(data, f); 
                        flash(subscribe_form.data["email"] + ' subscribed to e-mail notifications', 'success');
                            
                    
                    
                except Exception as err:
                    logger.info('error!!!!!!!!!');
                    flash('Error! Could not subscribe to emails.', 'danger'); 
                    logger.info(err); 
            elif request.form["btn"] == "Unsubscribe": 
                try: 
                    email_file = os.path.join(BASE_DIR, "emails.json"); 
                    if os.path.exists(email_file):
                        #if the file exists, then we need to append to it, otherwise just create a new file. 
                        with open(email_file, 'r') as f: 
                            data = json.load(f); 
                            deleted= False; 
                            for i in range(len(data)) : 
                                #delete the appropriate user's email so that they no longer receive notifications. 
                                if data[i]['email'] == subscribe_form.data["email"]: 
                                    del data[i]; 
                                    deleted=True
                                    break;
                            with open(email_file, 'w') as f: 
                                json.dump(data, f); 
                        if deleted: 
                            flash(subscribe_form.data["email"] + ' unsubscribed from e-mail notifications', 'success');
                        else: 
                            flash(subscribe_form.data["email"] + ' is not subscribed to e-mail notifications', 'warning');
                    else:   
                        flash(subscribe_form.data["email"] + ' is not subscribed to e-mail notifications', 'warning');
                except Exception as err:
                    logger.info('error!!!!!!!!!');
                    flash('Error! Could not unsubscribe from e-mail notifications.', 'danger'); 
                    logger.info(err); 
          
        else: 
            flash('Enter a valid e-mail address.', 'danger'); 
            
        return redirect(url_for('.subscribe')); 
    if request.method == "GET": 
        set_active_page('.subscribe'); 
        return render_template("notifications/subscribe.html", SUBPAGES=SUBPAGES,
        subscribe_form=subscribe_form,
        text_form = text_form);


@blueprint.route("/daily_report", methods = ["GET", "POST"])
@login_required
def daily_report(): 
    start = time.time()
    set_active_page('.daily_report'); 
    set_btn = 0;
    #read config file
    config_object = ConfigParser()
    config_object.read("config.ini")
    #retrieve objects containing variables
    variableinfo = config_object["VARIABLEINFO"]
    buttons = config_object["BUTTONS"]
    
    date_form = forms.DailyReportForm(request.form); 
    if request.method == "POST" or variableinfo["debugging"] == "true": 
        #date field has been changed. 
        logger.info(date_form.data["date"]);
        
        if "btn" in request.form:
            if request.form["btn"] == "Select": 
                if date_form.data["date"] <= date.today(): 
                    flash('Displaying Daily Report from ' + date_form.data["date"].strftime('%m/%d/%Y'), 'success'); 
                    return redirect(url_for('.daily_report',date=date_form.data["date"]));
                else: 
                    flash('Cannot select future date', 'danger'); 
                    return redirect(url_for('.daily_report')); 
                
        #new stuff
        #add config file settings here
        #read config file
        config_object = ConfigParser()
        config_object.read("config.ini")
        #retrieve objects containing variables
        variableinfo = config_object["VARIABLEINFO"]
        buttons = config_object["BUTTONS"]
        
        #set variables
        if "btn" in request.form:
            if request.form["btn"] == "30 seconds":
                variableinfo["interval"] = "'30 seconds'";
            elif request.form["btn"] == "1 minute":
                variableinfo["interval"] = "'1 minute'";
            elif request.form["btn"] == "30 minutes":
                variableinfo["interval"] = "'30 minutes'";
            elif request.form["btn"] == "1 hour":
                variableinfo["interval"] = "'1 hour'";
            elif request.form["btn"] == "Phase":
                variableinfo["total"] = "false";
                variableinfo["variable_statistic"] = "Max";
            elif request.form["btn"] == "Total":
                variableinfo["total"] = "true";
            elif request.form["btn"] == "Power":
                variableinfo["variable_plot"] = "Power";
                variableinfo["variable_statistic"] = "Max";
            elif request.form["btn"] == "Voltage":
                variableinfo["variable_plot"] = "Voltage";
                variableinfo["variable_statistic"] = "Max";
            elif request.form["btn"] == "Voltage THD":
                variableinfo["variable_plot"] = "Voltage THD";
                variableinfo["variable_statistic"] = "Max";
            elif request.form["btn"] == "Max":
                if variableinfo["total"] == "false":
                    variableinfo["variable_statistic"] = "Max";
                else:
                    if buttons["Max"] == "true":
                        buttons["Max"] = "false";
                    else:
                        buttons["Max"] = "true";
            elif request.form["btn"] == "Min":
                if variableinfo["total"] == "false":
                    variableinfo["variable_statistic"] = "Min";
                else:
                    if buttons["Min"] == "true":
                        buttons["Min"] = "false";
                    else:
                        buttons["Min"] = "true";
            elif request.form["btn"] == "Avg":
                if variableinfo["total"] == "false":
                    variableinfo["variable_statistic"] = "Avg";
                else:
                    if buttons["Avg"] == "true":
                        buttons["Avg"] = "false";
                    else:
                        buttons["Avg"] = "true";
            else:
                print("BUTTON ANALYSIS ERROR");
            
            #write changes back to config file
            with open('config.ini', 'w') as conf:
                config_object.write(conf);
            
            #read config file
            config_object = ConfigParser();
            config_object.read("config.ini");
            #retrieve objects containing variables
            variableinfo = config_object["VARIABLEINFO"];
            buttons = config_object["BUTTONS"];
        
        
        if variableinfo["interval"] == "'30 seconds'":
            second_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='30 seconds' style='background-color:#000000;' disabled>");
            minute_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 minute'>");
            halfhr_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 minutes'>");
            hour_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 hour'>");
        elif variableinfo["interval"] == "'1 minute'":
            second_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 seconds'>");
            minute_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='1 minute' style='background-color:#000000;' disabled>");
            halfhr_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 minutes'>");
            hour_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 hour'>");
        elif variableinfo["interval"] == "'30 minutes'":
            second_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 seconds'>");
            minute_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 minute'>");
            halfhr_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='30 minutes' style='background-color:#000000;' disabled>");
            hour_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 hour'>");
        elif variableinfo["interval"] == "'1 hour'":
            second_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 seconds'>");
            minute_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 minute'>");
            halfhr_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 minutes'>");
            hour_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='1 hour' style='background-color:#000000;' disabled>");
        else:
            variableinfo["interval"] = "N/A";

        set_btn = 1;
        
        
        if variableinfo["total"] == "false":
            phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
            totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            buttons["Phase"] = "disabled";
            buttons["Set"] = "false";
            buttons["Phase"] = "disabled";
            buttons["Total"] = "enabled";
        elif variableinfo["total"] == "true":
            phasepow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Phase'>");
            totalpow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Total'  style='background-color:#000000;' disabled>");
            buttons["Total"] = "disabled";
            buttons["Phase"] = "enabled";
            buttons["Total"] = "disabled";
        
        if ("btn" in request.form and (request.form["btn"] == "Total" or request.form["btn"] == "Phase")) or variableinfo["variable_plot"] == "Power":
            if variableinfo["total"] == "false":
                #variableinfo["variable_statistic"] = "Max";
                max_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Max' disabled style='background-color:#000000;'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
                totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            else:
                #variableinfo["variable_statistic"] = "Max";
                if buttons["Set"] == "false":
                    buttons["Max"] = "true";
                    buttons["Min"] = "true";
                    buttons["Avg"] = "true";
                    buttons["Set"] = "true";
                buttons["Power"] = "disabled";
                if buttons["Voltage"] == "disabled": buttons["Voltage"] = "enabled";
                if buttons["Voltage THD"] == "disabled": buttons["Voltage THD"] = "enabled";
                max_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Max'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                voltage_btn = "";
                thd_btn = "";
            
            power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
            variableinfo["variable_plot"] = "Power";
        
        if variableinfo["variable_plot"] == "Voltage":
            if variableinfo["total"] == "false":
                #variableinfo["variable_statistic"] = "Max";
                max_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Max' disabled style='background-color:#000000;'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
                totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            else:
                #button doesn't exist here
                max_btn = "";
                min_btn = "";
                avg_btn = "";
        
            power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
            voltage_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage' disabled style='background-color:#000000;'>");
            thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
            variableinfo["variable_plot"] = "Voltage";
            buttons["Voltage"] = "disabled";
            if buttons["Power"] == "disabled": buttons["Power"] = "enabled";
            if buttons["Voltage THD"] == "disabled": buttons["Voltage THD"] = "enabled";
            
        if variableinfo["variable_plot"] == "Voltage THD":
            if variableinfo["total"] == "false":
                #variableinfo["variable_statistic"] = "Max";
                max_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Max' disabled style='background-color:#000000;'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
                totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            else:
                #button doesn't exist here
                variableinfo["variable_statistic"] = "N/A";
                max_btn = "";
                min_btn = "";
                avg_btn = "";
        
            power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
            voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
            thd_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage THD' disabled style='background-color:#000000;'>");
            variableinfo["variable_plot"] = "Voltage THD";
            buttons["Voltage THD"] = "disabled";
            if buttons["Power"] == "disabled": buttons["Power"] = "enabled";
            if buttons["Voltage THD"] == "disabled": buttons["Voltage THD"] = "enabled";
            
        #write variable plot changes back to config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)
        
        #read config file
        config_object = ConfigParser()
        config_object.read("config.ini")
        #retrieve objects containing variables
        variableinfo = config_object["VARIABLEINFO"]
        buttons = config_object["BUTTONS"]
        
        if variableinfo["variable_statistic"] == "Max":
            if variableinfo["total"] == "false":
                if variableinfo["variable_plot"] == "Power":
                    power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
                    voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                    thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                elif variableinfo["variable_plot"] == "Voltage":
                    power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
                    voltage_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage' disabled style='background-color:#000000;'>");
                    thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                elif variableinfo["variable_plot"] == "Voltage THD":
                    power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
                    voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                    thd_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage THD' disabled style='background-color:#000000;'>");
                
                max_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Max' disabled style='background-color:#000000;'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
                totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            else:
                phasepow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Phase'>");
                totalpow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Total'  style='background-color:#000000;' disabled>");
                power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
                max_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Max'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                voltage_btn = "";
                thd_btn = "";
        
        if variableinfo["variable_statistic"] == "Min":
            if variableinfo["total"] == "false":
                if variableinfo["variable_plot"] == "Power":
                    power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
                    voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                    thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                elif variableinfo["variable_plot"] == "Voltage":
                    power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
                    voltage_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage' disabled style='background-color:#000000;'>");
                    thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                elif variableinfo["variable_plot"] == "Voltage THD":
                    power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
                    voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                    thd_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage THD' disabled style='background-color:#000000;'>");
                
                max_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Max'>");
                min_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Min' disabled style='background-color:#000000;'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
                totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            else:
                phasepow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Phase'>");
                totalpow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Total'  style='background-color:#000000;' disabled>");
                power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
                max_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Max'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                voltage_btn = "";
                thd_btn = "";                    
            
        if variableinfo["variable_statistic"] == "Avg":
            if variableinfo["total"] == "false":
                if variableinfo["variable_plot"] == "Power":
                    power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
                    voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                    thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                elif variableinfo["variable_plot"] == "Voltage":
                    power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
                    voltage_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage' disabled style='background-color:#000000;'>");
                    thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");
                elif variableinfo["variable_plot"] == "Voltage THD":
                    power_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Power'>");
                    voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
                    thd_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Voltage THD' disabled style='background-color:#000000;'>");
                
                max_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Max'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Avg' disabled style='background-color:#000000;'>");
                phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
                totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            else:
                phasepow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Phase'>");
                totalpow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Total'  style='background-color:#000000;' disabled>");
                power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' disabled style='background-color:#000000;'>");
                max_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Max'>");
                min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
                avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
                voltage_btn = "";
                thd_btn = "";
        
        #write variable statistic changes back to config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)
            
        #read config file
        config_object = ConfigParser()
        config_object.read("config.ini")
        #retrieve objects containing variables
        variableinfo = config_object["VARIABLEINFO"]
        buttons = config_object["BUTTONS"]
        
        #make the get method run
        set_btn = 1

    if request.method == "GET" or set_btn == 1:    
        if request.method == "GET" and variableinfo["debugging"] == "false":
            #config file initialization
            config_object = ConfigParser();
            config_object["VARIABLEINFO"] = {
                "variable_plot" : "Power",
                "variable_statistic" : "Max",
                "interval" : "'1 hour'",
                "total" : "false",
                "debugging" : "false"
            };
            config_object["BUTTONS"] = {
                "Phase" : "disabled",
                "Total" : "enabled",
                "Power" : "disabled",
                "Voltage" : "enabled",
                "Voltage THD" : "enabled",
                "Max" : "true",
                "Min" : "true",
                "Avg" : "true",
                "Set" : "false"
            };
            with open('config.ini', 'w') as conf:
                config_object.write(conf);
                
        #read config file
        config_object = ConfigParser();
        config_object.read("config.ini");
        #retrieve objects containing variables
        variableinfo = config_object["VARIABLEINFO"];
        buttons = config_object["BUTTONS"];
    
        display_date = request.args.get('date');
        if not display_date: 
            display_date = date.today(); 
        else: 
            display_date = datetime.strptime(display_date, '%Y-%m-%d').date(); 
        
        try :
            logger.info('trying to get timezone.');
            tz = pytz.timezone(str(config['TIME_ZONE'])); 
            local_now = datetime.now(tz); 
            offset = local_now.utcoffset().total_seconds()/60/60;
            tmfmt = '%m-%d-%Y 23:59:59'; #accounting for daylight savings + timezone. 
            date_to_grab = display_date.strftime(tmfmt); 
            date_to_grab = datetime.strptime(date_to_grab, '%m-%d-%Y %H:%M:%S'); 
            date_to_grab -= timedelta(hours=offset); 
            date_to_grab = date_to_grab.strftime('%m-%d-%Y %H:%M:%S') #grab the end of the day
        except Exception as  e :
            logger.info(e); 
            logger.info('Error in timezone.  Using UTC time instead.');
            date_to_grab = display_date.strftime('%m-%d-%Y 23:59:59'); #just use utc.
        logger.info(date_to_grab);
        (split_phase, month_avg, phasea_avg, phaseb_avg, phasec_avg, a_percent, b_percent, c_percent, min_power, max_power, total_power, power_msg, min_voltage, max_voltage, min_thd, max_thd, avg_thd, avg_volt, bk_script, bk_div) = GetReportData(date_to_grab);     
        date_form.date.data = display_date; 
        if not split_phase: 
            percent_table = Markup("<th style='background:black;width:" + a_percent+ "%;'> <p style='color:white'> Phase A:\n" + a_percent + "%</p></th><th style='background:red;width:" + b_percent+ "%;'><p style='color:white'> Phase B:\n " + b_percent + "%</p></th><th style='background:blue;width:" + c_percent+ "%;'><p style='color:white'> Phase C:\n" + c_percent + "%</p></th>")
        else: 
            percent_table = Markup("<th style='background:black;width:" + a_percent+ "%;'> Phase 1:\n" + a_percent + "%</th><th style='background:red;width:" + b_percent+ "%;'> Phase 2:\n " + b_percent + "%</th>")
        
        #default button settings (change if default config settings are changed)
        if request.method == "GET" and variableinfo["debugging"] == "false":
            phasepow_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Phase' style='background-color:#000000;' disabled>");
            totalpow_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Total'>");
            power_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Power' style='background-color:#000000;' disabled>");
            voltage_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage'>");
            thd_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Voltage THD'>");        
            max_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='Max' style='background-color:#000000;' disabled>");
            min_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Min'>");
            avg_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='Avg'>");
            second_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 seconds'>");
            hour_btn = Markup("<input class='btn btn-secondary' type='submit' name = 'btn' role = 'button' value='1 hour' style='background-color:#000000;' disabled>");
            halfhr_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='30 minutes'>");
            minute_btn = Markup("<input class='btn btn-outline-dark' type='submit' name = 'btn' role = 'button' value='1 minute'>");
        
        set_btn = 0
        
        if variableinfo["total"] == "false" and not split_phase and variableinfo["variable_plot"] == "Power":
            description = "Currently Viewing Tri-Phase " + variableinfo["variable_statistic"] + " " + variableinfo["variable_plot"];
        elif variableinfo["total"] == "false" and split_phase and variableinfo["variable_plot"] == "Power":
            description = "Currently Viewing Split-Phase " + variableinfo["variable_statistic"] + " " + variableinfo["variable_plot"];
        elif variableinfo["total"] == "false":
            description = "Currently Viewing " + variableinfo["variable_statistic"] + " " + variableinfo["variable_plot"];
        else:
            substr = "";
            if buttons["Max"] == "true":
                substr = "Max";
            if buttons["Min"] == "true":
                if substr != "": substr = substr + ", ";
                substr = substr + "Min";
            if buttons["Avg"] == "true":
                if substr != "": substr = substr + ", ";
                substr = substr + "Avg";   
            
            if substr == "":
                description = "Not Displaying Data: Select Options Below";
            else:
                description = "Currently Viewing Total " + substr + " Power";
        

        end = time.time()        
        elapsed_time = 'Load time: ' + str(round(end - start, 3)) + ' seconds'
        elapsed_timerem = (end - start) - (elapsed_timeq + elapsed_timecal + elapsed_timep)
        logger.info("Remaining Operations: %s seconds", str(round(elapsed_timerem, 3)))
        logger.info("Total Load Time: %s seconds", str(round(end - start, 3)))
        
        return render_template("notifications/reports.html", 
            SUBPAGES=SUBPAGES,
            date_form = date_form,
            date = display_date.strftime("%m-%d-%Y"), 
            tri_phase=(not split_phase),
            month_avg = month_avg,
            phasea_avg = phasea_avg,
            phaseb_avg = phaseb_avg, 
            phasec_avg = phasec_avg,
            percent_table = percent_table,
            min_power = min_power,
            max_power = max_power, 
            total_power= total_power,
            power_msg = power_msg,
            min_thd = min_thd,
            max_thd = max_thd,
            power_btn = power_btn,
            phasepow_btn = phasepow_btn,
            totalpow_btn = totalpow_btn,
            voltage_btn = voltage_btn,
            thd_btn = thd_btn,
            max_btn = max_btn,
            min_btn = min_btn,
            avg_btn = avg_btn,
            second_btn = second_btn,
            minute_btn = minute_btn,
            hour_btn = hour_btn,
            halfhr_btn = halfhr_btn,
            elapsed_time = elapsed_time,
            description = description,
            min_voltage = min_voltage,
            max_voltage = max_voltage,
            avg_thd = avg_thd,
            avg_volt = avg_volt,
            bk_script = bk_script,
            bk_div = bk_div,
            ); 
            
def GetReportData(day): 
    with psycopg2.connect(CONNECTION) as conn:        
        global elapsed_timeq
        global elapsed_timecal
        global elapsed_timep
        
        #new stuff
        #read the config file
        config_object = ConfigParser()
        config_object.read("config.ini")
        variableinfo = config_object["VARIABLEINFO"]
        buttons = config_object["BUTTONS"]
        
        tz = pytz.timezone(str(config['TIME_ZONE'])); 
        cursor = conn.cursor(cursor_factory=RealDictCursor); 
        #make objects to store data from sql queries
        """phasea = {
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
        }"""
        
        (phasea, phaseb, phasec) = status_notification.create_phase_objects()
        
        #start query time
        startq = time.time()
        
        #first get monthly avg.  
        query = "SELECT avg(avg_total) as power FROM hourlypower WHERE time > TIMESTAMP '" + str(day) + "' - INTERVAL '30 days' AND time < TIMESTAMP '" + str(day) + "'; ";
        cursor.execute(query); 
        month = cursor.fetchone();
        month_avg = round(month['power'],2);
       
        
        #query phases a,b,c 
        
        #measuring how long query takes
        starta = time.time()
        
        #query = "SELECT time_bucket(" + "'4 hours'" + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM phasea WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '7 days' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"
        #query = "SELECT time_bucket(" + variableinfo["interval"] + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM phasea WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '24 hours' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"
        #cursor.execute(query);
        #len_a = 0; 
        
        (phasea, len_a) = status_notification.store_data("phasea", phasea, variableinfo["interval"], day)
        
        enda = time.time()
        elapsed_timea = enda - starta
        
        
        
        
        """for r in cursor.fetchall(): 
            #make time in local timezone.
            t = r['bucket'].replace(tzinfo=pytz.utc).astimezone(tz); 
            phasea['time'].append(t);
            phasea['avg_power'].append(r['avg_power']);
            phasea['min_power'].append(r['min_power']);
            phasea['max_power'].append(r['max_power']);
            phasea['avg_volt'].append(r['avg_volt']);
            phasea['min_volt'].append(r['min_volt']);
            phasea['max_volt'].append(r['max_volt']); 
            phasea['avg_thd'].append(r['avg_thd']);
            phasea['min_thd'].append(r['min_thd']);
            phasea['max_thd'].append(r['max_thd']); 
            len_a += 1; 
        for key, value in phasea.items(): 
            phasea[key] = [i if i is not None else 0.0 for i in value];  #replace nones with 0. 
            phasea[key] = np.asarray(phasea[key]); """
            
        
        startb = time.time()
        
        #query = "SELECT time_bucket(" + "'4 hours'" + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM phaseb WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '7 days' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"       
        #query = "SELECT time_bucket(" + variableinfo["interval"] + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM phaseb WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '24 hours' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"
        #cursor.execute(query);
        #len_b = 0; 
        
        (phaseb, len_b) = status_notification.store_data("phaseb", phaseb, variableinfo["interval"], day)
        
        endb = time.time()
        elapsed_timeb = endb - startb
        
        
        
        """for r in cursor.fetchall(): 
            t = r['bucket'].replace(tzinfo=pytz.utc).astimezone(tz); 
            phaseb['time'].append(t);
            phaseb['avg_power'].append(r['avg_power']);
            phaseb['min_power'].append(r['min_power']);
            phaseb['max_power'].append(r['max_power']);
            phaseb['avg_volt'].append(r['avg_volt']);
            phaseb['min_volt'].append(r['min_volt']);
            phaseb['max_volt'].append(r['max_volt']); 
            phaseb['avg_thd'].append(r['avg_thd']);
            phaseb['min_thd'].append(r['min_thd']);
            phaseb['max_thd'].append(r['max_thd']); 
            len_b += 1; 
         
        for key, value in phaseb.items(): 
            phaseb[key] = [i if i is not None else 0.0 for i in value];  #replace nones with 0. 
            phaseb[key] = np.asarray(phaseb[key]); """
        
        startc = time.time()
        
        #query = "SELECT time_bucket(" + "'4 hours'" + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM phasec WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '7 days' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"
        #query = "SELECT time_bucket(" + variableinfo["interval"] + ", time) as bucket, avg((power).mag) as avg_power, min((power).mag) as min_power, max((power).mag) as max_power, avg((voltage).mag) as avg_volt, avg(thd_voltage) as avg_thd, min((voltage).mag) as min_volt, max((voltage).mag) as max_volt, min(thd_voltage) as min_thd, max(thd_voltage) as max_thd FROM phasec WHERE harmonic = 1 AND time > TIMESTAMP '" + str(day) + "' - INTERVAL '24 hours' AND time < TIMESTAMP '" + str(day) + "' GROUP BY bucket ORDER BY bucket DESC;"
        #cursor.execute(query); 
        #len_c = 0
        
        (phasec, len_c) = status_notification.store_data("phasec", phasec, variableinfo["interval"], day)
        
        endc = time.time()
        elapsed_timec = endc - startc
        
        """for r in cursor.fetchall(): 
            t = r['bucket'].replace(tzinfo=pytz.utc).astimezone(tz); 
            phasec['time'].append(t);
            phasec['avg_power'].append(r['avg_power']);
            phasec['min_power'].append(r['min_power']);
            phasec['max_power'].append(r['max_power']);
            phasec['avg_volt'].append(r['avg_volt']);
            phasec['min_volt'].append(r['min_volt']);
            phasec['max_volt'].append(r['max_volt']); 
            phasec['avg_thd'].append(r['avg_thd']);
            phasec['min_thd'].append(r['min_thd']);
            phasec['max_thd'].append(r['max_thd']); 
            len_c +=1; """
        
        #end query time
        endq = time.time()
        elapsed_timeq = endq - startq
        
        
        #start calculation time
        startcal = time.time()
        
        split_phase = False; 
        #if phasec['avg_power'] is none for all, then this is split phase power and should be phase1 and 2 not a,b,c. 
        if all(x is None for x in phasec['avg_power']):
            split_phase = True; 

        for key, value in phasec.items(): 
                phasec[key] = [i if i is not None else 0.0 for i in value];  #replace nones with 0. 
                phasec[key] = np.asarray(phasec[key]); 

        (last_idx, max_power_array, min_power_array, avg_power_array, max_idx, max_power, min_idx, min_power, total_avg, total_power, power_msg, amount, total_power, phasea_avg, phaseb_avg, phasec_avg, a_percent, b_percent, c_percent) = status_notification.array_calculations(phasea, phaseb, phasec, len_a, len_b, len_c, split_phase, month_avg)
        
        """if not split_phase: 
            
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
            c_percent = "0";"""
        
        #extremes for power quality report. 
        
        #voltage
        if not split_phase: 
            if len(phasea['min_volt']) > 0 and len(phaseb['min_volt']) > 0 and len(phasec['min_volt']) > 0:
                #new stuff
                while phasea['min_volt'].size < phaseb['min_volt'].size:
                    phaseb['min_volt'] = np.delete(phaseb['min_volt'], -1);
                
                min_a_b = np.minimum(phasea['min_volt'], phaseb['min_volt']);
                
                #new stuff
                while min_a_b.size < phasec['min_volt'].size:
                    phasec['min_volt'] = np.delete(phasec['min_volt'], -1);
                    
                min_a_b_c = np.minimum(min_a_b, phasec['min_volt']); 
                
                min_volt = np.argmin(min_a_b_c); 
                min_voltage = str(round(min_a_b_c[min_volt], 2)) + " V at " + phasea['time'][min_volt].strftime("%I:%M %p");
            else : 
                min_voltage = "NO DATA";
            
            if len(phasea['max_volt']) > 0 and len(phaseb['max_volt']) > 0 and len(phasec['max_volt']) > 0: 
                #new stuff
                while phasea['max_volt'].size < phaseb['max_volt'].size:
                    phaseb['max_volt'] = np.delete(phaseb['max_volt'], -1);
                
                max_a_b = np.maximum(phasea['max_volt'], phaseb['max_volt']);
                
                #new stuff
                while max_a_b.size < phasec['max_volt'].size:
                    phasec['max_volt'] = np.delete(phasec['max_volt'], -1);
                    
                max_a_b_c = np.maximum(max_a_b, phasec['max_volt']); 
                
                max_volt = np.argmax(max_a_b_c); 
                max_voltage = str(round(max_a_b_c[max_volt], 2)) + " V at " + phasea['time'][max_volt].strftime("%I:%M %p");
            else : 
                max_voltage = "NO DATA";
            
            #thd
            if len(phasea['min_thd']) > 0 and len(phaseb['min_thd']) > 0 and len(phasec['min_thd']) > 0: 
                #new stuff
                while phasea['min_thd'].size < phaseb['min_thd'].size:
                    phaseb['min_thd'] = np.delete(phaseb['min_thd'], -1);
                
                min_a_b = np.minimum(phasea['min_thd'], phaseb['min_thd']);
                
                #new stuff
                while min_a_b.size < phasec['min_thd'].size:
                    phasec['min_thd'] = np.delete(phasec['min_thd'], -1);
                    
                min_a_b_c = np.minimum(min_a_b, phasec['min_thd']); 
                
                min_thd = np.argmin(min_a_b_c); 
                min_thd = str(round(min_a_b_c[min_thd], 3)) + "% at " + phasea['time'][min_thd].strftime("%I:%M %p");
            else : 
                min_thd = "NO DATA";
            
            if len(phasea['max_thd']) > 0 and len(phaseb['max_thd']) > 0 and len(phasec['max_thd']) > 0:
                #new stuff
                while phasea['max_thd'].size < phaseb['max_thd'].size:
                    phaseb['max_thd'] = np.delete(phaseb['max_thd'], -1);

                max_a_b = np.maximum(phasea['max_thd'], phaseb['max_thd']);
                
                #new stuff
                while max_a_b.size < phasec['max_thd'].size:
                    phasec['max_thd'] = np.delete(phasec['max_thd'], -1);
                    
                max_a_b_c = np.maximum(max_a_b, phasec['max_thd']); 
                
                max_thd = np.argmax(max_a_b_c); 
                max_thd = str(round(max_a_b_c[max_thd], 3)) + "% at " + phasea['time'][max_thd].strftime("%I:%M %p");
            else : 
                max_thd = "NO DATA";
        else : 
            if len(phasea['min_volt']) > 0 and len(phaseb['min_volt']) > 0:
                min_a_b = np.minimum(phasea['min_volt'], phaseb['min_volt']);
                
                min_volt = np.argmin(min_a_b); 
                min_voltage = str(round(min_a_b[min_volt], 2)) + " V at " + phasea['time'][min_volt].strftime("%I:%M %p");
            else : 
                min_voltage = "NO DATA";
            
            if len(phasea['max_volt']) > 0 and len(phaseb['max_volt']) > 0 : 
                max_a_b = np.maximum(phasea['max_volt'], phaseb['max_volt']);
             
                max_volt = np.argmax(max_a_b); 
                max_voltage = str(round(max_a_b[max_volt], 2)) + " V at " + phasea['time'][max_volt].strftime("%I:%M %p");
            else : 
                max_voltage = "NO DATA";
            
            #thd
            if len(phasea['min_thd']) > 0 and len(phaseb['min_thd']) > 0: 
                min_a_b = np.minimum(phasea['min_thd'], phaseb['min_thd']);
               
                min_thd = np.argmin(min_a_b); 
                min_thd = str(round(min_a_b[min_thd], 3)) + "% at " + phasea['time'][min_thd].strftime("%I:%M %p");
            else : 
                min_thd = "NO DATA";
            
            if len(phasea['max_thd']) > 0 and len(phaseb['max_thd']) > 0 and len(phasec['max_thd']) > 0:
                max_a_b = np.maximum(phasea['max_thd'], phaseb['max_thd']);
                
                max_thd = np.argmax(max_a_b); 
                max_thd = str(round(max_a_b[max_thd], 3)) + "% at " + phasea['time'][max_thd].strftime("%I:%M %p");
            else : 
                max_thd = "NO DATA";
        
        amount = round(month_avg*0.13,2)
        month_avg = str(month_avg) + " kW-hr ($" + "${:,.2f}".format(amount) + ")";
        
        #power quality stuff next. 
        if not split_phase:
            #new stuff
            while phasea['avg_thd'].size < phaseb['avg_thd'].size:
                phaseb['avg_thd'] = np.delete(phaseb['avg_thd'], -1);
            while phasea['avg_thd'].size < phasec['avg_thd'].size:
                phasec['avg_thd'] = np.delete(phasec['avg_thd'], -1);
            
            avg_thd = str(round(np.mean([phasea['avg_thd'], phaseb['avg_thd'], phasec['avg_thd']]),3)) + "%"; 
        else: 
            avg_thd = str(round(np.mean([phasea['avg_thd'], phaseb['avg_thd']]),3)) + "%"; 
        if avg_thd == "nan%" : 
            avg_thd = "NO DATA"; 
        avg_volt = str(round(np.mean(phasea['avg_volt']),2)) + " V"; 
        if avg_volt == "nan V":
            avg_volt = "NO DATA";
            
        #end calculation time
        endcal = time.time()
        elapsed_timecal = endcal - startcal
        
        #start plot time
        startp = time.time()
        
        if variableinfo["total"] == "true":
            if buttons["Max"] == "true":
                #code to fix operands error
                while phasea['max_power'].size < phaseb['max_power'].size:
                    phaseb['max_power'] = np.delete(phaseb['max_power'], -1);
                while phasea['max_power'].size < phasec['max_power'].size:
                    phasec['max_power'] = np.delete(phasec['max_power'], -1);
                while phaseb['max_power'].size < phasec['max_power'].size:
                    phasec['max_power'] = np.delete(phasec['max_power'], -1);
            
                maxpower = phasea['max_power'] + phaseb['max_power'] + phasec['max_power'];
            else:
                maxpower = np.zeros(2);
                
            if buttons["Min"] == "true":
                #code to fix operands error
                while phasea['min_power'].size < phaseb['min_power'].size:
                    phaseb['min_power'] = np.delete(phaseb['min_power'], -1);
                while phasea['min_power'].size < phasec['min_power'].size:
                    phasec['min_power'] = np.delete(phasec['min_power'], -1);
                while phaseb['min_power'].size < phasec['min_power'].size:
                    phasec['min_power'] = np.delete(phasec['min_power'], -1);
            
                minpower = phasea['min_power'] + phaseb['min_power'] + phasec['min_power'];
            else:
                minpower = np.zeros(2);
                
            if buttons["Avg"] == "true":
                #code to fix operands error
                while phasea['avg_power'].size < phaseb['avg_power'].size:
                    phaseb['avg_power'] = np.delete(phaseb['avg_power'], -1);
                while phasea['avg_power'].size < phasec['avg_power'].size:
                    phasec['avg_power'] = np.delete(phasec['avg_power'], -1);
                while phaseb['avg_power'].size < phasec['avg_power'].size:
                    phasec['avg_power'] = np.delete(phasec['avg_power'], -1);
            
                avgpower = phasea['avg_power'] + phaseb['avg_power'] + phasec['avg_power'];
            else:
                avgpower = np.zeros(2);
            
            (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Total", maxpower, minpower, avgpower
                    )
                )
        elif variableinfo["variable_plot"] == 'Power':
            
            if variableinfo["variable_statistic"] == 'Max':
                a = phasea['max_power'];
                b = phaseb['max_power'];
                c = phasec['max_power'];
            elif variableinfo["variable_statistic"] == 'Min':
                a = phasea['min_power'];
                b = phaseb['min_power'];
                c = phasec['min_power'];
            elif variableinfo["variable_statistic"] == 'Avg':
                a = phasea['avg_power'];
                b = phaseb['avg_power'];
                c = phasec['avg_power'];
                 
            if not split_phase: 
                (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Power", a, b, c
                    )
                )
            else: 
                (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Power", a, b
                    )
                )
        elif variableinfo["variable_plot"] == 'Voltage':
            
            if variableinfo["variable_statistic"] == 'Max':
                a = phasea['max_volt'];
                b = phaseb['max_volt'];
                c = phasec['max_volt'];
            elif variableinfo["variable_statistic"] == 'Min':
                a = phasea['min_volt'];
                b = phaseb['min_volt'];
                c = phasec['min_volt'];
            elif variableinfo["variable_statistic"] == 'Avg':
                a = phasea['avg_volt'];
                b = phaseb['avg_volt'];
                c = phasec['avg_volt'];
                
            if not split_phase: 
                (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Voltage", a, b, c
                    )
                )
            else: 
                (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Voltage", a, b
                    )
                )
        elif variableinfo["variable_plot"] == 'Voltage THD':
            
            if variableinfo["variable_statistic"] == 'Max':
                a = phasea['max_thd'];
                b = phaseb['max_thd'];
                c = phasec['max_thd'];
            elif variableinfo["variable_statistic"] == 'Min':
                a = phasea['min_thd'];
                b = phaseb['min_thd'];
                c = phasec['min_thd'];
            elif variableinfo["variable_statistic"] == 'Avg':
                a = phasea['avg_thd'];
                b = phaseb['avg_thd'];
                c = phasec['avg_thd'];
                
            if not split_phase: 
                (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Voltage THD", a, b, c
                    )
                )
            else: 
                (bk_script, bk_div) = components(
                    graphs.plot_daily(
                        phasea['time'], "Voltage THD", a, b
                    )
                )
        else:
            bk_script = None;
            bk_div = "";
            
        #end plot time
        endp = time.time()
        elapsed_timep = endp - startp
        
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        
        if variableinfo["Total"] == "false":
            logger.info("%s: Plotting %s %s at %s resolution", str(current_time), variableinfo["variable_statistic"], variableinfo["variable_plot"], variableinfo["interval"]);
        else:
            logger.info("%s: Plotting Total Power at %s resolution", str(current_time), variableinfo["interval"])
        
        logger.info("Total Query Execution Time: %s seconds", str(round(elapsed_timeq, 3)))
        logger.info("Query Phase A: %s seconds", str(round(elapsed_timea, 3)))
        logger.info("Query Phase B: %s seconds", str(round(elapsed_timeb, 3)))
        logger.info("Query Phase C: %s seconds", str(round(elapsed_timec, 3)))
        logger.info("Calculation Time: %s seconds", str(round(elapsed_timecal, 3)))
        logger.info("Bokeh Plotting Time: %s seconds", str(round(elapsed_timep, 3)))
        
        return (split_phase,month_avg, phasea_avg, phaseb_avg, phasec_avg, a_percent, b_percent, c_percent, min_power, max_power, total_power, power_msg, min_voltage, max_voltage, min_thd, max_thd, avg_thd, avg_volt, bk_script, bk_div); 
