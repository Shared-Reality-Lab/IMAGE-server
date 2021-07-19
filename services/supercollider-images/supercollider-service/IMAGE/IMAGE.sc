// IMAGE class


IMAGE {
    // load and parse a JSON file as a dictionary
    *loadJSON { |path = nil|
        var res = nil;
        if(File.exists(path),
            {
                File.use(path, "r", { |f|
                    var jsonData;
                    jsonData = f.readAllString;
                    res = jsonData.parseYAML;
                });
            },
            {
                ("Could not open a JSON file at "++path++"!").postln;
            }
        );
        ^res
    }

    *loadSound { |path = nil|
        var res = nil;
        if(File.exists(path),
            {
                SoundFile.use(path, { |f|
                    res = f;
                });
            },
            {
                ("Could not open a sound file at "++path++"!").postln;
            }
        );
        ^res
    }
}