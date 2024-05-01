# Map Tactile Svg Handler

Alpha quality: Insufficiently refined to be tested by end-users.

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-map-tactile-svg)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a SVG that can be rendered as a tactile graphic to convey important streets, intersections and the point of interest (i.e. the location tag if found at the input latitude longitude coordinates).

Data from Open Street Maps(OSM) and Nominatim are used to create a SVG.
This SVG will be as per a specified [format](https://github.com/Shared-Reality-Lab/IMAGE-Monarch/tree/main#tactile-graphics) and will contain a layer with the streets. The intersections and the point of interest will be available independent of the layers.  