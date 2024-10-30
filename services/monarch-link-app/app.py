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
import re
import uuid
from werkzeug.routing import BaseConverter, ValidationError

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
            # return a dict if the file is empty
            return dict()


# generate an id that does not already exist
def generate_code(svgData):
    code = ''.join([str(random.randint(1, 8)) for i in range(6)])
    while code in svgData:
        code = generate_code(svgData)
    return code


# custom converter to validate that the id
# in the url is a valid id
class CodeConverter(BaseConverter):
    def to_python(self, value):
        # has six digits between 1 and 8
        pattern = re.compile("^[1-8]{6}$")
        # also has a length of six
        if not pattern.match(value):
            logging.debug('Received request with invalid ID value')
            raise ValidationError('Invalid id value')
        return value

    def to_url(self, value):
        return value


app.url_map.converters['code'] = CodeConverter


@app.route("/create", methods=["POST"])
@cross_origin()
def create():
    if request.method == "POST":
        logging.debug('Create request received')
        try:
            req_data = request.get_json()
            svgData = read_data()
            id = generate_code(svgData)
            secret = uuid.uuid4().hex
            svgData[id] = {"secret": bcrypt.generate_password_hash(secret)
                           .decode('utf-8'),
                           "data": req_data["data"],
                           "title": req_data["title"],
                           "layer": req_data["layer"]}
            write_data(svgData)
            logging.debug('Created new channel with code '+id)
            return {"id": id, "secret": secret}
        except KeyError:
            logging.debug("Unexpected JSON format. Returning 400")
            return "Unexpected JSON format", 400
        except Exception as e:
            logging.debug(e)
            abort(Response(response=e))


@app.route("/update/<code:id>", methods=["POST"])
@cross_origin()
def update(id):
    if request.method == "POST":
        try:
            logging.debug('Update request received')
            req_data = request.get_json()
            svgData = read_data()
            if id in svgData:
                if bcrypt.check_password_hash((svgData[id])["secret"],
                                              req_data["secret"]):
                    svgData[id] = {"secret":
                                   bcrypt.generate_password_hash(
                                    req_data["secret"]).decode('utf-8'),
                                   "data": req_data["data"],
                                   "title": req_data["title"],
                                   "layer": req_data["layer"]}
                    write_data(svgData)
                    logging.debug('Updated graphic')
                    return "Graphic in channel "+id+" has been updated!"
                else:
                    logging.debug('Unauthorized access to existing channel!')
                    return "Unauthorized access to existing channel!", 401
            else:
                svgData[id] = {"secret":
                               bcrypt.generate_password_hash(
                                req_data["secret"]).decode('utf-8'),
                               "data": req_data["data"],
                               "title": req_data["title"],
                               "layer": req_data["layer"]}
                write_data(svgData)
                logging.debug('TEMP: Created new channel using update!')
                return ("New channel created with code "+id +
                        ". Creating new ids using update is" +
                        " only intended for testing!")
        except KeyError:
            logging.debug("Unexpected JSON format. Returning 400")
            return "Unexpected JSON format", 400
        except Exception as e:
            logging.debug(e)
            abort(Response(response=e))


@app.route("/display/<code:id>", methods=["GET"])
@cross_origin()
def display(id):
    if request.method == "GET":
        logging.debug('Display request received')
        svgData = read_data()
        if id in svgData:
            try:
                response = Response()
                response.mimetype = "application/json"
                response.set_data(json.dumps({"renderings": [
                                {"data": {"graphic": svgData[id]["data"],
                                          "layer": svgData[id]["layer"]}}]}))
                response.add_etag(hashlib.md5(
                    (svgData[id]["data"]+svgData[id]["layer"]).encode()))
                response.make_conditional(request)
                logging.debug('Sending tactile response')
                return response
            except Exception as e:
                logging.debug(e)
                abort(Response(response=e))
        else:
            logging.debug('ID does not exist')
            return abort(404)


@app.route("/", methods=["POST", "GET"])
@cross_origin()
def home():
    return "Hi"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
