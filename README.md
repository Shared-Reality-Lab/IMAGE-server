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

## Working with Schemas

In the [schemas branch](https://github.com/Shared-Reality-Lab/IMAGE-server/tree/schemas) and submodule, we include various [JSON schema](https://json-schema.org/) files that describe the structure of the any data moving between components of the IMAGE architecture (orchestrator, preprocessors, handlers). This is done for three reasons:

* Schema provide documentation on the data;
* Components use them to check the data they *send* are correctly formatted;
* Components use them to check the data they *receive* are correctly formatted.

As such, schema files are closely related to the actual code running in any component, but are not specific to any one service. For example, [our object detection schema](https://github.com/Shared-Reality-Lab/IMAGE-server/blob/schemas/preprocessors/object-detection.schema.json) can describe the outputs of any number of vision models, allowing for us to upgrade and replace running services on an IMAGE server with the confidence that the system as a whole will continue working **if the new service uses the expected schema**. For this reason, we use [submodules](https://git-scm.com/docs/gitsubmodules.html) (i.e., a nested repository) to have a parallel review process for changes to schemas before they reach our main branch.

### How does the schemas submodule interact with main?

The schemas submodule is a nested repository within the main branch that tracks the schemas branch of this repository. Submodules are committed and updated as a single unit, tracking commits on the schemas branch. Branches from and pull requests to the schemas branch can be made so that new data types and features can be proposed, reviewed, and staged in the same manner as they would for components in the main branch.

This point about "staging" is important: we may agree on how the data for a part of the IMAGE architecture should be redefined, such as object detection preprocessors, but not yet be ready to update every component that interacts directly with those data. Even though our submodule tracks the schemas branch, it points to a specific commit and will only update to the HEAD of the branch when `git submodule update --remote` is run. This update can be included in a pull request to main alongside any required changes to the components that depend on the data described by the modified schema files. This concept can be difficult to understand, so a few practical examples are provided below.

#### I want to create a new schema for a new type of component

1. Design the schema: schemas describe a type of data in a reusable way, and should not be specific to a preprocessor or handler. Consider how best to do this, and draft an appropriate JSON schema in a new branch from the schemas branch.
2. Create a schema PR: make a pull request from the branch with your changes into the "schemas" branch, **not the main branch**. This will allow the team to give comments on your new data type and ensure it satisfies the requirements of the problem.
3. Merge the PR into schemas: note that this does not update what appears in main!
4. Create a new branch from main: in this branch, update the schemas submodule using `git submodule update --remote` and commit the change. Then, implement your new component(s) and make any other modifications so your new data type can be used.
5. Create a PR into main: the implementation of the components will be reviewed, not the design of the schemas.
6. Merge the PR into main: when this occurs, *all images will be rebuilt to use the latest version of the schemas submodule*. Begin testing on the staging server as you normally would.

#### I want to make a minor (non-breaking) change to a data type

1. Create a branch of `schemas` and implement.
2. Create a schema PR.
3. Merge the PR into `schemas`.
4. Create a PR to update the submodule in the main branch: include any updates to component functionality your modifications will allow.
5. Merge the PR into main.

#### I want to make a breaking change to a data type

1. Create a branch of schemas and implement.
2. Create a schema PR.
3. Merge the PR into schemas.
4. Create a new branch from main: update the schemas submodule and test all components that may use the modified data type extensively to ensure there are no regressions.
5. Merge the PR into main.

Note that if many different schemas are being modified, it may be necessary to delay merging PRs into the schemas branch until modifications to components are underway. Otherwise, PRs adding new schema files or making minor modifications may be blocked from merging into main until this process is complete.

## License

IMAGE project components (e.g., IMAGE browser extension and IMAGE Services), henceforth "Our Software" are licensed under GNU GPL3 (https://www.gnu.org/licenses/gpl-3.0.en.html) or AGPLv3 terms (https://www.gnu.org/licenses/agpl-3.0.txt) or later, as indicated in specific repositories or files on the project github located at https://github.com/Shared-Reality-Lab.

If you incorporate IMAGE code into your own project, but do not want to release your changes and additions consistent with the open source terms under which the IMAGE code is licensed, you may contact us to obtain an alternative license. For all inquiries, please contact us at image@cim.mcgill.ca.

If you are making a contribution to IMAGE, please note that we [require a Contributor License Agreement (CLA)](/CLA.md).
