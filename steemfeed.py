from __future__ import print_function
import time, datetime
import dateutil.parser
import requests
import random
import json
import websocket
import sys
from websocket import create_connection

from pprint import pprint

from graphenebase.types import *
from graphenebase.objects import GrapheneObject, isArgsThisClass
from steembase.operations import Amount
from piston.steem import Steem
import os

# Config

interval_init  = 60*60*float(os.environ['feed_interval_init'])
rand_level     = float(os.environ['feed_rand_level'])
freq           = int(os.environ['feed_freq'])
min_change     = float(os.environ['feed_min_change'])
max_age        = 60*60*int(os.environ['feed_max_age'])
manual_conf    = float(os.environ['feed_manual_conf'])
discount       = float(os.environ['feed_discount'])
use_telegram   = os.environ['feed_use_telegram']
telegram_token = os.environ['feed_telegram_token']
telegram_id    = os.environ['feed_telegram_id']
bts_ws         = ["wss://dele-puppy.com/ws", "wss://bitshares.openledger.info/ws", "wss://valen-tin.fr:8090/ws"]

# Piston/Account Configuration
steemnode      = os.environ['feed_node'] # The steemnode to connect to
witness        = os.environ['feed_account']   # Your witness name
wif            = os.environ['feed_wif']       # Your active WIF key

# New Classes, should be migrated to xeroc's library
class Exchange_rate(GrapheneObject):
    def __init__(self, *args, **kwargs) :
        if isArgsThisClass(self, args):
                self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]

            super().__init__(OrderedDict([
                ('base', Amount(kwargs["base"])),
                ('quote', Amount(kwargs["quote"])),
            ]))

class Feed_publish(GrapheneObject) :
    def __init__(self, *args, **kwargs) :
        if isArgsThisClass(self, args):
                self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(OrderedDict([
                ('publisher', String(kwargs["publisher"])),
                ('exchange_rate', Exchange_rate(kwargs["exchange_rate"])),
            ]))

def publish_feed(account, amount):
    op = Feed_publish(
        **{ "publisher": account,
            "exchange_rate": {
              "base": amount + " SBD",
              "quote": "1.000 STEEM"
            }}
    )
    steem.executeOp(op, wif)

def rand_interval(intv):
    intv += intv*rand_level*random.uniform(-1, 1)
    if intv < 60*60:
        intv = 60*60
    elif intv > 60*60*24*7:
        intv = 60*60*24*7
    return(int(intv))

def confirm(pct, p, last_update_id=None):
    if use_telegram == 0:
        conf = input("Your price feed change is over " + format(pct*100, ".1f") + "% (" + p + " USD/STEEM) If you confirm this, type 'confirm': ")
        if conf.lower() == "confirm":
            return True
        else:
            reconf = input("You denied to publish this feed. Are you sure? (Y/n): ")
            if reconf.lower() == "n":
                conf = input("If you confirm this, type 'confirm': ")
                if conf.lower() == "confirm":
                    return True
                else:
                    print("Publishing denied")
                    return False
            else:
                print("Publishing denied")
                return False
    elif use_telegram == 1:
        custom_keyboard = [["deny"]]
        reply_markup = json.dumps({"keyboard":custom_keyboard, "resize_keyboard": True})
        conf_msg = ("Your price feed change is over " + format(pct*100, ".1f") + "% (" + p + " USD/STEEM) If you confirm this, type 'confirm'")
        payload = {"chat_id":telegram_id, "text":conf_msg, "reply_markup":reply_markup}
        m = telegram("sendMessage", payload)
        while True:
            try:
                updates = telegram("getUpdates", {"offset":last_update_id+1})["result"][-1]
                chat_id = updates["message"]["from"]["id"]
                update_id = updates["update_id"]
                cmd = updates["message"]["text"]
            except:
                update_id = 0
                cmd = ""
            if update_id > last_update_id and cmd != "":
                if chat_id == telegram_id and cmd.lower() == "confirm":
                    payload = {"chat_id":telegram_id, "text":"Publishing confirmed"}
                    m = telegram("sendMessage", payload)
                    last_update_id = update_id
                    return True
                elif chat_id == telegram_id and cmd.lower() == "deny":
                    payload = {"chat_id":telegram_id, "text":"Publishing denied"}
                    m = telegram("sendMessage", payload)
                    last_update_id = update_id
                    return False
                else:
                    payload = {"chat_id":telegram_id, "text":"Wrong command. Please select confirm or deny"}
                    m = telegram("sendMessage", payload)
                    last_update_id = update_id
            time.sleep(3)

