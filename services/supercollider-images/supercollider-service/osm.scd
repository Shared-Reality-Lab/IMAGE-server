/*
 * Copyright (c) 2022 IMAGE Project, Shared Reality Lab, McGill University
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
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.
 */
var renderOsmStreets;
"OSM Streets Rendering".postln;
renderOsmStreets = { |json, ttsData, outPath, addr|
    var score, timing, order=5, segmentInfo=Array.new, baseGain=(0.dbamp), streets, pois, latList, lonList, latMax, latMin, lonMax, lonMin, intervalDuration = 0.1, lowNote = 70, highNote = lowNote + 48;
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

    // Set up data
    streets = json.at("data").at("streets");
    pois = json.at("data").at("points_of_interest");
    // Determine min and max of latitude and longitude
    // TODO use provided limits in header once standardized
    latList = streets.collect({|item, i| item.at("nodes").collect({|jtem, j| jtem.at("lat").asFloat }) }).flatten;
    lonList = streets.collect({|item, i| item.at("nodes").collect({|jtem, j| jtem.at("lon").asFloat }) }).flatten;
    latMin = latList.minItem;
    latMax = latList.maxItem;
    lonMin = lonList.minItem;
    lonMax = lonList.maxItem;

    // Wait before starting synthesis
    timing = timing + 0.5;

    // Launch synth for beginning of the street
    score.add([
        timing,
        [\s_new, (\playContinuousResonzNoiseHOA++order.asSymbol).asSymbol, 1002, 2, 1001,
            \freq, 90.midicps,
            \gain, 0.0,
            \decay, 0.005,
            \imp, 10]
    ]);

    // Iterate over each street...
    streets.do({|street, i|
        var theta, phi, freq;
        // TODO play street name if applicable
        // Set to first position in list
        // Note: longitude is east-west, latitude is north-south
        // Need to flip latitude since we function expects graphics coordinates (0 is top)
        # theta, phi = IMAGE.mapCoords(
            street.at("nodes")[0].at("lon").asFloat.linlin(lonMin, lonMax, 0, 1),
            street.at("nodes")[0].at("lat").asFloat.linlin(latMin, latMax, 1, 0)
        );
        freq = street.at("nodes")[0].at("lat").asFloat.linlin(latMin, latMax, lowNote.midicps, highNote.midicps);
        score.add([
            timing,
            [\n_set, 1002,
                \theta, theta,
                \phi, phi,
                \freq, freq]
        ]);

        // Iterate through nodes, play POIs when reached
        street.at("nodes").do({|node, j|
            // Node POI
            # theta, phi = IMAGE.mapCoords(
                node.at("lon").asFloat.linlin(lonMin, lonMax, 0, 1),
                node.at("lat").asFloat.linlin(latMin, latMax, 1, 0)
            );
            freq = node.at("lat").asFloat.linlin(latMin, latMax, lowNote.midicps, highNote.midicps);
            if (node.at("POIs_ID").notNil, {
                // mute street noise
                score.add([
                    timing,
                    [\n_set, 1002, \gain, baseGain * 0.003]
                ]);
                timing = timing + 0.1;
                // Magic numbers from Florian...
                score.add([
                    timing,
                    [\s_new, (\playDiscreteSinePingHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                        \theta, theta,
                        \phi, phi,
                        \freq, freq,
                        \decay, 0.01.linlin(0.0, 1.0, 0.008, 0.03),
                        \gain, baseGain * 0.01]
                ]);

                // TODO wait and play TTS for these POIs
            });

            // Unmute street noise
            score.add([
                timing,
                [\n_set, 1002, \gain, baseGain * 0.08]
            ]);
            // Move to new point (magic numbers from Florian)
            score.add([
                timing,
                [\n_set, 1002,
                    \theta, theta,
                    \phi, phi,
                    \freq, freq,
                    \decay, 0.1.linlin(0, 1, 0.008, 0.03),
                    \imp, 0.5.linlin(0, 1, 30, 30)
                ]
            ]);
            timing = timing + intervalDuration;
        });
        // Fade out segment and wait
        score.add([timing, [\n_set, 1002, \gain, 0]]);
        timing = timing + 0.8;
    });

    score.add([timing, [0]]);
    score.saveToFile("/tmp/sc-store/score.txt");

    // Write audio file
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
                    addr.sendMsg(\status, \done, *segmentInfo);
                },
                {
                    "Failed to write file in NRT!".postln;
                    addr.sendMsg(\status, \fail);
                }
            );
            "Done (OSM Street Rendering)".postln;
        }
   );
};

OSCdef.newMatching(\osmStreets, { |msg, time, addr, recvPort|
    var json = nil, ttsData = nil;
    "Received a message at /render/map/osmStreets...".postln;
    # json, ttsData = IMAGE.loadTTSJSON(msg.at(1).asString);
    if(json.notNil && ttsData.notNil,
        {
            try {
                "Trying to render...".postln;
                renderOsmStreets.(
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
            if (ttsData.isNil, { "TTS data is nil.".postln; });
            addr.sendMsg(\status, \fail);
        }
    );
}, '/render/map/osmStreets', nil);
