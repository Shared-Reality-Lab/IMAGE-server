/*
 * Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 * You should have received a copy of the GNU Affero General Public License
 * and our Additional Terms along with this program.
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.
 */
import Ajv2020 from "ajv";
import querySchemaJSON from "./schemas/request.schema.json";
import handlerResponseSchemaJSON from "./schemas/handler-response.schema.json";
import preprocessorResponseSchemaJSON from "./schemas/preprocessor-response.schema.json";
import responseSchemaJSON from "./schemas/response.schema.json";
import definitionsJSON from "./schemas/definitions.json";

export const ajv = new Ajv2020({
    "schemas": [definitionsJSON, querySchemaJSON, responseSchemaJSON, handlerResponseSchemaJSON, preprocessorResponseSchemaJSON]
});
