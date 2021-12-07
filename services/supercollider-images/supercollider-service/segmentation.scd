var renderSegments;
"Semantic Segmentation Sonification".postln;
renderSegments = { |json, ttsData, outPath, addr|
    var score, timing, order=5, segments, segmentInfo;
    timing = 0;
    segmentInfo = Array.new;
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

    "Set up done. Starting segments...".postln;

    // Load segments from file
    segments = json.at("segments");
    segments.do({ |segment, i|
        var audio, duration, centroid, theta, phi, midinote, pingDur=0.001;
        audio = segment.at("audio");
        duration = (audio.at("duration").asInteger / ttsData.sampleRate);
        centroid = segment.at("centroid");

        // Add segment info to array
        segmentInfo = segmentInfo.add(segment.at("nameOfSegment").asString);
        segmentInfo = segmentInfo.add(timing.asFloat);

        // Play segment name from TTS
        # theta, phi = IMAGE.mapCoords(centroid.at(0).asFloat, centroid.at(1).asFloat);
        score.add([
            timing,
            [\s_new, (\playBufferHOA++order.asSymbol).asSymbol, 1002, 2, 1001,
                \buffNum, 210,
                \start, audio.at("offset").asInteger,
                \duration, duration,
                \theta, theta,
                \phi, phi
            ]
        ]);

        timing = timing + duration;

        // Play segment sonification
        // Add segment player
        midinote = centroid.at(1).asFloat.linlin(0.0, 1.0, 57, 45).round;
        score.add([
            timing,
            [\s_new, (\playKlankNoise4SegmentHOA++order.asSymbol).asSymbol, 1003, 2, 1001, \midinote, midinote, \lag, pingDur]
        ]);
        score.add([
            timing,
            [\n_set, 1003, \gain, 0.1]
        ]);
        segment.at("coord").do({ |item, i|
            var x, y, theta, phi;
            x = item.at(0).asFloat;
            y = item.at(1).asFloat;
            # theta, phi = IMAGE.mapCoords(x, y);
            score.add([
                timing,
                [\n_set, 1003, \theta, theta, \phi, phi]
            ]);
            timing = timing + pingDur;
        });
        score.add([
            timing,
            [\n_set, 1003, \gain, 0.0]
        ]);
        timing = timing + 0.1;
        // Free the segment
        score.add([
            timing,
            [\n_free, 1003]
        ]);
        segmentInfo = segmentInfo.add(timing - segmentInfo.at(segmentInfo.size - 1));
    });

    // Add one last noop msg
    score.add([timing, [0]]);

    score.saveToFile("/tmp/sc-store/score.txt");

    score.recordNRT(
        nil,
        outPath,
        sampleRate: 48000,
        headerFormat: "WAV",
        sampleFormat: "int16",
        options: ServerOptions.new.numOutputBusChannels_(2),
        action: {
            // Check for written file
            if(File.exists(outPath),
                { addr.sendMsg(\status, \done, *segmentInfo); },
                {
                    "Failed to write file in NRT!".postln;
                    addr.sendMsg(\status, \fail);
                }
            );
            "Done".postln;
        }
    );
};

OSCdef.newMatching(\semseg, { |msg, time, addr, recvPort|
    var json = nil, ttsData = nil;
    "Received a message at /render/semanticSegmentation...".postln;
    # json, ttsData = IMAGE.loadTTSJSON(msg.at(1).asString);
    if(json.notNil && ttsData.notNil,
        {
            try {
                "Trying to render...".postln;
                renderSegments.(
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
}, '/render/semanticSegmentation', nil);
