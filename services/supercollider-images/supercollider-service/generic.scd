(
~loadJSON = { |path|
    var res = nil;
    if(File.exists(path),
        {
            File.use(path, "r", { |f|
                var jsonData;
                jsonData = f.readAllString;
                res = jsonData.parseYAML;
            });
            "Read file successfully.".postln;
        },
        { "Could not open the file :(".postln; }
    );
    res
};

~loadSound = { |path|
    var res = nil;
    if(File.exists(path),
        {
            SoundFile.use(path, { |f|
                res = f;
            });
        },
        { "Could not open the file :(".postln; }
    );
    res
};

~renderGeneric = { |json, ttsData, outPath, addr|
    var score, timing, serv;
    timing = 0;
    serv = Server(
        \nrtGeneric,
        options: ServerOptions.new.numOutputBusChannels_(2)
    );
    score = Score.new;

    // Add necessary synthdefs to server
    score.add([
        timing,
        ['/d_recv',
            // Play mono audio buffer in stereo
            SynthDef(\player, { |out=0, bufnum|
                Out.ar(out,
                    PlayBuf.ar(
                        1,
                        bufnum,
                        BufRateScale.kr(bufnum)
                    )!2
                );
            }).asBytes
        ]
    ]);
    score.add([
        timing,
        ['/d_recv',
            // Play mono audio with x-axis pan
            SynthDef(\panplayer, { |out=0, bufnum, pos=0.5|
                Out.ar(
                    out,
                    Pan2.ar(
                        PlayBuf.ar(
                            1,
                            bufnum,
                            BufRateScale.kr(bufnum)
                        ),
                        (pos - 0.5) * 2.0
                    )
                );
            }).asBytes
        ]
    ]);

    // Scene intro if any
    if(json.at("audioTemplate").at("intro") != nil,
        {
            var intro = json.at("audioTemplate").at("intro");
            score.add([
                timing,
                (b = Buffer(serv)).allocReadMsg(ttsData.path, intro.at("offset"), intro.at("duration"))
            ]);
            score.add([
                timing,
                (s = Synth.basicNew(\player, serv)).newMsg(args: ['bufnum', b.bufnum])
            ]);
            timing = timing + (intro.at("duration").asInteger / ttsData.sampleRate);
            score.add([timing, b.freeMsg]);
            score.add([timing, s.freeMsg]);
        }
    );

    // Iterate over objects (currently unsorted)
    json.at("objects").do({ |item, i|
        var audio, xCent;
        // Play and before last item
        if(i + 1 == json.at("objects").size,
            {
                var and;
                and = json.at("audioTemplate")
                .at("joining")
                .at("and");
                score.add([
                    timing,
                    (b = Buffer(serv)).allocReadMsg(
                        ttsData.path,
                        and.at("offset");
                        and.at("duration")
                    )
                ]);
                score.add([
                    timing,
                    (s = Synth.basicNew(\player, serv)).newMsg(args: ['bufnum', b.bufnum])
                ]);
                timing = timing + (and.at("duration").asInteger / ttsData.sampleRate);
                score.add([timing, b.freeMsg]);
                score.add([timing, s.freeMsg]);
            }
        );
        audio = item.at("offset");
        score.add([
            timing,
            (b = Buffer(serv)).allocReadMsg(ttsData.path, audio.at("offset"), audio.at("duration"))
        ]);
        xCent = item.at("centroid").at(0).asFloat;
        score.add([
            timing,
            (s = Synth.basicNew(\panplayer, serv)).newMsg(
                args: [
                    'bufnum', b.bufnum,
                    'pos', xCent
                ]
            )
        ]);
        timing = timing + (audio.at("duration").asInteger / ttsData.sampleRate);
        score.add([timing, b.freeMsg]);
        score.add([timing, s.freeMsg]);
    });

    // Write file
    score.recordNRT(
        nil,
        outPath,
        options: serv.options,
        action: {
            // Check for successful write (file exists)
            serv.remove;
            if(File.exists(outPath),
                { addr.sendMsg(\status, \done); },
                {
                    "Failed to write file!".postln;
                    addr.sendMsg(\status, \fail);
                }
            );
            "Done".postln;
        }
    );
};

OSCdef.newMatching(\genericObject, { |msg, time, addr, recvPort|
    var json, ttsData;
    json = ~loadJSON.(msg.at(1).asString);
    ttsData = ~loadSound.(msg.at(2).asString);
    if(json.notNil && ttsData.notNil,
        {
            ~renderGeneric.(
                json: json,
                ttsData: ttsData,
                outPath: msg.at(3).asString,
                addr: addr
            );
        },
        { addr.sendMsg(\status, \fail); }
    );
}, '/render/genericObject', nil);
)

(
m = NetAddr("127.0.0.1", 57120);
m.sendMsg("/render/genericObject", "/home/juliette/Documents/ATP Misc/demo2/generic-tts-handler-1625056971430.json", "/home/juliette/Documents/ATP Misc/demo2/generic-tts-handler-1625056971429.wav", "/home/OSCTEST.wav");
)