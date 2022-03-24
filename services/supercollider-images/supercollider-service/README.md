# SuperCollider Service

![license: AGPL](https://img.shields.io/badge/license-AGPL-success) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-service-supercollider)

## Overview

This is the SuperCollider-based audio synthesis service used by IMAGE that is based on our [generic SuperCollider images](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/supercollider)
Different actions are done using different endpoints in OSC specified in separate files (e.g., [photo.scd](./photo.scd)).
Since each request contains plenty of data and usually TTS information, the initiating OSC command indicates the path to a JSON
file containing the relevant information. This file is written to a shared volume across the two containers, in this image mounted at `/tmp/sc-store/`.
If the file just contains plain data, it can be loaded normally.
If it also links to a relevant TTS file, both can be opened using the `IMAGE.loadTTSJSON` command in the IMAGE quark.
This will open the JSON file in the path given as an argument, then open the TTS file whose path is under the `ttsFileName` key and
load that as a SoundFile. The JSON and TTS will be returned as a Dictionary and SoundFile respectively.

The OSC request also should specify the location the resulting audio should be written (again in the shared volume).
When the file is successfully written, the service will typically send an OSC message to the caller with the content `/status/done`.
Otherwise, it will send a message including `/status/fail`.

## Endpoints
