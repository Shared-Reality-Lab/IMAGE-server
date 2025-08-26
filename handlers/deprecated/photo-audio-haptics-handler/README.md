# Photo Audio Haptics Handler [DEPRECATED]


![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-photo-audio-haptics)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a scene to convey detected objects and semantic segments in a photograph through spatialized audio and haptic force-feedback.

For haptics, the following location information is generated from the two detected sources:

* Centroid and normalized bounding box information for each object;
* Centroid and normalized point information for each semantic segment.

The information is intended to be read by force-feedback haptic devices, such as the Haply 2DIY, for navigable contour tracing or point-to-point object movement.

For audio, data from the two detected sources are used to create a plain text description.
This description is used to create a text-to-speech rendering using [ESPnet](../../services/espnet-tts)
which is then passed to [SuperCollider](../../services/supercollider-images/supercollider-service/photo.scd).
It will be opportunistically returned as segmented audio. Otherwise, it will just return a simple audio rendering.

If successful, the handler returns a rendering with a list of JSON objects, called entities, each containing the type of audio and location information.
