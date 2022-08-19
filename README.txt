This README provides a high level overview of what each file is and explains where to insert this project's files on the MUGS unit filesystem.
Any of these locations can be editted but the source code will need to be updated accordingly to keep the user interface functioning.
Some of these files already exist at their location, but these are the updated versions that should replace the old ones.


config.ini - stores the config settings for a page so that the same page is restored if the page is refreshed
	location: /home/snickerdoodle/vipers

default.ini - stores the settings that the user currently has selected if the user clicks the save button
	location: /home/snickerdoodle/vipers

development.sh - BASH script that sets up the ViPERS development environment and eliminates the need to manually enter long commands
	location: /home/snickerdoodle/vipers

plots.log - log file that stores timing information about the UI, and informs the user about how long different parts of the code take to execute
	location: /home/snickerdoodle/vipers

apiclass.py - the file containing Shashank's PostgreSQL API that makes queries faster by sampling rather than averaging data
	location: /home/snickerdoodle/vipers

status_notification.py - stores some repeated functions between the UI's routes.py and the send_summary.py, eliminates repeated code
	location: /home/snickerdoodle/vipers

routes.py - there are two versions of this file
	1. routes_normal_version.py - contains the version of the UI that works as intended and should be used in most cases
	2. routes_psqlapi_version.py - has all of the functionality of the other version and also has options to use shashank's PSQL API to query data
	   V2 should only be used if the user specifically wants to test plotting with the API, as this version is not finished.
	
	Replace the routes.py file at the location below with the desired version, and rename this version to be the new routes.py
	location: /home/snickerdoodle/vipers/webapp/notifications

graphs.py - contains the bokeh graphing functions that are called by routes.py
	location: /home/snickerdoodle/vipers/webapp/views

reports.html - contains the html code used to setup the design of the UI webpage on ViPERS
	location: /home/snickerdoodle/vipers/webapp/notifications/templates/notifications

shashank_api_example - not necessary to upload to ViPERS, simply an example of how I used the API
	location: none

