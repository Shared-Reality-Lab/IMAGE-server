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
"Autour-style POI Rendering".postln;
autourStyle = { |json, ttsData, outPath, addr|
    var dMeters, score, timing, order=5, length=5, nTones=3, earconList, places, lat, lon, poiDelay=0.5, endDelay=0.5;
    timing = 0;
    score = IMAGE.newScore(order);

    // Distance in meters from lat-lon
    // From https://stackoverflow.com/a/11172685/1086511
    dMeters = { |lat1, lon1, lat2, lon2|
        var R, dLat, dLon, a, c, d;
        R = 6378.137;
        dLat = (lat2 * pi / 180.0) - (lat1 * pi / 180.0);
        dLon = (lon2 * pi / 180.0) - (lon1 * pi / 180.0);
        a = (dLat / 2.0).sin.squared + ((lat1 * pi / 180.0).cos * (lat2 * pi / 180.0).cos * (dLon / 2.0).sin.squared);
        c = 2 * a.sqrt.atan2((1 - a).sqrt);
        d = R * c;
        d * 1000
    };

    // Set up b-format decoder
    score.add([
        timing,
        [\s_new, (\binauralDecoderNrt++order.asSymbol).asSymbol, 1001, 0, 1, \in, 2]
    ]);

    // Initialize earcon list
    earconList = Array.fill(length, (0..(nTones -1 )))
                        .allTuples
                        .select({ |item| item.includesAll((0..(nTones - 1))); })
                        .perfectShuffle;
    earconList = earconList.rotate(earconList.size / 2);

    // Load TTS buffer
    score.add([
        timing,
        [\b_allocRead, 210, ttsData.path, 0, 0]
    ]);

    // Begin rendering places
    places = json.at("places");
    lat = json.at("lat").asFloat;
    lon = json.at("lon").asFloat;
    places.do({ |item|
        var dist, dLat, dLon, xDist, yDist;
        dLat = item.at("ll").at(0).asFloat;
        dLon = item.at("ll").at(1).asFloat;
        dist = dMeters.(lat, lon, dLat, dLon).asFloat;
        ("Dist: " + dist.asString).postln;
        xDist = dMeters.(lat, lon, dLat, lon).asFloat * (dLat - lat).sign;
        ("xDist: " + xDist.asString).postln;
        yDist = dMeters.(lat, lon, lat, dLon).asFloat * (dLon - lon).sign;
        ("yDist: " + yDist.asString).postln;
        item.add(\dist -> dist);
        item.add(\xDist -> xDist);
        item.add(\yDist -> yDist);
    });
    // Sort from nearest to farthest
    places.sort({ |a, b| a.at("dist") < b.at("dist") });
    places.do({ |item, i|
        var note, ecPattern, theta, phi, audio;
        note = yDist.linlin(-250, 250, 80, 104);
        theta = yDist.atan2(xDist);
        audio = item.at("audio");
        phi = 0;
        //phi = yDist.linlin(-250, 250, -0.25pi, 0.25pi);
        ecPattern = earconList.at(item.at("cat"));
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
                \gain, 0.01
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
                \gain, 0.01
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
        outPath,
        sampleRate: 48000,
        headerFormat: "WAV",
        sampleFormat: "int16",
        options: ServerOptions.new.numOutputBusChannels_(2),
        actions: {
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