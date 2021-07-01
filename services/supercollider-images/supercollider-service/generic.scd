(
//var jsonFile = "/home/juliette/generic-tts-handler-pp.json";
var jsonFile = "/home/juliette/Documents/ATP Misc/demo2/generic-tts-handler-1625056971430.json";
jsonFile.postln;

if(File.exists(jsonFile),
    {
        File.use(jsonFile, "r", { |f|
            var jsonData;
            jsonData = f.readAllString;
            ~json = jsonData.parseYAML;
        });
        "Read file successfully.".postln;
    },
    { "Could not open the file :(".postln; }
);
)

(
//var ttsFile = "/home/juliette/generic-tts-handler-1625072926686.wav";
var ttsFile = "/home/juliette/Documents/ATP Misc/demo2/generic-tts-handler-1625056971429.wav";

if (File.exists(ttsFile),
    {
        SoundFile.use(ttsFile, { |f|
            ~ttsData = f;
        });
    },
    { "Could not open the file :(".postln; }
);
)

(
var score = Score.new;
var timing = 0;
var serv = Server(\nrt, options: ServerOptions.new
    .numOutputBusChannels_(2)
);

// Add synthdefs
score.add([
    0,
    ['/d_recv',
        SynthDef(\player, { |out=0, inBuf|
            Out.ar(out,
                PlayBuf.ar(1, inBuf, BufRateScale.kr(inBuf))
            );
        }).asBytes
    ]
]);
score.add([
    0,
    ['/d_recv',
        SynthDef(\player2, { |out=0, inBuf|
            Out.ar(out,
                PlayBuf.ar(1, inBuf, BufRateScale.kr(inBuf))!2
            );
        }).asBytes
    ]
]);
score.add([
    0,
    ['/d_recv',
        SynthDef(\playerpan, { |out=0, inBuf, pos=0|
            Out.ar(out,
                Pan2.ar(
                    PlayBuf.ar(1, inBuf, BufRateScale.kr(inBuf)),
                    (pos - 0.5) * 2.0
                )
            );
        }).asBytes
    ]
]);
// Start with intro
t = ~json.at("audioTemplate").at("intro");
score.add([
    timing,
    (b=Buffer(serv, numChannels: 1)).allocReadMsg(~ttsData.path, t.at("offset"), t.at("duration"))
]);
score.add([
    timing,
    (s=Synth.basicNew(\player2, serv)).newMsg(args: ['inBuf', b.bufnum])
]);
timing = timing + t.at("duration").asInteger / ~ttsData.sampleRate;
score.add([timing, b.freeMsg]);
score.add([timing, s.freeMsg]);

// Iterate over objects
~json.at("objects").do({ |item, i|
    var audio, xCent;
    ("Iteration: "++i).postln;
    if(i + 1 == ~json.at("objects").size,
        {
            var t;
            "Last Element! Adding 'and'...".postln;
            t = ~json.at("audioTemplate")
            .at("joining")
            .at("and");
            score.add([
                timing,
                (b=Buffer(serv)).allocReadMsg(
                    ~ttsData.path,
                    t.at("offset"),
                    t.at("duration")
                )
            ]);
            score.add([
                timing,
                (s=Synth.basicNew(\player2, serv)).newMsg(args: ['inBuf', b.bufnum])
            ]);
            timing = timing + (t.at("duration").asInteger / ~ttsData.sampleRate);
            score.add([timing, b.freeMsg]);
            score.add([timing, s.freeMsg]);
        }
    );
    audio = item.at("offset");
    score.add([
        timing,
        (j=Buffer(serv)).allocReadMsg(~ttsData.path, audio.at("offset"), audio.at("duration"))
    ]);
    xCent = item.at("centroid").at(0).asFloat;
    xCent.postln;
    score.add([
        timing,
        (k=Synth.basicNew(\playerpan, serv)).newMsg(
            args: [
                'inBuf', j.bufnum,
                'pos', xCent
            ]
        )
    ]);
    timing = timing + (audio.at("duration").asInteger / ~ttsData.sampleRate);
    score.add([timing, j.freeMsg]);
    score.add([timing, k.freeMsg]);
});


score.recordNRT(
    nil,
    "/home/juliette/what.aiff",
    options: serv.options,
    action: { serv.remove; }
);
)