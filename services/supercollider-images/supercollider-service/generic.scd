var loadJSON, loadSound, renderGeneric;
"Generic Object Description".postln;
loadJSON = { |path|
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

loadSound = { |path|
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

renderGeneric = { |json, ttsData, outPath, addr|
    var score, timing, serv, objects, groupedObjIds, bonkDur;
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
    score.add([
        timing,
        ['/d_recv',
            // FM Synth for a bonk
            SynthDef(\bonk, { |freq=220, nc=3, nm=2, idx=2, amp=0.5, out=0, pos=0.5|
                var mod, car, env, mEnv;
                env = EnvGen.kr(Env.perc(attackTime: 0.01, releaseTime: 0.75, curve: -12), doneAction: Done.freeSelf);
                mEnv = EnvGen.kr(Env([idx, idx*0.5, idx], [0.01, 0.75]));
                mod = SinOsc.ar(freq * nm, mul: freq * nm * idx * mEnv);
                car = SinOsc.ar(freq * nc + mod, mul: amp * env);
                Out.ar(out, Pan2.ar(car, (pos - 0.5) * 2.0));
            }).asBytes
        ]
    ]);
    bonkDur = 0.76;

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
    objects = json.at("objects");
    groupedObjIds = Array.new;
    json.at("groups").do({ |item, i|
        item.at("IDs").postln;
    });
    // First do groups
    json.at("groups").do({ |item, i|
        var audio, objs, objIds;
        objIds = Array.new;
        item.at("IDs").do({ |it|
            groupedObjIds = groupedObjIds.add(it.asInteger);
            objIds = objIds.add(it.asInteger);
        });
        audio = item.at("audio");
        score.add([
            timing,
            (b = Buffer(serv)).allocReadMsg(
                ttsData.path,
                audio.at("offset"),
                audio.at("duration")
            )
        ]);
        score.add([
            timing,
            (s = Synth.basicNew(\player, serv)).newMsg(args: ['bufnum', b.bufnum])
        ]);
        timing = timing + (audio.at("duration").asInteger / ttsData.sampleRate);
        score.add([timing, b.freeMsg]);
        score.add([timing, s.freeMsg]);

        objs = objects.select({ |item, i|
            objIds.includes(item.at("ID").asInteger)
        });

        // Bonks
        objs.do({ |item|
            if(item.at("centroid").notNil,
                {
                    score.add([
                        timing,
                        (s = Synth.basicNew(\bonk, serv)).newMsg(
                            args: ['pos', item.at("centroid").at(0).asFloat]
                        )
                    ]);
                    timing = timing + bonkDur;
                },
                { "No centroid on item :(".postln; }
            );
        });
    });
    "Grouped Objects".postln;
    groupedObjIds.at(0).postln;
    // Remove objects handled by groups
    objects.takeThese({ |item, i|
        groupedObjIds.includes(item.at("ID").asInteger)
    }).postln;

    // Now do remaining objects
    objects.do({ |item, i|
        var audio, xCent;
        // ("Object no. "++i).postln;
        // Play and before last item
        if((i + 1 == objects.size) && (objects.size > 1),
            {
                var and;
                and = json.at("audioTemplate")
                .at("joining")
                .at("and");
                score.add([
                    timing,
                    (j = Buffer(serv)).allocReadMsg(
                        ttsData.path,
                        and.at("offset"),
                        and.at("duration")
                    )
                ]);
                score.add([
                    timing,
                    (k = Synth.basicNew(\player, serv)).newMsg(args: ['bufnum', b.bufnum])
                ]);
                timing = timing + (and.at("duration").asInteger / ttsData.sampleRate);
                score.add([timing, j.freeMsg]);
                score.add([timing, k.freeMsg]);
            }
        );
        audio = item.at("audio");
        score.add([
            timing,
            (b = Buffer(serv)).allocReadMsg(ttsData.path, audio.at("offset"), audio.at("duration"))
        ]);
        if(item.at("centroid").notNil,
            {
                xCent = item.at("centroid").at(0).asFloat;
                // ("Centroid: "++xCent).postln;
                score.add([
                    timing,
                    (s = Synth.basicNew(\panplayer, serv)).newMsg(
                        args: [
                            'bufnum', b.bufnum,
                            'pos', xCent
                        ]
                    )
                ]);
            },
            {
                score.add([
                    timing,
                    (s = Synth.basicNew(\player, serv)).newMsg(
                        args: [
                            'bufnum', b.bufnum,
                        ]
                    )
                ]);
            }
        );
        timing = timing + (audio.at("duration").asInteger / ttsData.sampleRate);
        score.add([timing, b.freeMsg]);
        score.add([timing, s.freeMsg]);
    });

    // Add one last noop msg
    score.add([timing, [0]]);

    // Write file
    score.recordNRT(
        nil,
        outPath,
        headerFormat: "WAV",
        sampleFormat: "int16",
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
    var json = nil, ttsData = nil;
    "Received a message at /render/genericObject...".postln;
    json = loadJSON.(msg.at(1).asString);
    json.postln;
    if(json.notNil,
        {
            if(json.at("ttsFileName").notNil,
                {
                    ttsData = loadSound.(json.at("ttsFileName").asString);
                }
            );
        }
    );
    if(json.notNil && ttsData.notNil,
        {
            try {
                renderGeneric.(
                    json: json,
                    ttsData: ttsData,
                    outPath: msg.at(2).asString,
                    addr: addr
                );
            } { |error|
                addr.sendMsg(\status, \fail);
                error.throw;
            }
        },
        { addr.sendMsg(\status, \fail); }
    );
}, '/render/genericObject', nil);