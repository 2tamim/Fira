import datetime,hashlib
def get_filename(filename):
    _datetime=str(datetime.datetime.now())
    _filename=hashlib.sha256(_datetime.encode()).hexdigest()
    return _filename+filename