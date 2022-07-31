# NYC Subway Train Tracker Bot
[![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)](https://travis-ci.org/joemccann/dillinger)

**A Telegram bot to get you real-time information about subway arrivals, departures, and alerts in the New York City subway system.**
- Find it on Telegram as [NYC Subway Train Tracker Bot] 

## Features
- [X] Real-time train status and alerts
- [X] Information about station stops for each subway line
- [X] Provision of service and transfer information 
- [X] Possibility of adding favourite station and train direction for quick tracking

## Installation
- Clone this git repository.
```sh 
git clone https://github.com/f3d3/NYCMTA-telegram-bot
```
- Change Directory
```sh 
cd NYCMTA-telegram-bot
```
- Install requirements with pip3
```sh 
pip3 install -r requirements.txt
```

## Configuration
Add values in [config.py](./config.py).

### Configuration Values
- `BOT_TOKEN` - Get it by contacting to [BotFather](https://t.me/botfather)
- `MTA_API_key` - Get it by creating an [MTA](https://api.mta.info) developer account
- `LIST_OF_ADMINS` - List of Telegram User ID of users that can access restricted commands.

## Deploy 

### Run the bot with systemd
Create a service file, e.g. `/etc/systemd/system/bot.service`
```
[Unit]
Description=Telegram Bot Service
Requires=network.target
After=network.target
StartLimitIntervalSec=0

[Service]
ExecStart=/bin/bash -c 'cd /path-to-folder/NYCMTA-telegram-bot/ && /usr/bin/python3 /path-to-folder/NYCMTA-telegram-bot/bot.py'
Type=simple
User=<user>
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Reload the systemctl daemon. Then, enable the service so that it boots on reboot and start it
```
sudo systemctl daemon-reload
sudo systemctl enable bot.service
sudo systemctl start bot.service
```

### Run the bot in the background
Use the command below to run the script by getting it to ignore the hangup signal and keep running. Output will be put in `nohup.out`.
```sh 
nohup python3 bot.py &
```
If you do not want an ever-growing `nohup.out` file, you need to redirect the script's output as
```sh 
nohup python3 bot.py > /dev/null 2>&1 &
```



## Copyright & License
- Copyright (©) 2022 by [Federico Moretto](https://github.com/f3d3)
- Licensed under the terms of the [GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007](./LICENSE)

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [NYC Subway Train Tracker Bot]: <https://t.me/NYCSubwayTrainTrackerBot>
