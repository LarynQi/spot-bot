caught, score, spot, images = {}, {}, {}, {}

DATABASES = {
    'fa21': 'spottings',
    'sp22': 'sp22-spottings',
    '61a-su22': '61a-su22-spottings',
    '61a-fa22': '61a-fa22-spottings',
    'csm-exec': 'csm-exec-spottings',
    'fa22': 'cb-fa22-spottings',
    'sp23': 'cb-sp23-spottings',
    '61a-sp23': '61a-sp23-spottings',
    'anova': 'anova-spottings',
    '180': '180-spottings',
    'data8-fa23': 'data8-fa23-spottings',
    'fa23': 'cb-fa23-spottings',
    'data8-sp24': 'data8-sp24-spottings'
}

DB_NAME = DATABASES['data8-sp24']

def read_db(client, db_name=DB_NAME):
    db = client.get_database(db_name)
    db_caught, db_spot, db_images = db.get_collection('caught'), db.get_collection('spot'), db.get_collection('images')

    caught, spot, images = {item['_id']: item['data'] for item in db_caught.find({})}, {item['_id']: item['data'] for item in db_spot.find({})}, {item['_id']: item['data'] for item in db_images.find({})}

    return caught, spot, images

def write_db(*args, db_name=DB_NAME):
    db = args[0].get_database(db_name)
    collections = [db.get_collection('caught'), db.get_collection('spot'), db.get_collection('images')]
    for collection, data in zip(collections, args[1:]):
        for entry in data:
            try:
                collection.insert_one({"_id": entry, "data": data[entry]})
            except:
                collection.update_one({"_id": entry}, {'$set': {"data": data[entry]}})

def read_prev(client, spotter, db_name=DB_NAME):
    db = client.get_database(db_name)
    try:
        res = next(iter(db.get_collection('prev').find({})))
        return [res["_id"], res["data"]]
    except:
        return [spotter, 0] 
    

def write_prev(client, prev, db_name=DB_NAME):
    collection = client.get_database(db_name).get_collection('prev')
    collection.remove({})
    collection.insert_one({"_id": prev[0], "data": prev[1]})

def init_db(client, db_name):
    db = client.get_database(db_name)
    spot = db.get_collection('spot')
    spot.insert_one({})
    spot.remove({})
    caught = db.get_collection('caught')
    caught.insert_one({})
    caught.remove({})
    images = db.get_collection('images')
    images.insert_one({})
    images.remove({})
    prev = db.get_collection('prev')
    prev.insert_one({})
    prev.remove({})

    curr_db_collection = client.get_database(DATABASES['fa23']).get_collection('curr_db')
    curr_db_collection.remove({})
    curr_db_collection.insert_one({"_id": 0, "data": db_name})

    return db_name

def read_db_name(client):
    db = client.get_database(DATABASES['fa23'])
    collection = db.get_collection('curr_db')
    return next(iter(collection.find({})))['data']
