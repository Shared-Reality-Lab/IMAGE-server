
```
git clone https://github.com/namdar-nejad/IMAGE-server.git
cd IMAGE-server
git checkout docker-debugging
git submodule init
git submodule update --remote
cp /home/juliette/Documents/IMAGE-server/config/* ./config/
docker-compose -f build.yml build ner 
docker-compose up -d orchestrator ner 
cp /home/namdarn/testinput.json ./
/var/docker/image/bin/sendimagereq ./testinput.json http://192.168.224.3:8080/render/preprocess
```

Current problem that I'm facing:
A problem with the chrome drive, which I haven't been able to figure out yet. Even with bypassing this, I had a few problems with the imports and dependencies, whhich makes me think there's a problem with my Dockerfile, even though I've been trouble shooting I'm not sure what the problme exactly is.
```
Failed to move to new namespace: PID namespaces supported, Network namespace supported, but failed: errno = Operation not permitted
```


# IMAGE-server
IMAGE server components, including Handlers

## IMAGE project information
Please see https://image.a11y.mcgill.ca for general information about the project.

If you wish to contribute to the project, the following wiki page is a good starting point, including for those on the IMAGE project team:
https://github.com/Shared-Reality-Lab/IMAGE-server/wiki

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
