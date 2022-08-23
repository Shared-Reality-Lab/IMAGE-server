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

var autourStyle;
"Autour-style Rendering".postln;

autourStyle = { |json, ttsData, outPath, addr|
    var dMeters, score, timing, order=5, length=5, nTones=3, earconList, places, lat, lon, poiDelay=0.5, endDelay=0.5, intro, baseGain=(1.dbamp);
    timing = 0;
    score = IMAGE.newScore(order);

    // Set up b-format decoder
    score.add([
        timing,
        [\s_new, (\binauralDecodeNrt++order.asSymbol).asSymbol, 1001, 0, 1, \in, 2]
    ]);

    // Initialize earcon list
    earconList = Array.fill(length, (0..(nTones -1 )))
                        .allTuples
                        .select({ |item| item.includesAll((0..(nTones - 1))); })
                        .perfectShuffle;
    earconList = earconList.rotate((earconList.size / 2).asInteger);

    // Load TTS buffer
    score.add([
        timing,
        [\b_allocRead, 210, ttsData.path, 0, 0]
    ]);

    intro = json.at("intro");
    score.add([
        timing,
        [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, intro.at("offset"), \duration, (intro.at("duration").asInteger / ttsData.sampleRate)]
    ]);
    timing = timing + (intro.at("duration").asInteger / ttsData.sampleRate);

    // Begin rendering places
    places = json.at("places");
    places.sort({ |a, b| a.at("azimuth").asFloat <= b.at("azimuth").asFloat });
    places.do({ |item, i|
        var note, ecPattern, theta, phi, audio, dist;
        theta = item.at("azimuth").asFloat;
        dist = item.at("dist").asFloat;
        note = theta.cos.linlin(-1, 1, 80, 104);
        audio = item.at("audio");
        phi = 0;
        ecPattern = earconList.at(item.at("cat").asInteger);
        // play earcon based on category
        // As of writing (2022-01-06), the radius for included POIs is 250 meters.
        score.add([
            timing,
            [\s_new, (\playDiscreteSinePingHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                \note, note,
                \int0, ecPattern.at(0),
                \int1, ecPattern.at(1),
                \int2, ecPattern.at(2),
                \int3, ecPattern.at(3),
                \int4, ecPattern.at(4),
                \theta, theta,
                \phi, phi,
                //\gain, 0.1 * dist.linlin(0, 250, 0, -6)
                \gain, baseGain * dist.linlin(0, 250, 0, -6).dbamp
            ]
        ]);
        timing = timing + 1.0; // TODO adjust based on length along with synthdef

        // TODO play title of POI
        score.add([
            timing,
            [\s_new, (\playBufferHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                \buffNum, 210,
                \start, audio.at("offset").asInteger,
                \duration, (audio.at("duration").asInteger / ttsData.sampleRate),
                \theta, theta,
                \phi, phi,
                //\gain, 0.2 * dist.linlin(0, 250, 0, -6)
                \gain, baseGain * dist.linlin(0, 250, 0, -6).dbamp
            ]
        ]);
        timing = timing + (audio.at("duration").asInteger / ttsData.sampleRate);


        timing = timing + poiDelay;
    });

    // Add last no-op
    timing = timing + endDelay;
    score.add([timing, [0]]);
    score.saveToFile("/tmp/sc-store/score.txt");

    // Write to file
    score.recordNRT(
        nil,
        outPath ++ ".wav",
        sampleRate: 48000,
        headerFormat: "WAVE",
        sampleFormat: "int16",
        options: ServerOptions.new.numOutputBusChannels_(2).verbosity_(-1),
        action: {
            // Check for successful write (file exists)
            if(File.exists(outPath),
                {
                    ("lame -v" + outPath ++ ".wav" + outPath).systemCmd;
                    File.delete(outPath ++ ".wav");
                    addr.sendMsg(\status, \done);
                },
                {
                    "Failed to write file!".postln;
                    addr.sendMsg(\status, \fail);
                }
            );
            "Done".postln;
        }
    );
};

OSCdef.newMatching(\autourPOI, { |msg, time, addr, recvPort|
    var json =nil, ttsData = nil;
    "Received a message at /render/map/autourPOI...".postln;
    # json, ttsData = IMAGE.loadTTSJSON(msg.at(1).asString);
    if(json.notNil && ttsData.notNil,
        {
            try {
                "Trying to render...".postln;
                autourStyle.(
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
}, '/render/map/autourPOI', nil);
