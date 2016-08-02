# EVE Online Notifications
A simple script polling the EVE Online API every hour to check for new notifications.

If there is a new notification an email will be send to the associated address. Otherwise an email will be send every 24h to let the user know that everything is fine.

#Usage#
* add - adds a new api key and an email address
* list - lists all registerd keys
* remove - removes a charakter's api key
* test - sends a mail to a specified address to test the setup
* start - starts the script, first poll after an hour

#Setup#
requires pip packages:
 * [evelink](https://pypi.python.org/pypi/EVELink)
 * [apscheduler](https://pypi.python.org/pypi/APScheduler)

1. customize credentials.py
2. the <b>test</b> command verifies the settings
3. use the <b>add</b> command to add a character
4. <b>start</b> command runs the service
