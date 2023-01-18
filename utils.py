caught, score, spot, images = {}, {}, {}, {}

DATABASES = {
    'fa21': 'spottings',
    'sp22': 'sp22-spottings',
    '61a-su22': '61a-su22-spottings',
    '61a-fa22': '61a-fa22-spottings',
    'csm-exec': 'csm-exec-spottings',
    'fa22': 'cb-fa22-spottings',
    'sp23': 'cb-sp23-spottings',
    '61a-sp23': '61a-sp23-spottings'
}

DB_NAME = DATABASES['sp23']

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
