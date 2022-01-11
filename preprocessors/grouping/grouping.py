# Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
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
# <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.

from flask import Flask, request, jsonify
import json
import time
import jsonschema
import logging
import collections
from math import sqrt
from operator import itemgetter


app = Flask(__name__)


def calculate_diagonal(x1, y1, x2, y2):
    #refered from
    #https://www.w3resource.com/python-exercises/python-basic-exercise-40.php
    diag = sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return diag


@app.route("/preprocessor", methods=['POST', 'GET'])
def readImage():
    object_type = []
    dimensions = []
    ungrouped = []
    flag = 0
    with open('./schemas/preprocessors/grouping.schema.json') as jsonfile:
        data_schema = json.load(jsonfile)
    with open('./schemas/preprocessor-response.schema.json') as jsonfile:
        schema = json.load(jsonfile)
    with open('./schemas/definitions.json') as jsonfile:
        definitionSchema = json.load(jsonfile)
    with open('./schemas/request.schema.json') as jsonfile:
        first_schema = json.load(jsonfile)
    #Following 6 lines refered from
    #https://stackoverflow.com/questions/42159346/jsonschema-refresolver-to-resolve-multiple-refs-in-python
    schema_store = {
        schema['$id']: schema,
        definitionSchema['$id']: definitionSchema
    }
    resolver = jsonschema.RefResolver.from_schema(
        schema, store=schema_store)
    content = request.get_json()
    try:
        validator = jsonschema.Draft7Validator(first_schema, resolver=resolver)
        validator.validate(content)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 400
    preprocessor = content["preprocessors"]
    if "ca.mcgill.a11y.image.preprocessor.objectDetection" \
            not in preprocessor:
        logging.info("Object detection output not "
                     "available. Skipping...")
        return "", 204
    oDpreprocessor = \
        preprocessor["ca.mcgill.a11y.image.preprocessor.objectDetection"]
    objects = oDpreprocessor["objects"]
    for i in range(len(objects)):
        object_type.append(objects[i]["type"])
        dimensions.append(objects[i]["dimensions"])
    repetition = [item for item, count in
                  collections.Counter(object_type).items() if count > 1]
    group = [[] for i in range(len(repetition))]
    final_group = []
    check_group = [False] * len(objects)

    for i in range(len(repetition)):
        flag = 0
        for j in range(len(objects)):
            if objects[j]["type"] == repetition[i]:
                flag = 1
                group[i].append([objects[j]["ID"],
                                 calculate_diagonal(dimensions[j][0],
                                                    dimensions[j][1],
                                                    dimensions[j][2],
                                                    dimensions[j][3])])
                check_group[j] = True
        if flag == 1:
            group[i] = sorted(group[i], key=itemgetter(1))
    dummy = [[] for i in range(len(group))]
    for i in range(len(group)):
        for j in range(len(group[i])):
            dummy[i].append(group[i][j][0])
        final_group.append({"IDs": dummy[i]})

    for i in range(len(check_group)):
        if check_group[i] is False:
            ungrouped.append(i)
    request_uuid = content["request_uuid"]
    timestamp = time.time()
    name = "ca.mcgill.a11y.image.preprocessor.grouping"
    data = {"grouped": final_group, "ungrouped": ungrouped}
    try:
        validator = jsonschema.Draft7Validator(data_schema)
        validator.validate(data)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    response = {
        "title": "Grouping Data",
        "description": "Grouped data for objects",
        "request_uuid": request_uuid,
        "timestamp": int(timestamp),
        "name": name,
        "data": data
    }
    try:
        validator = jsonschema.Draft7Validator(schema, resolver=resolver)
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        logging.error(e)
        return jsonify("Invalid Preprocessor JSON format"), 500
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
