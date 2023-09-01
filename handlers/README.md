# IMAGE Handlers

## What handlers are and how they work

Handlers are docker services that take the initial request and preprocessor results and produce as many meaningful renderings as possible.
Typically, handlers will act in a certain scenario, for example with photographs. Outside of their particular scenario, handlers typically
will produce no renderings.

Each handler advertises itself to the orchestrator component by joining the shared IMAGE network over docker and adding the label
`ca.mcgill.a11y.image.handler: enable`. When this is done, it will receive HTTP requests at `/handler` containing the data that may be
needed. Handlers work independently of other handlers and cannot share data between each other. For functionality to be shared, those functions
should be implemented as libraries installed in each handler or encapsulated in a separate helper service (see the `/services` directory for examples).

More information on handlers and how they fit into the overall system is available [on the wiki](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services).

## What is in this directory

This directory contains all the handlers produced by the IMAGE project. Not all the handlers here are currently running on our server at
[https://image.a11y.mcgill.ca](https://image.a11y.mcgill.ca)! All subdirectories prefixed with `hello-` are demonstrations for different
tasks and do *not* provide an experience that we consider useful to actual end users. Other handlers are now deprecated and have been replaced, but are kept here for documentation and reference.
As of 2022-06-29, these are the statuses of the handlers:

* Supported
    * `autour-handler` (embedded maps)
    * `high-charts` ([Highcharts](https://www.highcharts.com/) renderings)
    * `motd` (custom status messages)
    * `photo-audio-handler` (photographs, audio-only)
    * `photo-audio-haptics-handler` (photographs, force feedback)
* Demonstration
    * `hello-handler`
    * `hello-haptics-handler`
    * `hello-svg-handler`
    * `hello-tts-handler`
    * `ocr-handler`
* Deprecated
    * `generic-tts-handler` (see photo-audio-handler)
    * `object-text-handler` (see photo-audio-handler)
    * `pie-chart-handler` (see high-charts)
    * `segment-handler` (see photo-audio-handler)

For more information, consult the individual READMEs of the handlers.

## Language Handling
Some handlers use `multilang-support` microservice to translate its rendering to different languages:
* `photo-audio-handler`
* `high-charts` 
* `autour-handler`

Please refer to [Section 7 of the IMAGE wiki](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/7.-Multilang-Support-for-IMAGE-Guide) regarding the handlers for more details.