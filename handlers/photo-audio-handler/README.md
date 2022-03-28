# Photo Audio Handler

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-photo-audio)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a sptialized audio scene to convey detected objects and detected semantic segments.
As of the time of writing, these are determined using the YOLO preprocessor and CSAIL semseg preprocessor respectively.

Data from these two sources are used to create plain text description.
This description is used to create a text-to-speech rendering using [ESPnet](../../services/espnet-tts)
which is then passed to [SuperCollider](../../services/supercollider-service/photo.scd).
For audio, it will be opportunistically returned as segmented audio. Otherwise, it will just return a simple audio rendering.
