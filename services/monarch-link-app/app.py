from flask import Flask, request, jsonify, abort, Response
from flask_cors import CORS, cross_origin
import logging
import hashlib
import json

app = Flask(__name__)
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

@app.route("/create/<id>", methods=["POST"])
@cross_origin()
def render(id):
    if request.method=="POST":
        req_data=request.get_json()
        svgData = read_data()
        if id in svgData:
            if (svgData[id])["secret"] == req_data["secret"]:
                svgData[id] = {"secret":req_data["secret"], "data": req_data["data"], "layer": req_data["layer"]}
                write_data(svgData)
                return jsonify("Graphic in channel "+id+" has been updated!")
            else:
                return jsonify("Unauthorized access to existing channel!")
        else:
            svgData[id] = {"secret":req_data["secret"], "data": req_data["data"], "layer": req_data["layer"]}
            write_data(svgData)
            return jsonify("New channel created with code "+id)

@app.route("/display/<id>", methods=["GET"])
@cross_origin()
def display(id):
    if request.method=="GET":
        svgData = read_data()
        if id in svgData:
            response= Response()
            response.mimetype = "application/json"
            response.set_data(json.dumps({"renderings":[{"data":{"graphic":svgData[id]["data"], "layer": svgData[id]["layer"]}}]}))
            response.add_etag(hashlib.md5((svgData[id]["data"]+svgData[id]["layer"]).encode()))
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