/*
 * Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 * You should have received a copy of the GNU Affero General Public License
 * and our Additional Terms along with this program.
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.
 */
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

            // White noise burst
            SynthDef((\noiseBurstHOA++(i+1)).asSymbol, { |theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1|
                var sig, encoded;
                sig = WhiteNoise.ar(0.1) * EnvGen.ar( Env.perc, 1, doneAction:2 );
                encoded = HoaEncodeDirection.ar(sig * gain, theta, phi, radius, order.asInteger);
                Out.ar(out, encoded)
            }).store;

            // Ping tone
            SynthDef((\pingHOA++(i+1)).asSymbol, { |freq= 1000, resonz = 0.5, theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1, mix = 0.33, room = 0.5, damp = 0.5|
                var sig, env, envGen, rev, encoded;
                env = Env([0, 1, 0], [0.01, 0.1], [5,-5]);
                envGen =  EnvGen.ar(env, doneAction: 0);
                sig = Ringz.ar( PinkNoise.ar(0.1) * envGen, freq, resonz) * AmpComp.kr(freq, 300);
                rev = FreeVerb.ar(sig, mix: mix, room: room, damp:damp);
                DetectSilence.ar(rev, doneAction:2);
                encoded = HoaEncodeDirection.ar(rev * gain, theta, phi, radius, order.asInteger);
                Out.ar(out, encoded)
            }).store;

            // Moving voice
            // Designed for pie chart sweeps
            SynthDef((\playMovingVoiceHOA++(i+1)).asSymbol,{|freq = 100, blend = 0.5, bright = 0, duration = 3, phi = 0, thetaStart= -0.5pi, thetaEnd=  0.5pi, radius = 1, gain = 1|
                var va = Vowel(\a, \bass),
                    vi = Vowel(\i, \soprano),
                    sig, line, encoded, segduration, env, reverb;
                segduration = ((thetaEnd - thetaStart) / 2pi) * duration;
                env = EnvGen.kr(Env.new([0,1,1,0],[0.01, segduration, 0.01]), 1.0, doneAction: Done.none);
                sig =  BPFStack.ar( Decay.ar(Impulse.ar(freq), 0.01) * PinkNoise.ar(0.9) , va.blend(vi, blend).brightenExp(bright, 1), widthMods: 5 ) * env;
                reverb = FreeVerb.ar(sig, 0.33, 0.9, damp: 0.9, mul: 500);
                encoded = HoaEncodeDirection.ar(reverb *  gain,
                                            Line.ar(thetaStart, thetaEnd, segduration + 0.02),
                                            phi,
                                            2.0,
                                            order.asInteger);
                Out.ar(2,  encoded);
            }).store;

            // Point voice
            // For discrete line graphs
            SynthDef((\playVoicePingHOA++(i+1)).asSymbol, {|freq = 100, blend = 0.5, bright = 0, duration = 0.5, phi = 0, theta = 0, radius = 1, gain = 1|
                var va = Vowel(\a, \bass),
                    vi = Vowel(\i, \bass),
                    sig, encoded, env, partials, excitation, reverb;
                excitation = EnvGen.ar(Env.perc(0.001, duration, 1.0), 1.0, doneAction: Done.none) * PinkNoise.ar(0.1);
                partials = Klank.ar(`[{|i| i+1}!20, nil, {0.4}!20], excitation, freq);
                env = EnvGen.ar(Env.perc(0.001, duration * 3, 1.0), 1.0, doneAction: 2);
                sig = BPFStack.ar(partials, va.blend(vi, blend).brightenExp(bright, 1), widthMods: 5);
                reverb = FreeVerb.ar(sig, 0.5, 0.9, damp: 0.6, mul: 500) * env;
                encoded = HoaEncodeDirection.ar(reverb * gain,
                    theta,
                    phi,
                    2.0,
                    order.asInteger);
                Out.ar(2, encoded);
            }).store;

            // Another point for line graphs
            SynthDef((\discreteRingzPingHOA++(i+1)).asSymbol,{|freq = 200, phi = 0, theta = 0.0, radius = 1, gain = 0.1, decay = 0.02, imp = 48|
                var  sig, encoded, env, excitation, reverb;
                    // excitation =  Dust.ar(100);
                    // partials =  ({|i|SinOsc.ar( (i+1) * freq.lag(0.5) )}!10).sum;
                    env = EnvGen.ar(Env.perc(0.01, 0.01, 1.0, -4),1, doneAction: 2);
                    sig =  Ringz.ar( WhiteNoise.ar(0.05), freq, 10) ;
                    // sig =  Ringz.ar( PinkNoise.ar(0.05) * Decay.ar( Impulse.ar(imp), 0.01) , freq, decay, 0.01 );
                    // reverb = FreeVerb.ar(sig, 0.1, 0.3, damp: 0.6, mul: 1);
                    encoded = HoaEncodeDirection.ar(sig * env * gain,
                                            theta,
                                            phi,
                                            radius,
                                            order.asInteger);
                Out.ar(2,  encoded);
            }).store;

            // Continuous voice
            // For continuous line graphs
            SynthDef((\playVoiceContinuousHOA++(i+1)).asSymbol, {|freq = 200, blend = 0.0, bright = 1, phi = 0, theta = 0.0, radius = 1, gain = 0|
                var va = Vowel(\a, \bass),
                    vi = Vowel(\i, \bass),
                    sig, encoded, env, vow, partials, excitation, reverb;
                partials = LPF.ar(Decay.ar(Impulse.ar(freq.lag(0.5)), 0.01), 10000);
                vow = va.blend(vi, blend).brightenExp(bright, 1);
                sig = BPFStack.ar(partials, vow, widthMods: 0.2);
                encoded = HoaEncodeDirection.ar(sig * gain.lagud(0.5, 0.5),
                    theta,
                    phi,
                    2.0,
                    order.asInteger
                );
                Out.ar(2, encoded);
            }).store;

            // Discrete Sine Pings Length 5 For earcons
            SynthDef((\playDiscreteSinePingHOA++(i+1)).asSymbol, {|note = 80, int0=0, int1=1, int2=1, int3=0, int4=2, phi=0, theta=0, radius=1, gain=0, decay=0.02, imp=48|
                var env1, ping1, env2, ping2, env3, ping3, env4, ping4, env5, ping5, encoded, excitation, reverb, spread=0.05, envDec=0.02, attack=0.01, resonzDecay=3;
                // excitation = Dust.ar(100);
                env1 = EnvGen.ar(Env(levels: [0, 0, 1, 0], times: [0, attack, envDec], curve: [1, 8, -9]), 1, doneAction: Done.none);
                //sig = PinkNoise.ar(0.1);
                ping1 = Ringz.ar(env1 * PinkNoise.ar(0.1), (note + int0).midicps, resonzDecay,  AmpComp.kr((note + int0).midicps, 200));
                DetectSilence.ar(ping1, doneAction: Done.freeSelf);
                env2 = EnvGen.ar(Env(levels: [0, 0, 1, 0], times: [spread *1, attack, envDec], curve: [1, 8, -9]), 1, doneAction: Done.none);
                ping2 = Ringz.ar(env2 * PinkNoise.ar(0.1), (note + int1).midicps, resonzDecay,  AmpComp.kr((note + int1).midicps, 200));
                DetectSilence.ar(ping2, doneAction: Done.freeSelf);
                env3 = EnvGen.ar(Env(levels: [0, 0, 1, 0], times: [spread *2, attack, envDec], curve: [1, 8, -9]), 1, doneAction: Done.none);
                ping3 = Ringz.ar(env3 * PinkNoise.ar(0.1), (note + int2).midicps, resonzDecay,  AmpComp.kr((note + int2).midicps, 200));
                DetectSilence.ar(ping3, doneAction: Done.freeSelf);
                env4 = EnvGen.ar(Env(levels: [0, 0, 1, 0], times: [spread *3, attack, envDec], curve: [1, 8, -9]), 1, doneAction: Done.none);
                ping4 = Ringz.ar(env4 * PinkNoise.ar(0.1), (note + int3).midicps, resonzDecay,  AmpComp.kr((note + int3).midicps, 200));
                DetectSilence.ar(ping4, doneAction: Done.freeSelf);
                env5 = EnvGen.ar(Env(levels: [0, 0, 1, 0], times: [spread *4, attack, envDec], curve: [1, 8, -9]), 1, doneAction: Done.none);
                ping5 = Ringz.ar(env5 * PinkNoise.ar(0.1), (note + int4).midicps, resonzDecay,  AmpComp.kr((note + int4).midicps, 200));
                DetectSilence.ar(ping5, doneAction: Done.freeSelf);
                // reverb = FreeVerb.ar(sig, 0.1, 0.3, damp: 0.5, mul: 1);
                encoded = HoaEncodeDirection.ar((ping1 + ping2 + ping3 + ping4 + ping5) * gain,
                    theta,
                    phi,
                    2.0,
                    order.asInteger
                );
                Out.ar(2, encoded);
            }).store;

            // Continuous noise for pie charts v2 from Florian
            SynthDef((\playContinuousResonzNoiseHOA++(i+1)).asSymbol, { |freq = 200, phi = 0, theta = 0, radius = 2, gain = 0, decay = 0.02, imp = 48, lag = 10|
              var sig, encoded, reverb;
              sig = Ringz.ar(PinkNoise.ar(0.05) * Decay2.ar(Impulse.ar(imp), 0.03, 0.1), freq, decay, 0.01) * AmpComp.kr(freq, 200);
              reverb = FreeVerb.ar(sig, 0.1, 0.3, damp: 0.6, mul: 500);
              encoded = HoaEncodeDirection.ar(reverb * gain.lagud(lag, lag),
                theta,
                phi,
                radius,
                order.asInteger
              );
              Out.ar(2, encoded);
            }).store;
        });


        // Buffer Playback
        // Stereo Buffer
        SynthDef(\playBufferStereo,{ |buffNum = 0, start = 0, duration = 1, out = 0, stereoPos = 0.0, gain = 1|
            var sig;
            sig = PlayBuf.ar(1, bufnum: buffNum, rate: BufRateScale.kr(buffNum), trigger: 1, startPos: start) *
            EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
            Out.ar(out, Pan2.ar(sig * gain, stereoPos))
        }).store;

        // Ambisonics Buffers Playback
        5.do({|i|
            var order = i+1;
            SynthDef((\playBufferHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1, theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1|
                var sig, encoded;
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: BufRateScale.kr(buffNum), trigger: 1, startPos: start) *  EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
                encoded = HoaEncodeDirection.ar(sig * gain, theta, phi, radius, order.asInteger);
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
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: BufRateScale.kr(buffNum), trigger: 1, startPos: start) *  EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
                sig = FreeVerb.ar(sig, mix: mix, room: room, damp: damp);
                encoded = HoaEncodeDirection.ar(sig * gain, theta, phi, radius, order.asInteger);
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
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: BufRateScale.kr(buffNum), trigger: 1, startPos: start) *
                EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
                encoded = HoaEncodeDirection.ar(sig * gain, Line.ar(thetaStart, thetaStop, duration),
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
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: BufRateScale.kr(buffNum), trigger: 1, startPos: start) *
                EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;

                sig = FreeVerb.ar(sig, mix: 0.33, room: 0.5, damp:0.5);
                encoded = HoaEncodeDirection.ar(sig * gain, Line.ar(thetaStart, thetaStop, duration),
                    Line.ar(phiStart, phiStop, duration),
                    Line.ar(radiusStart, radiusStop, duration),
                    order.asInteger);
                Out.ar(out, encoded)
            }).store;

            // Play buffer for segmentations
            SynthDef((\playBuffer4SegmentHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0,
                theta = 0.0pi, phi = 0.0pi, radius = 2.5,
                out = 2, gain = 0, lag = 0.1|
                var sig, encoded;
                sig = PlayBuf.ar(1, bufnum: buffNum, rate: BufRateScale.kr(buffNum), trigger: 1, startPos: start, loop: 1);
                encoded = HoaEncodeDirection.ar(sig, theta.lag(lag),
                    phi.lag(lag),
                    radius.lag(lag),
                    order.asInteger);
                Out.ar(out, encoded * gain.lag(lag))
            }).store;

            // Play klank for segmentations
            SynthDef((\playKlankNoise4SegmentHOA++(i+1)).asSymbol, { |midinote = 60,
                                                                      theta = 0.0pi, phi = 0.0pi, radius = 2.5,
                                                                      out = 2, gain = 0, lag = 0.1, release=0.5, gate=1|
            var sig, encoded, env, envGen;
                env = Env.asr(releaseTime: release);
                envGen = EnvGen.ar(env, gate);
                sig = Klank.ar(`[{|i|  (i+1) + 0.01.rand2 }!18, {|i| 1/(i+1) }!18, {|i| 2/(i+1) }!18], BrownNoise.ar(0.001) + Dust.ar(50, 0.5) , midinote.midicps  ) * envGen * AmpComp.kr(midinote.midicps, 300);
                DetectSilence.ar(sig, doneAction: Done.freeSelf);
                encoded = HoaEncodeDirection.ar(sig* gain.lag(lag), theta.lag(lag),
                                                     phi.lag(lag),
                                                     radius.lag(lag),
                                                     order.asInteger);
                Out.ar(out, encoded)
            }).store;
        });
    }

    // load and parse a JSON file as a dictionary
    // *loadJSON { |path|
    //     var res = nil;
    //     if(File.exists(path.standardizePath),
    //         {
    //             File.use(path, "r", { |f|
    //                 var jsonData;
    //                 jsonData = f.readAllString;
    //                 res = jsonData.parseYAML;
    //             });
    //         },
    //         {
    //             ("Could not open a JSON file at "++path++"!").postln;
    //         }
    //     );
    //     ^res
    // }

    // *loadSound { |path|
    //     var res = nil;
    //     if(File.exists(path),
    //         {
    //             SoundFile.use(path, { |f|
    //                 res = f;
    //             });
    //         },
    //         {
    //             ("Could not open a sound file at "++path++"!").postln;
    //         }
    //     );
    //     ^res
    // }

    *loadTTSJSON { |path|
        var jsonData, soundFile;
        //jsonData = this.loadJSON(path);
        jsonData = path.standardizePath.parseJSONFile;
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

        //soundFile = this.loadSound(jsonData.at("ttsFileName"));
        soundFile = SoundFile.openRead(jsonData.at("ttsFileName").standardizePath);
        if(soundFile.isNil,
            {
                Error("Failed to load sound file at %!".format(jsonData.at("ttsFileName"))).throw;
            }
        );
        ^[
            jsonData,
            soundFile
        ]
    }

    *newScore { |order = 3, busOffset = 2|
        var score;
        score = Score.new;
        HOABinaural.loadbinauralIRs4Score2(score, order, 0);
        ^score
    }

    *mapCoords { |x, y|
        var theta, phi;
        theta = x.linlin(0, 1, -0.45pi, 0.45pi);
        phi = y.linlin(0, 1, 0.35pi, -0.35pi);
        ^[ theta, phi ]
    }
}

/**
 * More than one repsonder/renderer
 * loadTTSJSON
 * function to open score and prep (load assets for binaural filters, buffers etc. include options)
 * HandlerOptions?
*/
