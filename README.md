# IMAGE-server
IMAGE server components, including Handlers

## IMAGE project information
Please see https://image.a11y.mcgill.ca for general information about the project.

If you wish to contribute to the project, the following wiki page is a good starting point, including for those on the IMAGE project team:
https://github.com/Shared-Reality-Lab/IMAGE-server/wiki

IMAGE as a whole is in beta. McGill operates a public server that the IMAGE browser extension uses by default, which runs various preprocessors and handlers that the IMAGE team deems ready for testing by end users. There are many additional components in the IMAGE code repositories, some of which are not considered ready for use. These are made available for researchers and others as alpha code that requires further refinement before it is likely usable in practice. Caveats are generally noted in the README for each component. If you are a researcher evaluating or building on IMAGE, we ask that you distinguish between beta and alpha code when referencing specific IMAGE components and functionality. As a general reference for the IMAGE server architecture, please use the following paper:

Juliette Regimbal, Jeffrey R. Blum, Cyan Kuo, and Jeremy R. Cooperstock. 2024. IMAGE: An Open-Source, Extensible Framework for Deploying Accessible Audio and Haptic Renderings of Web Graphics. ACM Trans. Access. Comput. 17, 2, Article 11 (June 2024), 17 pages. https://doi.org/10.1145/3665223

## Set Up

Clone this repository. Note that the schemas are a submodule, so you need to either get them in the initial clone, e.g.,
```
git clone --recurse-submodules git@github.com:Shared-Reality-Lab/IMAGE-server.git
```

or else get them after you've done the initial clone (while in the root of the cloned repo on your local machine):
```
git submodule init
git submodule update
```

## License

IMAGE project components (e.g., IMAGE browser extension and IMAGE Services), henceforth "Our Software" are licensed under GNU GPL3 (https://www.gnu.org/licenses/gpl-3.0.en.html) or AGPLv3 terms (https://www.gnu.org/licenses/agpl-3.0.txt) or later, as indicated in specific repositories or files on the project github located at https://github.com/Shared-Reality-Lab.

If you incorporate IMAGE code into your own project, but do not want to release your changes and additions consistent with the open source terms under which the IMAGE code is licensed, you may contact us to obtain an alternative license. For all inquiries, please contact us at image@cim.mcgill.ca.

If you are making a contribution to IMAGE, please note that we [require a Contributor License Agreement (CLA)](/CLA.md).
