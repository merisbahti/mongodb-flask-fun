from flask import Flask, make_response, session, redirect, url_for, render_template, request
from pymongo import Connection, MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS
from gridfs.errors import NoFile
from werkzeug import secure_filename, Response
from util.id_generator import id_generator

import datetime

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

@app.route("/upload", methods=['POST'])
def upload():
    try:
        if request.method == 'POST':
            files = request.files.getlist("file")
            if len(files) < 1:
                return "no files" + str(files)
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
            return "".join(["localhost:5000/", str(upload_id)])
        return "error"
    except OSError:
        return "No space left on server!"

@app.route('/<upload_id>')
def show(upload_id):
    index = coll.find_one({"upload_id": upload_id})
    if not index:
        return "not found"
    session[upload_id] = "true";
    return render_template("serve.html", indexes=index['indexes'])

@app.route('/file/<oid>')
def file(oid):
    try:
        file = FS.get(ObjectId(oid))
        if (file.upload_id not in session):
                return redirect(url_for('show', upload_id = file.upload_id))
        response = make_response(file.read())
        response.mimetype = file.content_type
        response.headers['Content-Disposition'] = "attachment; filename=\""+file.name+"\""
        return response
    except NoFile:
        return "No file"

@app.route('/files')
def list_gridfs_files():
    return str("<br>".join(FS.list())) 

app.debug = True
if __name__ == "__main__":
    app.run(host='0.0.0.0')
