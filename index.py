from flask import Flask, make_response, session, redirect, url_for
from flask import render_template
from flask import request

from pymongo import Connection
from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS
from gridfs.errors import NoFile
from werkzeug import secure_filename 
from werkzeug import Response
import datetime

import string
import random

app = Flask(__name__)
app.secret_key = "really_secret_key"

client = MongoClient()
db = client.index_db
coll = db.index_collection

FSDB = Connection().gridfs_server_test
FS = GridFS(FSDB)

@app.route("/")
def hello():
    return render_template("upload.html") 

def id_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

@app.route("/upload", methods=['POST'])
def upload():
    if request.method == 'POST':
        files = request.files.getlist("file")
        indexes = {} 
        upload_id = id_generator() 
        for file in files:
            filename = secure_filename(file.filename)
            oid = FS.put(file, 
                    content_type=file.content_type, 
                    filename=filename,
                    upload_id=upload_id)
            indexes[str(oid)] = filename 
        entry = {"upload_id": upload_id,
                 "indexes": indexes,
                 "date": datetime.datetime.utcnow()}
        coll.insert(entry)
        return " ".join([str(upload_id), str(oid)])
    return "error"

@app.route('/<upload_id>')
def show(upload_id):
    index = coll.find_one({"upload_id": upload_id})
    session[upload_id] = upload_id;
    return render_template("serve.html", indexes=index['indexes'])

@app.route('/file/<oid>')
def file(oid):
    #Check for session first.
    try:
        file = FS.get(ObjectId(oid))
        if (file.upload_id in session):
                return redirect(url_for('show', upload_id = file.upload_id))
        response = make_response(file.read())
        response.mimetype = file.content_type
        response.headers['Content-Disposition'] = "attachment; filename=\""+file.upload_id+"\""
        return response
    except NoFile:
        return "No file"

app.debug = True
if __name__ == "__main__":
    app.run()
