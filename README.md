# past-precipitation

[link](http://ericrxu.com:1080/rain)

- - - - 

Upgrade Ubuntu and packages

    sudo apt-get update

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
