import express from "express";
import Ajv from "ajv/dist/2020";

import querySchemaJSON from "/usr/local/share/schemas/request.schema.json";
import { docker, getPreprocessorServices, getHandlerServices } from "./docker";

const app = express();
const port = 8080;
const ajv = new Ajv({
    "schemas": [querySchemaJSON]
});

const PREPROCESSOR_TIME_MS = 15000;

app.use(express.json());

app.post("/atp/render", (req, res) => {
    if (ajv.validate("https://bach.cim.mcgill.ca/atp/query.schema.json", req.body)) {
        // get list of preprocessors and handlers
        docker.listContainers().then(async (containers) => {
            const preprocessors = getPreprocessorServices(containers);
            const handlers = getHandlerServices(containers);

            // TODO do things with these services
            // Preprocessors run in order
            const data = req.body;
            for (const preprocessor of preprocessors) {
                const controller = new AbortController();
                const timeout = setTimeout(() => {
                    controller.abort();
                }, PREPROCESSOR_TIME_MS);

                await fetch(`http://${preprocessor}/atp/preprocessor`, {
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "signal": controller.signal
                }).then(resp => {
                    return resp.json();
                }).then(json => {
                    data.preprocessors[preprocessor] = json;
                }).catch(err => {
                    // Try to continue...
                    // tslint:disable-next-line:no-console
                    console.error(err);
                });
            }

            // in docker, the service names are resolved and balanced automatically
        }).then(() => {
            res.json(
                {
                    "request_uuid": req.body.request_uuid,
                    "timestamp": Math.round(Date.now() / 1000),
                    "renderings": [
                      {
                        "metadata": {
                        "type_id": "697db3a5-2474-4b34-b203-670af34943bc",
                          "confidence": 85,
                          "creator_rendering": {
                            "metadata": {
                              "type_id": "697db3a5-2474-4b34-b203-670af34943bc",
                              "confidence": 100,
                              "description": null,
                              "creator_url": "https://srl.mcgill.ca/atp",
                              "more_details_rendering": null
                            },
                            "text_string": "Created by the McGill University SRL team"
                          },
                          "creator_url": "https://srl.mcgill.ca/atp/",
                          "more_details_rendering": {
                            "metadata": {
                              "type_id": "c640f825-6192-44ce-b1e4-dd52e6ce6c63",
                              "confidence": 73,
                              "description": "Activate to hear about this picture in 3D audio on your headphones.",
                              "creator_rendering": {
                                "metadata": {
                                  "type_id": "697db3a5-2474-4b34-b203-670af34943bc",
                                  "confidence": 100,
                                  "creator_url": "https://srl.mcgill.ca/atp/",
                                  "description": null,
                                  "more_details_rendering": null
                                },
                                "text_string": "Created by the McGill University SRL team"
                              }
                            },
                            "haptic_url": null,
                            "audio_url": "https://bach.cim.mcgill.ca/atp/testpages/tp01/test01.mp3",
                            "media_tags": null,
                            "more_details_rendering": null
                          }
                        },
                        "text_string": "Picture of a Pebble smartwatch strapped to a hairy leg outdoors."
                      }
                    ]
                  }
            );
        }).catch(e => {
            // tslint:disable-next-line:no-console
            console.error(e);
            res.status(500).send(e.name + ": " + e.message);
        });
    } else {
        res.status(400).send(ajv.errors);
    }
});

app.listen(port, () => {
    // tslint:disable-next-line:no-console
    console.log(`Started server on port ${port}`);
});