def telegram(method, params=None):
    url = "https://api.telegram.org/bot"+telegram_token+"/"
    params = params
    r = requests.get(url+method, params = params).json()
    return r

def btc_usd():
    prices = {}
    try:
        r = requests.get("https://api.bitfinex.com/v1/pubticker/BTCUSD").json()
        prices['bitfinex'] = {'price': float(r['last_price']), 'volume': float(r['volume'])}
    except:
        pass
    try:
        r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker").json()
        prices['coinbase'] = {'price': float(r['price']), 'volume': float(r['volume'])}
    except:
        pass
    try:
        r = requests.get("https://www.okcoin.com/api/v1/ticker.do?symbol=btc_usd").json()["ticker"]
        prices['okcoin'] = {'price': float(r['last']), 'volume': float(r['vol'])}
    except:
        pass
    try:
        r = requests.get("https://www.bitstamp.net/api/v2/ticker/btcusd/").json()
        prices['bitstamp'] = {'price': float(r['last']), 'volume': float(r['volume'])}
    except:
        pass
    if not prices:
       return 0
    total_usd = 0
    total_btc = 0
    for p in prices.values():
        total_usd += p['price'] * p['volume']
        total_btc += p['volume']
    avg_price = total_usd / total_btc
    return avg_price

def bts_dex_hist(address):
    for s in address:
        try:
            ws = create_connection(s)
            login = json.dumps({"jsonrpc": "2.0", "id":1,"method":"call","params":[1,"login",["",""]]})
            hist_api = json.dumps({"jsonrpc": "2.0", "id":2, "method":"call","params":[1,"history",[]]})
            btc_hist = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "call", "params": [2, "get_fill_order_history", ["1.3.861", "1.3.973", 50]]})
            bts_hist = json.dumps({"jsonrpc": "2.0", "id": 4, "method": "call", "params": [2, "get_fill_order_history", ["1.3.0", "1.3.973", 50]]})
            bts_feed = json.dumps({"jsonrpc": "2.0", "id": 5, "method": "call", "params": [0, "get_objects", [["2.4.3"]]]})
            ws.send(login)
            ws.recv()
            ws.send(hist_api)
            ws.recv()
            ws.send(btc_hist)
            dex_btc_h = json.loads(ws.recv())["result"]
            ws.send(bts_hist)
            dex_bts_h = json.loads(ws.recv())["result"]
            ws.send(bts_feed)
            bts_btc_feed = json.loads(ws.recv())["result"][0]["current_feed"]["settlement_price"]
            bts_btc_p = bts_btc_feed["base"]["amount"]/bts_btc_feed["quote"]["amount"]/10**3
            ws.close()
            return (dex_btc_h, dex_bts_h, bts_btc_p)
        except:
            return (0, 0, 0)


