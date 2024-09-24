# Autour Handler

Beta quality: Useful enough for testing by end-users.

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-autour)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a spatialized audio scene indicating points of interest around a location.
Points of interest are determined using the [Autour Preprocessor](../../preprocessors/autour).
It is heavily influenced by and depends on the [Autour project](http://autour.mcgill.ca/).

It takes data from the autour preprocessor, sorts clockwise from due north based on each point of interest's bearing
from the location specified in the request, filters out those within 250 meters, and forwards those to
[the SuperCollider responder for audio processing](../../services/supercollider-service/autour.scd).

It also communicates with the [ESPnet TTS service](../../services/espnet-tts) for text-to-speech.
