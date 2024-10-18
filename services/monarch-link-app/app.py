# Copyright (c) 2024 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# and our Additional Terms along with this program.
# If not, see
# <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.

from flask import Flask, request, abort, Response
from flask_bcrypt import Bcrypt
from flask_cors import CORS, cross_origin
import logging
import hashlib
import json
import random
import uuid

app = Flask(__name__)
bcrypt = Bcrypt(app)
logging.basicConfig(level=logging.DEBUG)

CORS(
    app, resources={r"/*": {"origins": "*"}}
)  # CORS allowed for all domains on all routes

try:
    with open("data.json", 'x') as file:
        json.dump(dict(), file)
except FileExistsError:
    logging.debug("The file already exists")


def write_data(svgData):
    with open("data.json", "w") as outfile:
        json.dump(svgData, outfile)


def read_data():
    with open('data.json', 'r') as openfile:
        try:
            return json.load(openfile)
        except Exception:
            return dict()


def generate_code(svgData):
    code = ''.join([str(random.randint(1, 9)) for i in range(6)])
    while code in svgData:
        code = generate_code(svgData)
    return code


@app.route("/create/<title>", methods=["POST"])
@cross_origin()
def create(title):
    if request.method == "POST":
        req_data = request.get_json()
        svgData = read_data()
        id = generate_code(svgData)
        secret = uuid.uuid4().hex
        svgData[id] = {"secret": bcrypt.generate_password_hash(secret).decode('utf-8'),
                       "data": req_data["data"],
                       "layer": req_data["layer"]}
        write_data(svgData)
        return {"id": id, "secret": secret}


@app.route("/update/<id>", methods=["POST"])
@cross_origin()
def update(id):
    if request.method == "POST":
        req_data = request.get_json()
        svgData = read_data()
        if id in svgData:
            if bcrypt.check_password_hash((svgData[id])["secret"], req_data["secret"]):
                svgData[id] = {"secret":
                               bcrypt.generate_password_hash(
                                   req_data["secret"]).decode('utf-8'),
                               "data": req_data["data"],
                               "layer": req_data["layer"]}
                write_data(svgData)
                return "Graphic in channel "+id+" has been updated!"
            else:
                return "Unauthorized access to existing channel!", 401
        else:
            svgData[id] = {"secret":
                           bcrypt.generate_password_hash(
                               req_data["secret"]).decode('utf-8'),
                           "data": req_data["data"],
                           "layer": req_data["layer"]}
            write_data(svgData)
            return ("New channel created with code "+id +
                    ". Creating new ids using update is only intended for testing!")


@app.route("/display/<id>", methods=["GET"])
@cross_origin()
def display(id):
    if request.method == "GET":
        svgData = read_data()
        if id in svgData:
            response = Response()
            response.mimetype = "application/json"
            response.set_data(json.dumps({"renderings": [
                              {"data": {"graphic": svgData[id]["data"],
                                        "layer": svgData[id]["layer"]}}]}))
            response.add_etag(hashlib.md5(
                (svgData[id]["data"]+svgData[id]["layer"]).encode()))
            response.make_conditional(request)
            return response
        else:
            return abort(404)


@app.route("/", methods=["POST", "GET"])
@cross_origin()
def home():
    return "Hi"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
