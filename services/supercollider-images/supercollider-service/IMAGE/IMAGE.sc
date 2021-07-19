// IMAGE class


IMAGE {
    // load and parse a JSON file as a dictionary
    *loadJSON { |path = nil|
        var res = nil, realPath = nil;
        realPath = File.realpath(path);
        if(File.exists(realPath),
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

    *loadTTSJSON { |path = nil|
        var jsonData, soundFile;
        jsonData = this.loadJSON(path);
        if(jsonData.isNil,
            {
                Error("Failed to load JSON file at %!".format(path)).throw;
            }
        );

        if(jsonData.at("ttsFileName").isNil,
            {
                Error("JSON data does not include a key at 'ttsFileName'!").throw;
            }
        );

        soundFile = this.loadSound(jsonData.at("ttsFileName"));
        if(soundFile.isNil,
            {
                Error("Failed to load sound file at %!".format(jsonData.at("ttsFileName"))).throw;
            }
        );
        ^Dictionary.newFrom([
            \jsonData, jsonData,
            \soundFile, soundFile
        ])
    }
}

/**
 * More than one repsonder/renderer
 * loadTTSJSON
 * function to open score and prep (load assets for binaural filters, buffers etc. include options)
 * HandlerOptions?
*/