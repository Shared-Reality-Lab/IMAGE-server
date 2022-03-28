# Generic TTS Handler [DEPRECATED]

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373)

## What is this?

This used to use the [object detection output from the YOLO preprocessor](../../preprocessors/yolo) to create spatialized
audio using the [ESPnet TTS service](../../services/espnet-tts) and [SuperCollider responder](../../services/supercollider-images/supercollider-service/generic.scd).
It is very specifically written and has been succeeded by the more generic [photo audio handler](../photo-audio-handler).
