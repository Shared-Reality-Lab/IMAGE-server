Beta quality: Useful enough for testing by end-users.

This preprocessor has been created in order to make sense of the outputs generated by object detection preprocessor. The object detection just detects the objects and sends them back in a json format. The sorting preprocessor arranges these objects in 3 different categories namely:

```
1. Left to Right
2. Top to Bottom
3. Small to Big
```

In order to run the API as a docker container use the following commands: 

```docker build -t <image-name>```

```docker run --publish <port>:5000 <image-name>```

Appropriate comments have also been added to ```sorting.py```.
