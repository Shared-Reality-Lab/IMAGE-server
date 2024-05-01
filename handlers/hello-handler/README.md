# Hello, Handler!

Beta quality: Useful enough for testing by end-users.

## What is this?

This is an extremely basic version of a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) meant to illustrate its basic operation.
To recap, a handler responds to POST requests sent to `/handler` containing an IMAGE request body along with any preprocessors. It then must respond with a list of renderings.
This handler just extracts the dimensions of an image sent to it and returns a text rendering of those dimensions.
