# jesta's fork of [clayop/steemfeed](https://github.com/clayop/steemfeed)

This is a modified version of clayop's steemfeed used to `publish_feed` for accounts witnessing on the steem blockchain.

## Major Changes:

- No longer uses a local cli_wallet / httprpc connection, now uses [xeroc/piston](https://github.com/xeroc/piston) to create, sign and broadcast the `publish_feed` transaction.
- Dockerized the entire application. If you don't want to use docker, you could still export the variables from the `.example.env` file and run `python3 steemfeed.py` to start the application.

## Docker Configuration

1. Have Docker installed. Running `docker info` should return the information about your instance. If you need help installing, [see docker's installation guide](https://docs.docker.com/engine/installation/).
2. `cp .example.env .env`, then edit it to add your account name, active WIF key, and your preferred node.
3. `docker-compose up` to bring the node online. Ctrl+C to kill the process.

**To run in the background**, run `docker-compose up -d`. If you are running in the background, you can also tail the logs with `docker logs -f steemfeed_app_1`.

**If you modify steemfeed.py**, you will need to rebuild and rerun using the following command:

`docker-compose build && docker-compose up`

This will rebuild the container and then start it again.

# Original readme.md (from [clayop/steemfeed](https://github.com/clayop/steemfeed))

### Supported Exchanges
* Bittrex
* Openledger (BTS-STEEM, Open.BTC-STEEM)
* Poloniex (Not listed yet)


### Preparation
To use this price feed script, the following dependencies and packages should be installed.

    sudo apt-get install libffi-dev libssl-dev python3-dev python3-pip
    sudo pip3 install python-dateutil
    sudo pip3 install websocket-client
    sudo pip3 install steem

(if you got an error during installing steem, run ``sudo pip3 install upgrade pip``)

In addition, you should run cli_wallet by using the following command,

    cli_wallet -s ws://localhost:8090 -H 127.0.0.1:8092 --rpc-http-allowip=127.0.0.1

And unlock your cli_wallet.


### Installation
Copy the code in [this link](https://github.com/clayop/steemfeed/blob/master/steemfeed.py) and paste as `steemfeed.py` in your witness server.


### Configuration
Then, edit the `steemfeed.py` to configure. We have some items under Config category in the code.

* `interval`: Interval of publishing price feed. The default value is one hour (3600 seconds)
* `freq`: Frequency of parsing trade history. Please be noticed that it can parse only 200 last trading history (Bittrex), so as trading is active you may need to decrease this frequency value.
* `min_change`: Minimum price change percentage to publish feed
* `max_age`: Maximum age of price feed
* `manual_conf`: Maximum price change without manual confirmation. If price change exceeds this, you will be asked to confirm
* `use_telegram`: If you want to use Telegram for confirmation, enter 1
* `telegram_token`: Create your Telegram bot at @BotFather (https://telegram.me/botfather)
* `telegram_id`: Get your telegram id at @MyTelegramID_bot (https://telegram.me/mytelegramid_bot)
* `bts_ws` : List of BitShares Websocket servers
* `rpc_host`: Your RPC host address
* `rpc_port`: Your RPC host port
* `witness`: Enter ***YOUR WITNESS ID*** here
 

### Run
Then, run this code in a separate screen

    screen -S steemfeed
    python3 ./steemfeed.py
