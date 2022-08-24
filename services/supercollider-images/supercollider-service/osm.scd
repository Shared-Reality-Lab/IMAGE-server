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
     var score, timing, order=5, segmentArray=Array.new, baseGain=(0.dbamp);
     timing = 0;
     score = IMAGE.newScore(order);

     // TODO

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
