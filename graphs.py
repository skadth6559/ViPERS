# -*- coding: utf-8 -*-

# #############################################################################
# This Software has been developed by ARL for US Government purposes.
# A license to  use  this  software  may  be  granted  as  needed  under
# the  terms  of  an  appropriate agreement with ARL (contract, CRADA, PLA,
# MOA, MOU, ISSA, etc.). Absent specific  terms  to  the  contrary  in  that
# agreement,  this  software  may  not  be  re-packaged,  sold  or  otherwise
# re-distributed,  or  de-compiled  or  otherwise  reverse-engineered
#
# Distribution authorized to US. Government and contractors only;
# further dissemination only as directed by ARL or higher DoD authority;
# critical technology (12 October 2017).
# Requests shall be referred to: U.S. Army Research Laboratory,
# ATTN: RDRL-SES-P, 2800 Powder Mill Rd., Adelphi, MD 20783-1197.
# US ARL information protected from public release or disclosure
# under 35 USC 205.
# #############################################################################

import datetime
import sys
import logging
import numpy as np


import psutil
from flask import url_for
from bokeh.models import (
    OpenURL,
    TapTool,
    CustomJS,
    FactorRange,
    ColumnDataSource,
    DatetimeTickFormatter,
    Button, 
    Paragraph, 
    Div
)

from bokeh.layouts import column, row, layout
from bokeh.plotting import figure
from bokeh.transform import dodge

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def human_readable_size(size, decimal_places=1):
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def get_disk_data():
    """ Return a dictionary of disk data.
    """
    disks = {
        p.mountpoint: psutil.disk_usage(p.mountpoint)
        for p in psutil.disk_partitions()
        if "/snap/" not in p.mountpoint
    }
    return disks


def convert_disk_data(disk_data):
    """ Convert psutil data into a dictionary with human readable elements.
    """
    data = dict(name=[], percent=[], free=[], total=[], used=[], color=[])
    for name, values in disk_data.items():
        data["name"].append(name)
        data["percent"].append(values.percent)
        data["used"].append(human_readable_size(values.used))
        data["total"].append(human_readable_size(values.total))
        data["free"].append(human_readable_size(values.free))
        if values.percent < 80:
            data["color"].append("green")
        else:
            data["color"].append("red")
    return data


def plot_disk():
    """ Plot disk status.
    """

    disk_data = get_disk_data()
    data = convert_disk_data(disk_data)

    source = ColumnDataSource(data=data)

    p = figure(
        plot_width=400,
        plot_height=200,
        x_range=(0, 100),
        y_range=data["name"],
        title="Disk Usage",
        tools="hover",
        tooltips="@name: used: @used total: @total free: @free",
    )

    p.hbar(y="name", right="percent", color="color", height=0.9, source=source)

    return p

