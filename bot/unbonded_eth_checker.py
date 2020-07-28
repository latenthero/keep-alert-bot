import json
import time
import requests
import logging
from threading import Thread
from web3 import Web3
import mongo_helper
import config

w3 = Web3(Web3.HTTPProvider(config.web3_provider))
alerted_addresses = []
emoji_ok = u'\U00002705'
emoji_warn = u'\U000026A0'

class UnbondedEthChecker(Thread):

    def __init__(self, name):
        Thread.__init__(self)
        self.name = name

    def run(self):
        kb = w3.eth.contract(address=config.keep_bonding_address, abi=json.loads(config.keep_bonding_abi))
        while True:
            try:
                cursor = mongo_helper.get_users_from_db()
                for user in cursor:
                    #print(user)
                    for address in user['addresses']:
                        unbonded_wei = kb.functions.unbondedValue(w3.toChecksumAddress(address)).call()
                        unbonded_eth = w3.fromWei(unbonded_wei, 'ether')
                        if unbonded_eth < user['threshold'] and (user['_id'], address) not in alerted_addresses:
                            message = '%s Unbonded ETH amount is low (*%s ETH*) on address `%s`' % (emoji_warn, unbonded_eth, address)
                            alerted_addresses.append((user['_id'], address))
                            requests.get(config.message_url_pattern % (config.bot_token, message, user['_id']))
                            logging.info('Alert send to user %s. Text: %s' % (user['_id'], message))
                        if unbonded_eth > user['threshold'] and (user['_id'], address) in alerted_addresses:
                            message = '%s Unbonded ETH amount is sufficient (*%s ETH*) on address `%s`' % (emoji_ok, unbonded_eth, address)
                            alerted_addresses.remove((user['_id'], address))
                            requests.get(config.message_url_pattern % (config.bot_token, message, user['_id']))
                            logging.info('Alert send to user %s. Text: %s' % (user['_id'], message))
            except Exception as e:
                logging.exception("Exception occurred")
                print(e)
            time.sleep(10)
