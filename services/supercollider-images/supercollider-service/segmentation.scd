var renderSegments;
"Semantic Segmentation Sonification".postln;
renderSegments = { |json, ttsData, outPath, addr|
    var score, timing, order=3, segments;
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

    // Load texture buffers
    // TODO

    "Set up done. Starting segments...".postln;

    // Load segments from file
    segments = json.at("segments");
    segments.do({ |segment, i|
        var audio, duration;
        audio = segment.at("audio");
        duration = (audio.at("duration").asInteger / ttsData.sampleRate);

        // Play segment name from TTS
        // TODO as HOA
        score.add([
            timing,
            [\s_new, \playBufferStereo, -1, 0, 1, \bufNum, 210, \start, audio.at("offset").asInteger, \duration, duration]
        ]);

        timing = timing + duration;

        // Play segment sonification
        // TODO
    });

    // Add one last noop msg
    score.add([timing, [0]]);

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
                { addr.sendMsg(\status, \done); },
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
    msg.at(1).asString.postln;
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
            json.postln;
            ttsData.postln;
            addr.sendMsg(\status, \fail);
        }
    );
}, '/render/semanticSegmentation', nil);