def create_available_sd_files(sd_data, sd_headers, size1, size2, size=(400, 275)):
    file_types = ["Card2", "Card1"]
    TOOLTIPS = [("Time", "@labels"), ("File", "@files")]
    plot = figure(
        y_range=file_types,
        x_axis_type="datetime",
        plot_width=size[0],
        plot_height=size[1],
        tools=["tap", "xwheel_zoom", "xpan", "box_select", "box_zoom", "reset"],
        title="Click or Select to Download Data",
        sizing_mode="scale_width",
        tooltips=TOOLTIPS,
    )
    plot.xaxis.formatter = DatetimeTickFormatter(
        microseconds="%m/%d %H:%M",
        milliseconds="%m/%d %H:%M",
        seconds="%m/%d %H:%M",
        minutes="%m/%d %H:%M",
        hours="%m/%d %H:%M",
        days="%d %b %Y",
        months="%d %b %Y",
        years="%d %b %Y",
    )
    
    
    labels_d = generate_label(
        sd_data[1], sd_data[2]
    )  # create the label for the data zone.
    labels_h = generate_label(sd_headers[1], sd_headers[2])

    source_dat = ColumnDataSource(
        data=dict(
            files=sd_data[0],
            starts=[i*1000 for i in sd_data[1]],
            ends=[i*1000 for i in sd_data[2]],
            y=[file_types[0]] * len(sd_data[0]),
            labels=labels_d,
            color=sd_data[3],
        )
    )

    source_hdr = ColumnDataSource(
        data=dict(
            files=sd_headers[0],
            starts=[i*1000 for i in sd_headers[1]],
            ends=[i*1000 for i in sd_headers[2]],
            y=[file_types[1]] * len(sd_headers[0]),
            labels=labels_h,
            color=sd_headers[3],
        )
    )
    plot.quad(
        left="starts",
        right="ends",
        bottom=dodge("y", -0.35, range=plot.y_range),
        top=dodge("y", 0.35, range=plot.y_range),
        fill_color="color",
        fill_alpha=0.45,
        line_color="black",
        source=source_dat,
    )

    plot.quad(
        left="starts",
        right="ends",
        bottom=dodge("y", -0.35, range=plot.y_range),
        top=dodge("y", 0.35, range=plot.y_range),
        fill_color="color",
        fill_alpha=0.45,
        line_color="black",
        source=source_hdr,
    )
    source_dat.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(s=source_dat),
            code="""
        const inds = s.selected.indices;
        const data = s.data;
        console.log(s);
        
        download_list = []; 
        //turn the selected files blue and add them to data to be sent via post request. 
        for(var i = 0; i < inds.length; i++){
            
           
            data['color'][inds[i]] = 'green';
            
           
            download_list.push(data['files'][inds[i]]); 
        
        }


    """,
        ),
    )

    source_hdr.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(s=source_hdr),
            code="""
        const inds = s.selected.indices;
        const data = s.data;
        
       
        header_list = []; 
        //turn the selected files blue and add them to data to be sent via post request. 
        for(var i = 0; i < inds.length; i++){
            
            
            data['color'][inds[i]] = 'green';
                
            header_list.push(data['files'][inds[i]]); 
               
            
        }
        
      


    """,
        ),
    )
    button = Button(label="Download", button_type="success", sizing_mode='scale_width', align='center');
    button.js_on_click(CustomJS(code="""
        //when we actually submit, we want to empty the download form, add all the files to it, 
        //and submit.
        console.log('here');
        $("#switchSD").css({'visibility':'hidden'}); 
        $("#download_form").empty(); 
        $("#download_form").append('<input type= "hidden" name="csrf_token" value="' + csrf_token.value + '">'); 
        $("#download_form").append('<input class="btn btn-secondary" type="hidden" name="btn" role="button" value="Download Selected">'); //we just need to add this so that the post request doesn't error out. 
                       //it's looking for a btn in the form. 
        
        //make sure that all of the lists exist and iterate through them to add file names. 
        if(typeof download_list !== 'undefined'){
            for(var i =0; i < download_list.length; i++){
                $("#download_form").append('<input type="hidden" name="files[]" value ="' + download_list[i] + '">'); 
            }
        }
       
        
        if(typeof header_list !== 'undefined'){
            for(var i =0; i < header_list.length; i++){
                $("#download_form").append('<input type="hidden" name="files[]" value ="' + header_list[i] + '">'); 
            }
        }
        
     
        //error checking if download_list or header_list is empty. 
        if (jQuery.isEmptyObject(download_list)) {
            download_list = []; 
        }  
        
        if (jQuery.isEmptyObject(header_list)) {
            header_list = []; 
        }
        
        //combine lists for post request. 
        var to_download = [].concat(download_list, header_list);  
  
       
        $.ajax({
            type: 'POST', 
            url: '/raw_data/sd_download_request',
            data : {files:to_download},
            dataType: 'json', 
            success : function(data) {
                var myModal = new bootstrap.Modal(document.getElementById('downloadModal'), {
                  keyboard: false
                }); 
                
               //change test with the file names/sizes. 
                $("#modalContent").text('Downloading ' + data.num_files + ' files (' + data.file_size + '). Continue?');  
                if (data.file_size.includes("GB") && parseInt(data.file_size) >= 2) {
                    $("#modalWarning").text("Warning! Files will be concatenated before download.  Some applications may not be able to process large files.");
                    $("#modalWarning").css({ 'color' : 'red'}); 
                } else {
                    $("#modalWarning").text(""); 
                } 
                
                var warning = ""; 
                //if we try to download files from the sd card that is being written to.
                if (data.conflict[0]) {
                    warning = "Warning! Currently writing to Card 1. Download time will be greatly impacted. "; 
                } else if (data.conflict[1]){
                    warning = "Warning! Currently writing to Card 2.  Download time will be greatly impacted. ";
                } 
                
             
                $("#modalWarning2").text(warning)
                $("#modalWarning2").css({ 'color' : 'red'}); 
                
                if (data.download_time >= 120) {
                    data.download_time /= 60; 
                    data.download_time = Math.round(data.download_time); 
                    data.download_time += " minutes."; 
                } else {
                    data.download_time = Math.round(data.download_time); 
                    data.download_time += " seconds."; 
                }
                $("#downloadTime").text("Estimated Download Time: " + data.download_time ); 
                if(warning.length > 0) { //only display the switch button if we need to.
                    $("#switchSD").css({'visibility':'visible'}); 
                }
                myModal.toggle(); 
            }
        }); 
   
    """)); 
    
    #capacity_div = Div(text= "<h6 style='height:50;'> Capacity </h6> <div class='h-50 d-inline-block' style='background:#ffd358;'> <p>" + size1 + "</p> </div> <div class='h-50 d-inline-block' style='background:#a9dcd6;'><p>" + size2 + "</p></div> ", width=75, height=size[1], background='blue'); 
    title_para = Paragraph(text= "Capacity", width=75, height=50); 
    para1 = Paragraph(text=size1, width=75, height=150);    
    para2 = Paragraph(text=size2, width=75, height=150); 
    return row(column(title_para, para1, para2), column(plot, button, sizing_mode = 'scale_width')); 


