# Photo Tactile Svg Handler

Alpha quality: Insufficiently refined to be tested by end-users.

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-photo-tactile-svg)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a SVG that can be rendered as a tactile graphic to convey detected objects and detected semantic segments.

Data from object detection and semantic segmentation are used to create a SVG.
This SVG will be as per a specified [format](https://github.com/Shared-Reality-Lab/IMAGE-Monarch/tree/main#tactile-graphics) and might contain multiple layers with the number of layers equal to the number of object classes found within the photo. The semantic segments will be available independent of the layers.

When `object-segmentation` (SAM 3) output is available for a detected object, its precise polygon outline is drawn in place of that object's plain bounding-box rectangle. Semantic segmentation is otherwise scoped to background/environmental elements (sky, walls, floors, etc.) that object detection doesn't cover.