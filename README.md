# past-precipitation 🌧️🌧️🌧️🌧️🌧️

[UI](https://app.ericrxu.com/rain)


**Past Precipitation** is a pet project designed to help users find historical rainfall data for populous cities, with a particular focus on California. 🌧️ Finding free and reliable historical precipitation data can be challenging, and this tool aims to fill that gap.

## Origin
The project began out of a personal need to determine when Bedwell Bayfront Park would be muddy after rainfall. With my notoriously poor memory and a surprising realization of how much rain the bay area receives (I moved here in 2020), I wanted to avoid getting my running shoes stuck in the mud during my jobs at the park.

## Features
- **Historical Rainfall Data**: Access historical precipitation data (historical data starting from April 30, 2023)
- **User-Friendly Web Form**: Input your location to get detailed historical rainfall statistics.
- **Technology Stack**: Hosted on DigitalOcean cloud VCPU servers using Flask and MySQL.


---


## Installation

Upgrade Ubuntu and packages

    sudo apt-get update
    sudo apt-get upgrade

Install mySQL ([Ubuntu 22.04 instructions here](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-22-04))

Install git, go to home directory, and clone this repo

    sudo apt-get install git
    cd ~/
    git clone https://github.com/eric-r-xu/past-precipitation.git
    
Install latest python and all packages and activate virtual environment
    
    cd past-precipitation
    sh prepare_env.sh

Run flask web application in background (logs in /logs/rain_service.log including standard error)

    nohup /$(whoami)/past-precipitation/env/bin/python /$(whoami)/past-precipitation/rain_service.py 2>&1 &
    
Schedule cron for scripted api call to get latest precipitation data (

    export VISUAL=nano;crontab -e
    
    add following row entry to schedule runs every 30 minutes (logs in /logs/rain_api.log including standard error)
    
    0,30 * * * * /$(whoami)/past-precipitation/env/bin/python /$(whoami)/past-precipitation/rain_api.py 2>&1


Example Data Backfill Command for Past Precipitation Data for Bedwell Bayfront Park for between 1742281200 and 1742367600

     /$(whoami)/myproject/myprojectenv/bin/python /$(whoami)/past-precipitation/rain_api.py -s 1742281200 -l "Bedwell Bayfront Park" -e 1742367600
