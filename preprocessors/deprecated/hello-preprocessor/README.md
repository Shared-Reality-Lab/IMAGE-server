# Hello, Preprocessor!
# [DEPRECATED]: This preprocessor is no longer maintained. Please refer to any of the other examples of preprocessor present [here](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/main/preprocessors)

## What is this?

This is a basic version of a [preprocessor](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#preprocessors=)
as an example.
To recap, a preprocessor receives HTTP POST requests to `/preprocessor` containing a well-formated IMAGE request in the body.
It then does some process to either produce additional data relevant to the request or queries a third party for more information.
The results are returned along with a reverse domain name indicating what kind of information is available and how it can be interpreted.
This just returns the message "Hello, world!" as the data and does no actual processing or communication of a request.
