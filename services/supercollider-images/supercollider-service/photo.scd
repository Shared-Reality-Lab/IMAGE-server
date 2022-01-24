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
var renderPhoto;
"Photo Audio Rendering".postln;
renderPhoto = { |json, ttsData, outPath, addr|
    var score, timing, order=5, parts, segmentInfo=Array.new, baseGain=0.1;
    timing = 0;
    score = IMAGE.newScore(order);

    // Set up b-format decoder
    score.add([
        timing,
        [\s_new, (\binauralDecodeNrt++order.asSymbol).asSymbol, 1001, 0, 1, \in, 2]
    ]);

    // Load TTS buffer
    score.add([
        timing,
        [\b_allocRead, 210, ttsData.path, 0, 0]
    ]);

    // TODO the rendering
    json.postln;
    parts = json.at("data");
    parts.do({ |item|
        var type = item.at("type"), audio = item.at("audio");
        switch(type.asSymbol,
            \text, {
                var duration = (audio.at("duration").asInteger / ttsData.sampleRate);
                "Text".postln;
                // Play non-spatialized audio
                score.add([
                    timing,
                    [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, audio.at("offset").asInteger, \duration, duration, \gain, baseGain]
                ]);
                timing = timing + duration;
            },
            \object, {
                var duration = (audio.at("duration").asInteger / ttsData.sampleRate), objects = item.at("objects");
                // Play TTS label (spatialized) and ping(s)
                "Object".postln;
                score.add([
                    timing,
                    [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, audio.at("offset").asInteger, \duration, duration, \gain, baseGain]
                ]);
                timing = timing + duration;

                // Sort objects within group left-to-right
                objects.sort({ |a, b|
                    var xa, xb;
                    xa = a.at("centroid").at(0).asFloat;
                    xb = b.at("centroid").at(0).asFloat;
                    xa < xb
                });
                objects.do({ |point|
                    var totalDur = 2;
                    if(point.at("centroid").notNil,
                        {
                            var dur, theta, phi, volume;
                            # theta, phi = IMAGE.mapCoords(
                                point.at("centroid").at(0).asFloat,
                                point.at("centroid").at(1).asFloat
                            );
                            dur = point.at("centroid").at(0).asFloat.linlin(0.0, 1.0, 0.0, totalDur);
                            volume = point.at("area").asFloat.linlin(0, 0.25, -5, 0);
                            score.add([
                                (timing + dur),
                                [\s_new, (\pingHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                                    \gain, baseGain * volume.dbamp,
                                    \room, 0.6,
                                    \damp, 0.5,
                                    \mix, 0.3,
                                    \freq, point.at("centroid").at(1).asFloat.linlin(0.0, 1.0, 2000, 1000),
                                    \resonz, 0.01,
                                    \theta, theta,
                                    \phi, phi]
                            ]);
                        },
                        { "No centroid on item :(".postln; }
                    );
                });
                timing = timing + 2.25;
            },
            \segment, {
                var duration = (audio.at("duration").asInteger / ttsData.sampleRate), coord = item.at("coord"), area = item.at("area").asFloat, maxTime=25, totalTime=maxTime*area, pingDur=0.001, midinote;
                // TTS and then segment outline
                "segment".postln;
                score.add([
                    timing,
                    [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, audio.at("offset").asInteger, \duration, duration, \gain, baseGain]
                ]);
                timing = timing + duration;

                coord = coord.resamp0((totalTime / pingDur).asInteger);
                midinote = item.at("centroid").at(1).asFloat.linlin(0.0, 1.0, 57, 45).round;
                score.add([
                    timing,
                    [\s_new, (\playKlankNoise4SegmentHOA++order.asSymbol).asSymbol, 1003, 2, 1001, \midinote, midinote, \lag, pingDur, \gain, baseGain * -20.dbamp]
                ]);
                coord.do({ |point|
                    var x, y, theta, phi;
                    x = point.at(0).asFloat;
                    y = point.at(1).asFloat;
                    # theta, phi = IMAGE.mapCoords(x, y);
                    score.add([
                        timing,
                        [\n_set, 1003, \theta, theta, \phi, phi]
                    ]);
                    timing = timing + pingDur;
                });
                score.add([timing, [\n_set, 1003, \gain, 0.0]]);
                score.add([timing, [\n_free, 1003]]);
            },
            { ("Unknown input of type '" + type.asString + "'! Skipping.").postln; }
        );
    });

    // Add one last noop message
    score.add([timing, [0]]);
    score.saveToFile("/tmp/sc-store/score.txt");

    // Write file
    score.recordNRT(
        nil,
        outPath,
        sampleRate: 48000,
        headerFormat: "FLAC",
        sampleFormat: "int16",
        options: ServerOptions.new.numOutputBusChannels_(2).verbosity_(-1),
        action: {
            // Check for successful write (file exists)
            if(File.exists(outPath),
                { addr.sendMsg(\status, \done, *segmentInfo); },
                {
                    "Failed to write file in NRT!".postln;
                    addr.sendMsg(\status, \fail);
                }
            );
            "Done (Photo Rendering)".postln;
        }
    );
};

OSCdef.newMatching(\photoAudio, { |msg, time, addr, recvPort|
    var json = nil, ttsData = nil;
    "Received a message at /render/photo...".postln;
    # json, ttsData = IMAGE.loadTTSJSON(msg.at(1).asString);
    if(json.notNil && ttsData.notNil,
        {
            try {
                "Trying to render...".postln;
                renderPhoto.(
                    json: json,
                    ttsData: ttsData,
                    outPath: msg.at(2).asString,
                    addr: addr
                );
            } { |error|
                error.what.postln;
                addr.sendMsg(\status, \fail);
                error.throw;
            }
        },
        {
            "JSON or TTS data nil!".postln;
            if(json.isNil, { "JSON is nil.".postln; });
            if(ttsData.isNil, { " TTS data is nil.".postln; });
            addr.sendMsg(\status, \fail);
        }
    );
}, '/render/photo', nil);
