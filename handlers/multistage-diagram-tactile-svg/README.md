# Multistage Diagram Tactile Svg Handler

Alpha quality: Insufficiently refined to be tested by end-users.

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-multistage-diagram-tactile-svg)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a SVG that can be rendered as a tactile graphic to convey multistage diagram.

Data from multistage diagram [preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#preprocessors=) are used to create a SVG.
This SVG will be as per a specified [format](https://github.com/Shared-Reality-Lab/IMAGE-Monarch/tree/main#tactile-graphics) and contains a single layer depicting semantic segments of the stages in the diagram and arrows indicating the links between them.