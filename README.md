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
```sh 
python3 bot.py
```

## License

MIT

**Free Software, Hell Yeah!**

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [NYC Subway Train Tracker Bot]: <https://t.me/NYCSubwayTrainTrackerBot>
