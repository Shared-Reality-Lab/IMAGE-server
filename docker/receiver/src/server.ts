import express from "express";

const app = express();
const port = 8080;

app.use(express.json());

app.post("/atp/render", (req, res) => {
    res.json(
        {
            "request_uuid": "5901107e-6ca4-4361-96e4-b295512f7dd9",
            "timestamp": 1618590997,
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
});

app.listen(port, () => {
    // tslint:disable-next-line:no-console
    console.log(`Started server on port ${port}`);
});