def create_available_hdd_files(
    stream_data, stream_hdr, bup_data, bup_hdr, locs, size=(400, 300)
):
    print('creating plot', file=sys.stderr);
    # data comes in in the form (file_names[], starts[], ends[], colors[])
    # locs is of the form [(stream path, folder), (bup_path, folder)]
    stream_locs = locs[0]
    backup_locs = locs[1]

    # create the y-axis labels
    categories = ["Streamed Data", "Backed Up Data"]
    file_types = ["data", "header"]
    y_labels = [
        (category, file_type) for category in categories for file_type in file_types
    ]

    # tooltips show the start/end datetimes for the file.
    TOOLTIPS = [("Time", "@labels"), ("File", "@files")]

    # creating the figure3.
    plot = figure(
        y_range=FactorRange(*y_labels),
        x_axis_type="datetime",
        plot_width=size[0],
        plot_height=size[1],
        tools=["tap", "xwheel_zoom", "xpan", "box_select", "box_zoom", "reset"],
        title="Click or Select to Download Data",
        sizing_mode="scale_width",
        tooltips=TOOLTIPS,
    )

    # if there's any backed up data.
    if len(bup_data[0]) > 0:
      #  logger.info("BACKED UP DATA")
        source_bup_dat = generate_source(
            bup_data[0],
            bup_data[1],
            bup_data[2],
            generate_label(bup_data[1], bup_data[2]),
            backup_locs[0],
            backup_locs[1],
            "Backed Up Data",
            "data",
            bup_data[3],
            0
        )
        plot.quad(
            left="starts",
            right="ends",
            bottom=dodge("y", -0.5, range=plot.y_range),
            top=dodge("y", 0.4, range=plot.y_range),
            fill_alpha=0.5,
            line_color="black",
            fill_color="color",
            source=source_bup_dat,
        )

    if len(bup_hdr[0]) > 0:
       # print("BACKED UP HEADERS")
        source_bup_hdr = generate_source(
            bup_hdr[0],
            bup_hdr[1],
            bup_hdr[2],
            generate_label(bup_hdr[1], bup_hdr[2]),
            backup_locs[0],
            backup_locs[1],
            "Backed Up Data",
            "header",
            bup_hdr[3],
            1
        )

        # backed up hdr files
        plot.quad(
            left="starts",
            right="ends",
            bottom=dodge("y", -0.5, range=plot.y_range),
            top=dodge("y", 0.4, range=plot.y_range),
            fill_alpha=0.5,
            line_color="black",
            fill_color="color",
            source=source_bup_hdr,
        )

    # if there's any streamed data.
    if len(stream_data[0]) > 0:
      #  print("STREAMED DATA")
        source_stream_dat = generate_source(
            stream_data[0],
            stream_data[1],
            stream_data[2],
            generate_label(stream_data[1], stream_data[2]),
            stream_locs[0],
            stream_locs[1],
            "Streamed Data",
            "data",
            stream_data[3],
            2
        )

        # streamed dat files
        plot.quad(
            left="starts",
            right="ends",
            bottom=dodge("y", -0.5, range=plot.y_range),
            top=dodge("y", 0.4, range=plot.y_range),
            fill_alpha=0.5,
            line_color="black",
            fill_color="color",
            source=source_stream_dat,
        )
    if len(stream_hdr[0]) > 0:
      #  print("STREAMED HEADERS")
        source_stream_hdr = generate_source(
            stream_hdr[0],
            stream_hdr[1],
            stream_hdr[2],
            generate_label(stream_hdr[1], stream_hdr[2]),
            stream_locs[0],
            stream_locs[1],
            "Streamed Data",
            "header",
            stream_hdr[3],
            3
        )

        # streamed hdr files
        plot.quad(
            left="starts",
            right="ends",
            bottom=dodge("y", -0.5, range=plot.y_range),
            top=dodge("y", 0.4, range=plot.y_range),
            fill_alpha=0.5,
            line_color="black",
            fill_color="color",
            source=source_stream_hdr,
        )

    plot.xaxis.formatter = DatetimeTickFormatter(
        microseconds="%m/%d %H:%M",
        milliseconds="%m/%d %H:%M",
        seconds="%m/%d %H:%M",
        minutes="%m/%d %H:%M",
        hours="%m/%d %H:%M",
        days="%d %b %Y",
        months="%d %b %Y",
        years="%d %b %Y",
    )
   
    button = Button(label="Download", button_type="success", sizing_mode='scale_width', align='center');
    button.js_on_click(CustomJS(code="""
        //when we actually submit, we want to empty the download form, add all the files to it, 
        //and submit.
        console.log('here');
        $("#download_form").empty(); 
        $("#download_form").append('<input type= "hidden" name="csrf_token" value="' + csrf_token.value + '">'); 
        $("#download_form").append('<input class="btn btn-secondary" type="hidden" name="btn" role="button" value="Download Selected">'); //we just need to add this so that the post request doesn't error out. 
                       //it's looking for a btn in the form. 
        
        //make sure that all of the lists exist and iterate through them to add file names. 
        if(typeof bup_data_list !== 'undefined'){
            for(var i =0; i < bup_data_list.length; i++){
                $("#download_form").append('<input type="hidden" name="bup_files[]" value ="' + bup_data_list[i] + '">'); 
            }
        }
       
        
        if(typeof bup_hdr_list !== 'undefined'){
            for(var i =0; i < bup_hdr_list.length; i++){
                $("#download_form").append('<input type="hidden" name="bup_files[]" value ="' + bup_hdr_list[i] + '">'); 
            }
        }
        
        
        if(typeof streamed_data_list !== 'undefined'){
            for(var i =0; i < streamed_data_list.length; i++){
               $("#download_form").append('<input type="hidden" name="streamed_files[]" value ="' + streamed_data_list[i] + '">'); 
            }
        }
        
        
        if(typeof streamed_hdr_list !== 'undefined'){
            for(var i =0; i < streamed_hdr_list.length; i++){
                $("#download_form").append('<input type="hidden" name="streamed_files[]" value ="' + streamed_hdr_list[i] + '">'); 
            }
        }
        
        
      //error checking if download_list or header_list is empty. 
        if (jQuery.isEmptyObject(bup_data_list)) {
            bup_data_list = []; 
        }  
        
        if (jQuery.isEmptyObject(bup_hdr_list)) {
            bup_hdr_list = []; 
        }
        
        if (jQuery.isEmptyObject(streamed_hdr_list)) {
            streamed_hdr_list = []; 
        }
        
        if (jQuery.isEmptyObject(streamed_data_list)) {
            streamed_data_list = []; 
        }
        
        //combine lists for post request. 
        var to_download_bup = [].concat(bup_data_list, bup_hdr_list);  
        var to_download_streamed = [].concat(streamed_data_list, streamed_hdr_list); 
  
       
        $.ajax({
            type: 'POST', 
            url: '/raw_data/hdd_download_request',
            data : {bup_files:to_download_bup, streamed_files: to_download_streamed},
            dataType: 'json', 
            success : function(data) {
                var myModal = new bootstrap.Modal(document.getElementById('downloadModal'), {
                  keyboard: false
                }); 
                
               //change test with the file names/sizes. 
                $("#modalContent").text('Downloading ' + data.num_files + ' files (' + data.file_size + '). Continue?');  
                if (data.file_size.includes("GB") && parseInt(data.file_size) >= 2) {
                    var download_time = parseFloat(data.file_size) * (2 ** 10) / 10; 
                    //put download_time in minutes if it's long. 
                    
                    if (download_time >= 120) {
                        download_time /= 60; 
                        download_time = Math.round(download_time); 
                        download_time += " minutes."; 
                    } else {
                        download_time = Math.round(download_time); 
                        download_time += " seconds."; 
                    }
                    
                    
                    $("#modalWarning").text("Warning! Estimated ZIP file size is not available for files over 2 GB. Progess bar will be unavailable at download. Estimated download time is " + download_time);
                    $("#modalWarning").css({ 'color' : 'red'}); 
                } else {
                    $("#modalWarning").text(""); 
                } 
               myModal.toggle(); 
            }
        }); 
   
    """)); 
    return column(plot, button, sizing_mode = 'scale_width'); 