if __name__ == '__main__':
    print("Connecting to Steem RPC")

    steem = Steem(node=steemnode, wif=wif)
    info = steem.info()
    try:
        bh = steem.info()["head_block_number"]
        print("Connected. Current block height is " + str(bh))
    except:
        print("Connection error. Check your cli_wallet")
        quit()

    if use_telegram == 1:
        try:
            print("Connecting to Telegram")
            test = telegram("getMe")
        except:
            print("Telegram connection error")
            quit()

    steem_q = 0
    btc_q = 0
    last_update_t = 0
    try:
        last_update_id = telegram("getUpdates")["result"][-1]["update_id"]
    except:
        last_update_id = 0
    interval = rand_interval(interval_init)
    time_adj = time.time() - datetime.utcnow().timestamp()
    start_t = (time.time()//freq)*freq - freq
    last_t = start_t - 1
    my_info = steem.rpc.get_witness_by_account(witness)
    if float(my_info["sbd_exchange_rate"]["quote"].split()[0]) == 0:
        last_price = 0
    else:
        last_price = float(my_info["sbd_exchange_rate"]["base"].split()[0]) / float(my_info["sbd_exchange_rate"]["quote"].split()[0]) 
    print("Your last feed price is " + format(last_price, ".3f") + " USD/STEEM")

    while True:
        curr_t = (time.time()//freq)*freq - freq
        if curr_t > last_t:
# Bittrex
            try:
                bt_h = requests.get("https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-STEEM")
                bt_hist = bt_h.json()
                for i in range(200):
                    strf_t = bt_hist["result"][i]["TimeStamp"]
                    unix_t = dateutil.parser.parse(strf_t).timestamp()
                    unix_t += time_adj
                    if unix_t >= curr_t:
                        steem_q += bt_hist["result"][i]["Quantity"]
                        btc_q += bt_hist["result"][i]["Total"]
                        pass
                    else:
                        break
            except:
                print("Error in fetching Bittrex market history              ")
                pass

# Poloniex
            try:
                po_h = requests.get("https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_STEEM&start="+str(curr_t))
                po_hist = po_h.json()
                for i in range(len(po_hist)):
                    steem_q += float(po_hist[i]["amount"])
                    btc_q += float(po_hist[i]["total"])
                    pass
            except:
                print("Error in fetching Poloniex market history")
                pass

# Bitshares DEX
            dex_btc_h, dex_bts_h, bts_btc_p = bts_dex_hist(bts_ws)
            for i in range(50):
                if (isinstance(dex_btc_h, list) and dateutil.parser.parse(dex_btc_h[i]["time"]).timestamp() + time_adj) >= curr_t:
                    if dex_btc_h[i]["op"]["pays"]["asset_id"] == "1.3.973":
                        steem_q += float(dex_btc_h[i]["op"]["pays"]["amount"])/10**3
                        btc_q += float(dex_btc_h[i]["op"]["receives"]["amount"])/10**8
                    else:
                        steem_q += float(dex_btc_h[i]["op"]["receives"]["amount"])/10**3
                        btc_q += float(dex_btc_h[i]["op"]["pays"]["amount"])/10**8
            for i in range(50):
                if (isinstance(dex_btc_h, list) and dateutil.parser.parse(dex_bts_h[i]["time"]).timestamp() + time_adj) >= curr_t:
                    if dex_bts_h[i]["op"]["pays"]["asset_id"] == "1.3.973":
                        steem_q += float(dex_bts_h[i]["op"]["pays"]["amount"])/10**3
                        btc_q += (float(dex_bts_h[i]["op"]["receives"]["amount"])/10**5)*bts_btc_p
                    else:
                        steem_q += float(dex_bts_h[i]["op"]["receives"]["amount"])/10**3
                        btc_q += (float(dex_bts_h[i]["op"]["pays"]["amount"])/10**5)*bts_btc_p
            last_t = curr_t

        if curr_t - start_t >= interval:
            if steem_q > 0:
                price = btc_q/steem_q*btc_usd()
                price_str = format(price*(1-discount), ".3f")
                # If this is our first price submission, just execute
                if last_price == 0:
                    publish_feed(witness, price_str)
                    print("Published price feed: " + price_str + " (-" + str(discount * 100) + "\%) USD/STEEM at " + time.ctime()+"\n")
                    last_price = price
                    steem_q = 0
                    btc_q = 0
                    last_update_t = curr_t
                # otherwise perform normally
                else:
                    if (abs(1 - price/last_price) < min_change) and ((curr_t - last_update_t) < max_age):
                        print("No significant price change and last feed is still valid")
                        print("Last price: " + format(last_price, ".3f") + "  Current price: " + price_str + "  " + format((price/last_price*100 - 100), ".1f") + "%  / Feed age: " + str(int((curr_t - last_update_t)/3600)) + " hours")
                        steem_q = 0
                        btc_q = 0
                    else:
                        if abs(1 - price/last_price) > manual_conf:
                            if confirm(manual_conf, price_str, last_update_id) is True:
                                publish_feed(witness, price_str)
                                print("Published price feed: " + price_str + " USD/STEEM at " + time.ctime()+"\n")
                                last_price = price
                        else:
                            publish_feed(witness, price_str)
                            print("Published price feed: " + price_str + " USD/STEEM at " + time.ctime()+"\n")
                            last_price = price
                        steem_q = 0
                        btc_q = 0
                        last_update_t = curr_t
            else:
                print("No trades occured during this period")
            interval = rand_interval(interval_init)
            start_t = curr_t
        left_min = (interval - (curr_t - start_t))/60
        print(str(int(left_min)) + " minutes to next update / Volume: " + format(btc_q, ".4f") + " BTC  " + str(int(steem_q)) + " STEEM\r")
        sys.stdout.flush()
        time.sleep(freq*0.7)
