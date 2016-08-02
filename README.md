# eveNotifications
A simple script polling the EVE Online API every hour to check for new notifications.

If there is a new notification an email will be send to the associated address. Otherwise an email will be send every 24h to let the user know that everything is fine.

#Usage#
* add - adds a new api key and an email address
* list - lists all registerd keys
* remove - removes a charakter's api key
* start - starts the script, first poll after an hour

#Setup#
change the email address and password in the credentials.py file  
requires pip packages:
 * evelink
 * apscheduler
