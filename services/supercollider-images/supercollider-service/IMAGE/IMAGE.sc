// IMAGE class


IMAGE {
    // stores compiled SynthDefs so they're accessible in NRT
    *storeSynthDefs {
        // Stereo limiter
        SynthDef(\limiterStereo,{ |level = 0.9, dur = 0.2, in = 0, out = 0|
            var sig;
            sig = In.ar(in, 2);
            Out.ar(out, sig * 0.1)
        }).store;

        // Ambisonic SynthDefs at orders 1-5
        5.do({|i|
	         var order = i+1;
	         SynthDef((\binauralDecodeNrt++(i+1)).asSymbol, { |in= 0, out=0|
	         var decoded, limited;
		     decoded = HOABinaural.ar4Score(order, In.ar(in, (order+1).pow(2).asInteger ));
		     limited = [Limiter.ar(decoded[0], 0.9, 0.001), Limiter.ar(decoded[1], 0.9, 0.001)];
	         Out.ar(out, limited)
           }).store;
           });

            // White noise burst
            SynthDef((\noiseBurstHOA++(i+1)).asSymbol, { |theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1|
                var sig, encoded;
                sig = WhiteNoise.ar(0.1) * EnvGen.ar( Env.perc, 1, doneAction:2 );
                encoded = HoaEncodeDirection.ar(sig, theta, phi, radius, order.asInteger);
                Out.ar(out, encoded)
            }).store;

            // Ping tone
            SynthDef((\pingHOA++(i+1)).asSymbol, { |freq= 1000, resonz = 0.5, theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1, mix = 0.33, room = 0.5, damp = 0.5|
                var sig, env, envGen, rev, encoded;
                env = Env([0, 1, 0], [0.01, 0.1], [5,-5]);
                envGen =  EnvGen.ar(env, doneAction: 0);
                sig = Ringz.ar( WhiteNoise.ar(0.1) * envGen, freq, resonz) * AmpComp.kr(freq, 300);
                rev = FreeVerb.ar(sig, mix: mix, room: room, damp:damp);
                DetectSilence.ar(rev, doneAction:2);
                encoded = HoaEncodeDirection.ar(rev, theta, phi, radius, order.asInteger);
                Out.ar(out, encoded * gain)
            }).store;
        });

        // Buffer Playback
        // Stereo Buffer
        SynthDef(\playBufferStereo,{ |buffNum = 0, start = 0, duration = 1, out = 0, stereoPos = 0.0, gain = 1|
            var sig;
            sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *
            EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
            Out.ar(out, Pan2.ar(sig, stereoPos))
        }).store;

        // Ambisonics Buffers
        5.do({|i|
            var order = i+1;
            SynthDef((\playBufferHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1, theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1|
                var sig, encoded;
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *  EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
                encoded = HoaEncodeDirection.ar(sig, theta, phi, radius, order.asInteger);
                Out.ar(out, encoded)
            }).store;

            SynthDef((\playBufferReverbHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1,
                theta = 0.0,
                phi = 0.0,
                radius = 1.5,
                mix = 0.33,
                room = 0.5,
                damp = 0.5,
                out = 2, gain = 1|
                var sig, encoded;
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *  EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
                sig = FreeVerb.ar(sig, mix: mix, room: room, damp: damp);
                encoded = HoaEncodeDirection.ar(sig, theta, phi, radius, order.asInteger);
                Out.ar(out, encoded)
            }).store;
        });

        // Buffers with movement effect
        5.do({|i|
            var order = i+1;
            SynthDef((\playBufferLinearMoveHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1,
                thetaStart = 0.5pi, thetaStop = -0.5pi,
                phiStart = 0.25pi, phiStop = -0.25pi,
                radiusStart = 2.5, radiusStop = 0.5,
                out = 2, gain = 1|
                var sig, encoded;
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *
                EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
                encoded = HoaEncodeDirection.ar(sig, Line.ar(thetaStart, thetaStop, duration),
                    Line.ar(phiStart, phiStop, duration),
                    Line.ar(radiusStart, radiusStop, duration),
                    order.asInteger);
                Out.ar(out, encoded)
            }).store;

            SynthDef((\playBufferLinearMoveReverbHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1,
                thetaStart = 0.5pi, thetaStop = -0.5pi,
                phiStart = 0.25pi, phiStop = -0.25pi,
                radiusStart = 2.5, radiusStop = 0.5,
                mix = 0.33,
                room = 0.5,
                damp = 0.5,
                out = 2, gain = 1|
                var sig, encoded;
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *
                EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;

                sig = FreeVerb.ar(sig, mix: 0.33, room: 0.5, damp:0.5);
                encoded = HoaEncodeDirection.ar(sig, Line.ar(thetaStart, thetaStop, duration),
                    Line.ar(phiStart, phiStop, duration),
                    Line.ar(radiusStart, radiusStop, duration),
                    order.asInteger);
                Out.ar(out, encoded)
            }).store;
        });
    }

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

    *newScore { |order = 3, busOffset = 2|
        var score;
        score = Score.new;
        HOABinaural.loadbinauralIRs4Score2(score, order, 0);
        ^score
    }
}

/**
 * More than one repsonder/renderer
 * loadTTSJSON
 * function to open score and prep (load assets for binaural filters, buffers etc. include options)
 * HandlerOptions?
*/