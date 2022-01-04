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
 * If not, see <https://github.com/Shared-Reality-Lab/auditory-haptic-graphics-server/LICENSE>.
 */

var renderGeneric;
"Generic Object Description".postln;
renderGeneric = { |json, ttsData, outPath, addr|
    var score, timing, order=5, objects, groupedObjIds, maxArea=0;
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

    "Set up done. Starting intro...".postln;

    // Scene intro if any
    if(json.at("audioTemplate").at("intro") != nil,
        {
            var intro = json.at("audioTemplate").at("intro"), duration;
            duration = (intro.at("duration").asInteger / ttsData.sampleRate);
            score.add([
                timing,
                [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, intro.at("offset"), \duration, duration]
            ]);
            timing = timing + duration;
        }
    );

    // Iterate over objects (currently unsorted)
    objects = json.at("objects");
    // Determine maximum area of an object
    objects.do({ |item|
        if(item.at("area").asFloat > maxArea,
            {
                maxArea = item.at("area").asFloat;
            }
        );
    });
    ("Max Area: " + maxArea.asString).postln;
    groupedObjIds = Array.new;
    json.at("groups").do({ |item, i|
        item.at("IDs").postln;
    });
    // First do groups
    json.at("groups").do({ |item, i|
        var audio, duration, objs, objIds;
        objIds = Array.new;
        item.at("IDs").do({ |it|
            groupedObjIds = groupedObjIds.add(it.asInteger);
            objIds = objIds.add(it.asInteger);
        });
        audio = item.at("audio");
        duration = (audio.at("duration").asInteger / ttsData.sampleRate);

        score.add([
            timing,
            [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, audio.at("offset").asInteger.asInteger, \duration, duration]
        ]);

        timing = timing + duration;

        objs = objects.select({ |item, i|
            objIds.includes(item.at("ID").asInteger)
        });

        // Sort objects within group left to right.
        // Later on, other options should be available and checked.
        objs.sort({ |a, b|
            var xa, xb;
            xa = a.at("centroid").at(0).asFloat;
            xb = b.at("centroid").at(0).asFloat;
            xa < xb
        });

        // Bonks
        objs.do({ |item|
            var totalDur = 2;
            if(item.at("centroid").notNil,
                {
                    var dur, theta, phi, volume;
                    //var dur = 0.25, theta, phi;
                    # theta, phi = IMAGE.mapCoords(
                        item.at("centroid").at(0).asFloat,
                        item.at("centroid").at(1).asFloat
                    );
                    dur = item.at("centroid").at(0).asFloat.linlin(0.0, 1.0, 0.0, totalDur);
                    volume = item.at("area").asFloat.linlin(0, maxArea, -10, 0);
                    score.add([
                        (timing + dur),
                        [\s_new, (\pingHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                            \gain, 0.8 * volume.dbamp,
                            \room, 0.6,
                            \damp, 0.5,
                            \mix, 0.3,
                            \freq, item.at("centroid").at(1).asFloat.linlin(0.0, 1.0, 2000, 1000),
                            \resonz, 0.01,
                            \theta, theta,
                            \phi, phi]
                    ]);
                },
                { "No centroid on item :(".postln; }
            );
        });
        timing = timing + 2.25;
    });
    "Grouped Objects".postln;
    groupedObjIds.at(0).postln;
    // Remove objects handled by groups
    objects.takeThese({ |item, i|
        groupedObjIds.includes(item.at("ID").asInteger)
    });

    // Now do remaining objects
    objects.do({ |item, i|
        var audio, xCent, dur, volume;
        // ("Object no. "++i).postln;
        // Play and before last item
        if((i + 1 == objects.size) && (objects.size > 1),
            {
                var and, duration;
                and = json.at("audioTemplate")
                .at("joining")
                .at("and");
                duration = (and.at("duration").asInteger / ttsData.sampleRate);
                score.add([
                    timing,
                    [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, and.at("offset").asInteger, \duration, duration, \gain, 1]
                ]);
                timing = timing + duration;
            }
        );
        audio = item.at("audio");
        dur = (audio.at("duration").asInteger / ttsData.sampleRate);
        volume = item.at("area").asFloat.linlin(0, maxArea, -10, 0);
        if(item.at("centroid").notNil,
            {
                var theta, phi;
                # theta, phi = IMAGE.mapCoords(
                    item.at("centroid").at(0).asFloat,
                    item.at("centroid").at(1).asFloat
                );
                score.add([
                    timing,
                    [\s_new, (\playBufferHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                        \buffNum, 210,
                        \start, audio.at("offset").asInteger,
                        \duration, dur,
                        \theta, theta,
                        \phi, phi,
                        \gain, 0.5 * volume.dbamp
                    ]
                ]);
            },
            {
                "No centroid on item!".postln;
                score.add([
                    timing,
                    [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, audio.at("offset").asInteger, \duration, dur, \gain, 0.8 * volume.dbamp]
                ]);
            }
        );
        timing = timing + dur;
    });

    // Add one last noop msg w/ half second pause
    timing = timing + 0.5;
    score.add([timing, [0]]);

    score.saveToFile("/tmp/sc-store/score.txt");

    // Write file
    score.recordNRT(
        nil,
        outPath,
        sampleRate: 48000,
        headerFormat: "WAV",
        sampleFormat: "int16",
        options: ServerOptions.new.numOutputBusChannels_(2),
        action: {
            // Check for successful write (file exists)
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
    # json, ttsData = IMAGE.loadTTSJSON(msg.at(1).asString);
    if(json.notNil && ttsData.notNil,
        {
            try {
                "Trying to render...".postln;
                renderGeneric.(
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
            if(ttsData.isNil, { "TTS data is nil.".postln; });
            addr.sendMsg(\status, \fail);
        }
    );
}, '/render/genericObject', nil);