def plot_daily(time, variable, phasea, phaseb, phasec=None, size = (400,275)): 
    plot = figure(
        y_axis_type = 'linear',
        x_axis_type = "datetime",
        plot_width = size[0],
        plot_height = size[1],
        tools =["tap", "xwheel_zoom", "xpan", "box_zoom", "box_select", "reset"],
        sizing_mode= "scale_width",
    )
    
    plot.title.text_font_size = '20pt';
    plot.xaxis.axis_label_text_font_size = '14pt';
    plot.yaxis.axis_label_text_font_size = '14pt';
    plot.xaxis.major_label_text_font_size = '12pt';
    plot.yaxis.major_label_text_font_size = '12pt';
    plot.xaxis.axis_label = "Time (EST)";
    
    if variable != "Total":
        if variable == "Power":
            plot.title.text = 'Power Daily Summary';
            plot.yaxis.axis_label = "Power (V-A)";
        elif variable == "Voltage":
            plot.title.text = 'Voltage Daily Summary';
            plot.yaxis.axis_label = "Voltage (V)"; 
        elif variable == "Voltage THD":
            plot.title.text = 'Voltage THD Daily Summary';
            plot.yaxis.axis_label = "Voltage THD (%)";
            
        if phasec is not None and variable == "Power": 
            plot.multi_line([time,time,time], [phasea, phaseb, phasec], line_color=["black", "red", "blue"], line_width= 2);
        elif variable == "Power": 
            plot.multi_line([time,time], [phasea, phaseb], line_color=["black", "red"], line_width= 2);
        else:
            plot.line(time, phasea, line_color = "black", line_width = 2);
    else:
        plot.title.text = 'Total Power Daily Summary';
        plot.yaxis.axis_label = "Power (V-A)";
        
        if not np.array_equal(phasea, np.zeros(2)):
            plot.line(time, phasea, line_color = "gray", legend_label = "Max", line_width = 2);
        if not np.array_equal(phaseb, np.zeros(2)):
            plot.line(time, phaseb, line_color = "gray", legend_label = "Min", line_width = 2);
        if not np.array_equal(phasec, np.zeros(2)):    
            plot.line(time, phasec, line_color = "black", legend_label = "Avg", line_width = 2);
        plot.legend.location = "top_left";
        
    
    return plot;

