# SuperCollider Service

![license: AGPL](https://img.shields.io/badge/license-AGPL-success) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-service-supercollider)

## Overview

This is the SuperCollider-based audio synthesis service used by IMAGE that is based on our [generic SuperCollider images](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/supercollider)
Different actions are done using different endpoints in OSC specified in separate files (e.g., [photo.scd](./photo.scd)) and loaded in [loader.scd](./loader.scd).
Since each request contains plenty of data and usually TTS information, the initiating OSC command indicates the path to a JSON
file containing the relevant information. This file is written to a shared volume across the two containers, in this image mounted at `/tmp/sc-store/`.
If the file just contains plain data, it can be loaded normally.
If it also links to a relevant TTS file, both can be opened using the `IMAGE.loadTTSJSON` command in the IMAGE quark.
This will open the JSON file in the path given as an argument, then open the TTS file whose path is under the `ttsFileName` key and
load that as a SoundFile. The JSON and TTS will be returned as a Dictionary and SoundFile respectively.

The OSC request also should specify the location the resulting audio should be written (again in the shared volume).
When the file is successfully written, the service will typically send an OSC message to the caller with the content `/status/done`.
Otherwise, it will send a message including `/status/fail`.

Note that all spatialized audio at this time is binaural - we do not currently support any other configuration (although we would like to!).

An IMAGE quark containing the SynthDefs used in the service and various convenience functions is located in the [IMAGE directory](./IMAGE).

## Endpoints

### Supported

- `/render/photo [path to input JSON] [path to output MP3]`: The photo responder meant to create spatialized audio for objects and regions detected in a photograph. This corresponds to the [photo-audio-handler](../../../handlers/photo-audio-handler) and is also used by the [photo-audio-haptics-handler](../../../handlers/photo-audio-haptics-handler). Located in [photo.scd](./photo.scd).
- `/render/map/autourPOI [path to input JSON] [path to output MP3]`: Displays points of interest spatialized around the listener's head in a style similar to [Autour](http://autour.mcgill.ca). This corresponds to the [autour-handler](../../../handlers/autour-handler) and is implemented in [autour.scd](./autour.scd).
- `/render/charts/line [path to input JSON] [path to output MP3]`: A simple rendering of a [Highcharts](https://www.highcharts.com/) line chart. Corresponds to the [high-charts handler](../../../handlers/high-charts) and is implemented in [charts/line.scd](./charts/line.scd).
- `/render/charts/pie [path to input JSON] [path to output MP3]`: A simple rendering of a Highcharts pie chart. Corresponds to the [high-charts handler](../../../handlers/high-charts) and is implemented in [charts/pie.scd](./charts/pie.scd).

### Deprecated

- `/render/genreicObject [path to input JSON] [path to output WAV]`: Strictly organized rendering of objects detected in a photo only. Succeeded by the `/render/photo` endpoint above. Implemented in [generic.scd](./generic.scd).
- `/render/semanticSegmentation [path to input JSON] [path to output WAV]`: Strictly organized rendering of semantic segments in a photo only. Succeeded by the `/render/photo` endpoint above. Implemented in [segmentation.scd](./segmentation.scd).
- `/render [path to input JSON] [path to output WAV]`: Example of outputting audio. Fairly useless.
- `/ping`: Responds `/pong` when hit. May be useful for debugging.
