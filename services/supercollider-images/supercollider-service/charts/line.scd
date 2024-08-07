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
var singleLineChart;
"Single Line Chart".postln;
singleLineChart = { |json, ttsData, outPath, addr|
    var score, timing, order=5, baseGain=(-4.dbamp), audio, seriesData, miny, maxy, timediff;
    timing = 0;
    score = IMAGE.newScore(order);
    // Set up b-format decoder
    score.add([
        timing,
        [\s_new, (\binauralDecodeNrt++order.asSymbol).asSymbol, 1001, 0, 1, \in, 2]
    ]);

    // Assuming JSON contains:
    // - title/intro TTSed
    // - series containing data points

    // Let's do TTS first...
    score.add([
        timing,
        [\b_allocRead, 210, ttsData.path, 0, 0]
    ]);
    audio = json.at("audio");
    (audio.at("duration").asInteger / ttsData.sampleRate);
    // Play non-spatialized audio
    score.add([
        timing,
        [\s_new, \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, audio.at("offset").asInteger, \duration, (audio.at("duration").asInteger / ttsData.sampleRate), \gain, 0.dbamp]
    ]);
    timing = timing + (audio.at("duration").asInteger / ttsData.sampleRate);

    // Set up Graph
    seriesData = [];
    json.at("seriesData").do({ |item, i|
        var yval;
        try {
            yval = item.at("y").asFloat;
        } { |err|
            yval = 0;
        };
        seriesData = seriesData.add(
            [
                i.linlin(0, json.at("seriesData").size, -1, 1),
                yval
            ]
        );
    });
    miny = seriesData.flop[1].minItem;
    maxy = seriesData.flop[1].maxItem;
    // Below defines a band where rendering duration will not increase
    // but instead the time between pings will get shorter, sounding
    // continuous to the listener. This may need to be adjusted further.
    timediff = seriesData.size.linlin(20, 1000, 0.1, 0.001);
    seriesData.do({ |item, i|
        score.add([
            timing,
            [
                \s_new, (\discreteRingzPingHOA++order.asSymbol).asSymbol, -1, 2, 1001,
                \theta, item.at(0).linlin(-1.0, 1.0, -0.5pi, 0.5pi),
                \phi, item.at(1).linlin(miny, maxy, -0.4pi, 0.4pi),
                \freq, item.at(1).linlin(miny, maxy, 100, 2000),
                \decay, 0.0102,
                \radius, 2.0,
                \gain, baseGain * 0.1
            ]
        ]);
        timing = timing + timediff;
    });
    timing = timing + 0.1;
    score.add([timing, [0]]);

    // Write file
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
                    "Failed to write file in NRT!".postln;
                    addr.sendMsg(\status, \fail);
                }
            );
            "Done (Simple Line Chart)".postln;
        }
    );
};

OSCdef.newMatching(\singlelinechart, { |msg, time, addr, recvPort|
    var json = nil, ttsData = nil;
    "Received as message at /render/charts/line...".postln;
    # json, ttsData = IMAGE.loadTTSJSON(msg.at(1).asString);
    if(json.notNil && ttsData.notNil,
        {
            try {
                "Trying to render...".postln;
                singleLineChart.(
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
}, '/render/charts/line', nil);