def create_available_phasor_files(data, headers, size=(500, 350)):
    file_types = ["data files", "header files"]
    TOOLTIPS = [("Time", "@labels"), ("File", "@files")]
    plot = figure(
        y_range=file_types,
        x_axis_type="datetime",
        plot_width=size[0],
        plot_height=size[1],
        tools=["tap", "xwheel_zoom", "xpan", "box_zoom", "box_select", "reset"],
        title="Click or Select to Download Data",
        sizing_mode="scale_width",
        tooltips=TOOLTIPS,
    )

    plot.xaxis.formatter = DatetimeTickFormatter(
        microseconds="%m/%d %H:%M",
        milliseconds="%m/%d %H:%M",
        seconds="%m/%d %H:%M",
        minutes="%m/%d %H:%M",
        hours="%m/%d %H:%M",
        days="%d %b %Y",
        months="%d %b %Y",
        years="%d %b %Y",
    )
    labels_d = generate_label(
        data[1], data[2]
    )  # create the label for the data zone.
    labels_h = generate_label(headers[1], headers[2])

    source_dat = ColumnDataSource(
        data=dict(
            files=data[0],
            starts= [i * 1000 for i in data[1]],
            ends= [i*1000 for i in data[2]],
            y=["data files"] * len(data[0]),
            labels=labels_d,
            color=data[3],
        )
    )

    source_hdr = ColumnDataSource(
        data=dict(
            files=headers[0],
            starts=[i*1000 for i in headers[1]],
            ends=[i*1000 for i in headers[2]],
            y=["header files"] * len(headers[0]),
            labels=labels_h,
            color=headers[3],
        )
    )

    plot.quad(
        left="starts",
        right="ends",
        bottom=dodge("y", -0.35, range=plot.y_range),
        top=dodge("y", 0.35, range=plot.y_range),
        fill_color="color",
        fill_alpha=0.45,
        line_color="black",
        source=source_dat,
    )

    plot.quad(
        left="starts",
        right="ends",
        bottom=dodge("y", -0.35, range=plot.y_range),
        top=dodge("y", 0.35, range=plot.y_range),
        fill_color="color",
        fill_alpha=0.45,
        line_color="black",
        source=source_hdr,
    )

    source_dat.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(s=source_dat),
            code="""
        const inds = s.selected.indices;
        const data = s.data;
        
        download_list = []; 
        
        //turn the selected files blue and add them to data to be sent via post request. 
        for(var i = 0; i < inds.length; i++){
            

            data['color'][inds[i]] = 'green';
            
           
           download_list.push(data['files'][inds[i]]); 
            
        }
        

    """,
        ),
        
    
    )

    source_hdr.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(s=source_hdr),
            code="""
        const inds = s.selected.indices;
        const data = s.data;
        
       
        header_list = []; 
        //turn the selected files blue and add them to data to be sent via post request. 
        for(var i = 0; i < inds.length; i++){
            

            data['color'][inds[i]] = 'green';
            
            header_list.push(data['files'][inds[i]]); 
           
  
        }
        
        
    """,
        ),
    )
    
    button = Button(label="Download", button_type="success", sizing_mode='scale_width', align='center');
    button.js_on_click(CustomJS(code="""
        //when we actually submit, we want to empty the download form, add all the files to it, 
        //and submit.
        $("#download_form").empty(); 
        $("#download_form").append('<input type= "hidden" name="csrf_token" value="' + csrf_token.value + '">'); 
        $("#download_form").append('<input class="btn btn-secondary" type="hidden" name="btn" role="button" value="Download Selected">'); //we just need to add this so that the post request doesn't error out. 
                       //it's looking for a btn in the form. 
        
        //have to check that these lists have been defined. 
        if(typeof download_list !== 'undefined'){
            for(var i =0; i < download_list.length; i++){
                $("#download_form").append('<input type="hidden" name="files[]" value ="' + download_list[i] + '">'); 
            }
        }
        

        if(typeof header_list !== 'undefined'){ 
            for(var i =0; i < header_list.length; i++){
               $("#download_form").append('<input type="hidden" name="files[]" value ="' + header_list[i] + '">'); 
            }
        } 
        
        //error checking if download_list or header_list is empty. 
        if (jQuery.isEmptyObject(download_list)) {
            download_list = []; 
        }  
        
        if (jQuery.isEmptyObject(header_list)) {
            header_list = []; 
        }
        
        //combine lists for post request. 
        var to_download = [].concat(download_list, header_list);  
  
       
        $.ajax({
            type: 'POST', 
            url: '/file_download/download_request',
            data : {files:to_download},
            dataType: 'json', 
            success : function(data) {
                var myModal = new bootstrap.Modal(document.getElementById('downloadModal'), {
                  keyboard: false
                }); 
                
               //change test with the file names/sizes. 
                $("#modalContent").text('Downloading ' + data.num_files + ' files (' + data.file_size + '). Continue?');  
                if (data.file_size.includes("GB") && parseInt(data.file_size) >= 2) {
                    var download_time = parseFloat(data.file_size) * (2 ** 10) / 10; 
                    //put download_time in minutes if it's long. 
                    
                    if (download_time >= 120) {
                        download_time /= 60; 
                        download_time = Math.round(download_time); 
                        download_time += " minutes."; 
                    } else {
                        download_time = Math.round(download_time); 
                        download_time += " seconds."; 
                    }
                    
                    
                    $("#modalWarning").text("Warning! Estimated ZIP file size is not available for files over 2 GB. Progess bar will be unavailable at download. Estimated download time is " + download_time);
                    $("#modalWarning").css({ 'color' : 'red'}); 
                } else {
                    $("#modalWarning").text(""); 
                } 
               myModal.toggle(); 
            }
        }); 

    
        
   
   """)); 
   
    delete_button = Button(label="Delete", button_type="danger", sizing_mode='scale_width', align='center');
    delete_button.js_on_click(CustomJS(code="""
        //when we actually submit, we want to empty the download form, add all the files to it, 
        //and submit.
        $("#delete_form").empty(); 
        $("#delete_form").append('<input type= "hidden" name="csrf_token" value="' + csrf_token.value + '">'); 
        $("#delete_form").append('<input class="btn btn-secondary" type="hidden" name="btn" role="button" value="Delete Selected">'); //we just need to add this so that the post request doesn't error out. 
                       //it's looking for a btn in the form. 
        
        //have to check that these lists have been defined. 
        if(typeof download_list !== 'undefined'){
            for(var i =0; i < download_list.length; i++){
                $("#delete_form").append('<input type="hidden" name="files[]" value ="' + download_list[i] + '">'); 
            }
        }
        

        if(typeof header_list !== 'undefined'){ 
            for(var i =0; i < header_list.length; i++){
               $("#delete_form").append('<input type="hidden" name="files[]" value ="' + header_list[i] + '">'); 
            }
        } 
        
                if(typeof header_list !== 'undefined'){ 
            for(var i =0; i < header_list.length; i++){
               $("#download_form").append('<input type="hidden" name="files[]" value ="' + header_list[i] + '">'); 
            }
        } 
        
        //error checking if download_list or header_list is empty. 
        if (jQuery.isEmptyObject(download_list)) {
            download_list = []; 
        }  
        
        if (jQuery.isEmptyObject(header_list)) {
            header_list = []; 
        }
        
        //combine lists for post request. 
        var to_delete = [].concat(download_list, header_list);  
  
       
        $.ajax({
            type: 'POST', 
            url: '/file_download/download_request',
            data : {files:to_delete},
            dataType: 'json', 
            success : function(data) {
                var myModal = new bootstrap.Modal(document.getElementById('deleteModal'), {
                  keyboard: false
                }); 
                
               //change test with the file names/sizes. 
               $("#DeleteMsg").text('Deleting ' + data.num_files + ' files (' + data.file_size + '). Continue?'); 
               myModal.toggle(); 
            }
        }); 
        
   
   """)); 
    return column(plot, button, delete_button, sizing_mode = 'scale_width'); 
