var pointLine, continuousLine, pieChart;
"Charts Sonifications (pointLine, continuousLine, pieChart)".postln;
// Currently lacking labels or title. WIP
pieChart = { |json, outPath, addr|
    var score, timing=0, order=5, wedges, total, arcs, duration = 2;
    score = IMAGE.newScore(order);

    wedges = json.at("wedges").collect({|item, i| item.asFloat});
    wedges = wedges.sort({|a,b| a > b});

    // Set up b-format decoder
    score.add([
        timing,
        [\s_new, (\binauralDecodeNrt++order.asSymbol).asSymbol, 1001, 0, 1, \in, 2]
    ]);

    // Create angular sweep pairs in radians from raw data
    wedges = wedges.integrate!2;
    wedges = wedges.flop
                   .flat
                   .drop(-1);
    wedges = wedges.addFirst(0.0);
    arcs = wedges.linlin(0.0, wedges.last, 0.0, 2pi);
    arcs = arcs.clump(2);

    // Render sweeps in order from 0 to 2pi
    arcs.do({|arc, i|
        var start, end, percentage;
        start = arc[0];
        end = arc[1];
        percentage = ((end - start) / 2pi);

        score.add([
            timing,
            [\s_new, (\playMovingVoiceHOA++order.asSymbol).asSymbol, 1002 + i, 2, 1001,
                \freq, percentage.linlin(0.0, 1.0, 1.0, 0.0).linexp(0.0, 1.0, 4.0, 40),
                \blend, percentage.linlin(0, 1, 0, 1),  // noop
                \bright, percentage.linlin(0, 1, 0.8, 2.0),
                \gain, percentage.linlin(0, 1, 0.2, 1.0),
                \thetaStart, start,
                \thetaEnd, end,
                \duration, duration
            ]
        ]);

        timing = timing + (percentage * duration) + 0.3 + 0.1;  // Sorry, magic numbers
    });

    // Add last noop msg
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

OSCdef.newMatching(\piechart, { |msg, time, addr, recvPort|
    var json = nil;
    "Received as message at /render/charts/pie...".postln;
    json = IMAGE.loadJSON(msg.at(1).asString);
    if(json.notNil,
        {
            try {
                "Trying to render...".postln;
                pieChart.(
                    json: json,
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
            "JSON data nil!".postln;
            addr.sendMsg(\status, \fail);
        }
    );
}, '/render/charts/pie', nil);
