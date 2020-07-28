import pymongo
import config

DEFAULT_THRESHOLD = 1

mongo_client = pymongo.MongoClient(config.mongo_conn)
try:
    print('MongoDB version is %s' % mongo_client.server_info()['version'])
except pymongo.errors.OperationFailure as error:
    print(error)
keep_alert_db = mongo_client.keep_alert
users_col = keep_alert_db.users


def add_address_to_db(address, user_id):
    user = users_col.find_one({'_id': user_id})
    if user is None:
        users_col.insert_one({
            '_id': user_id,
            'addresses': [address],
            'threshold': DEFAULT_THRESHOLD
        })
    else:
        if address not in user['addresses']:
            addresses = user['addresses']
            addresses.append(address)
            users_col.update_one({'_id': user_id}, {
                '$set': {
                    '_id': user_id,
                    'addresses': addresses
                }
            })


def remove_address_from_db(address, user_id):
    addresses = get_addresses_from_db(user_id)
    addresses.remove(address)
    users_col.update_one({'_id': user_id}, {
        '$set': {
            '_id': user_id,
            'addresses': addresses
        }
    })


def get_addresses_from_db(user_id):
    user = users_col.find_one({'_id': user_id})
    return user['addresses']


def add_threshold_to_db(threshold, user_id):
    user = users_col.find_one({'_id': user_id})
    if user is None:
        users_col.insert_one({
            '_id': user_id,
            'addresses': [],
            'threshold': threshold
        })
    else:
        users_col.update_one({'_id': user_id}, {
            '$set': {
                '_id': user_id,
                'threshold': threshold
            }
        })


def get_threshold_from_db(user_id):
    user = users_col.find_one({'_id': user_id})
    return user['threshold']


def get_users_from_db():
    return users_col.find({})