def generate_source(
    files, starts, ends, labels, path, folder, category, file_type, colors, file_list
):
    """Returns a column data source corresponding to the input parameters"""
    source = ColumnDataSource(
        data=dict(
            y=[(category, file_type)] * len(files),
            files=files,
            starts=[i*1000 for i in starts],
            ends=[i*1000 for i in ends],
            labels=labels,
            path=[path] * len(files),
            folder=[folder] * len(files),
            color=colors,
        )
    )
    
    # file_list is an int to decide between 
    # which of the following lists this should go to. 
    #   bup_data_list 0
	#	bup_hdr_list  1
	#	streamed_data_list 2
	#	streamed_hdr_list 3
    source.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(s=source, l=file_list),
            code="""
        console.log(s);
        const inds = s.selected.indices;
        const data = s.data;
        
        
        switch(l) {
            case 0 : 
                bup_data_list = []; 
                //turn the selected files blue and add them to data to be sent via post request. 
                for(var i = 0; i < inds.length; i++){
                    
               
                        
                    data['color'][inds[i]] = 'green';
                    
                    bup_data_list.push(data['files'][inds[i]]); 
                       
                    
                }
        
                break;
            case 1 : 
                bup_hdr_list = []; 
                //turn the selected files blue and add them to data to be sent via post request. 
                for(var i = 0; i < inds.length; i++){
                    
                    
                    
                    data['color'][inds[i]] = 'green';
                    
                    bup_hdr_list.push(data['files'][inds[i]]); 
                   
                
                }
                break;
            case 2 : 
                streamed_data_list = []; 
                //turn the selected files blue and add them to data to be sent via post request. 
                for(var i = 0; i < inds.length; i++){
                    
                   
                        
                    data['color'][inds[i]] = 'green';
                    
                    streamed_data_list.push(data['files'][inds[i]]); 
                   
                    
                }
                break;
            case 3 : 
                streamed_hdr_list = []; 
                //turn the selected files blue and add them to data to be sent via post request. 
                for(var i = 0; i < inds.length; i++){
                    
                    
                        
                    data['color'][inds[i]] = 'green';
                    
                    streamed_hdr_list.push(data['files'][inds[i]]); 
                   
                    
                }
                break; 
        }
    

    """,
        ),
    )

    return source


def generate_label(starts, ends):
    """generate the start and end labels for the tooltips for backed up data.
    takes the time stamp and puts it in a datetime format. """
    labels = []
    for i in range(0, len(starts)):

        start = datetime.datetime.fromtimestamp(starts[i])  # starts and ends are in ms since epoch.
        start = start.strftime("%b %-d %Y, %H:%M:%S")
        end = datetime.datetime.fromtimestamp(ends[i])
        end = end.strftime("%b %-d %Y, %H:%M:%S")

        labels.append(start + "-" + end)

    return labels
