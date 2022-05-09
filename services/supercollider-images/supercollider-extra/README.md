# SuperCollider "Extra" Docker Image

This is an image build using the [base SuperCollider image](../supercollider) that includes extra features useful, but not specific to, the IMAGE project.
In addition to the base image,

* utilities for MP3 and OGG are installed (`lame` and `vorbis-tools`);
* [sc3-plugins](https://github.com/supercollider/sc3-plugins) is installed with the version specified by the `VERSION` build argument;
* the MP3, ATK, SC-HOA, and Vowel quarks and their dependencies are installed.

Note that some dependencies are removed that don't work on a headless setup (i.e., PointView and parts of ws-lib).
