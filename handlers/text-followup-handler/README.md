# Text Followup Handler

Alpha quality: Insufficiently refined to be tested by end-users.

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-text-followup)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that returns a text-only response to a followup query posed by the user.

Data from text-followup preprocessor are used to generate the response.
Only the brief response from the preprocessor is included in the handler response.