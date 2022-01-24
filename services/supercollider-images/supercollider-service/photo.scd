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
    var score, timing, order=5;
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
                { addr.sendMsg(\status, \done, *segmeentInfo); }
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
