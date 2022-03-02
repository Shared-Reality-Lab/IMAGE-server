(
~path = “/Users/floriangrond/Documents/PROJECTS/2021-ATP/CHARTS/Charts_Data_Format_Examples/example2/“;
~order = 5;
~chart = “example2.json”;
~entries = JSONFileReader.read(~path++~chart);
~series = ~entries.at(“data”).at(“series”)[0].at(“data”)[0];
~seriesInterpreted = [];
~series.do({|item,i| ~seriesInterpreted = ~seriesInterpreted.add(
                       [i.linlin(0,~series.size, -1,1) ,
                        item.at(“y”).interpret,
                        item.at(“category”).interpret,
                        item.at(“dt”)
                       ] ) });
~seriesInterpreted.do({|item,i|
                     if(item[1] == nil,{item[1] = 0});
});
// Discrete NOISE Ping
5.do({|i|
    var order = i+1;
SynthDef((\discreteRingzPingHOA++(i+1)).asSymbol,{|freq = 200, phi = 0, theta = 0.0, radius = 1, gain = 0.1, decay = 0.02, imp = 48|
    var  sig, encoded, env, excitation, reverb;
        // excitation =  Dust.ar(100);
        // partials =  ({|i|SinOsc.ar( (i+1) * freq.lag(0.5) )}!10).sum;
        env = EnvGen.ar(Env.perc(0.01, 0.01, 1.0, -4),1, doneAction: 2);
        sig =  Ringz.ar( WhiteNoise.ar(0.05), freq, 10) ;
        // sig =  Ringz.ar( PinkNoise.ar(0.05) * Decay.ar( Impulse.ar(imp), 0.01) , freq, decay, 0.01 );
        // reverb = FreeVerb.ar(sig, 0.1, 0.3, damp: 0.6, mul: 1);
        encoded = HoaEncodeDirection.ar(sig * env * gain,
                                theta,
                                phi,
                                2.0,
                                order.asInteger);
    Out.ar(2,  encoded);
}).add
});
5.do({|i|
    var order = i+1;
SynthDef((\playBufferHOA++(i+1)).asSymbol,{|freq = 200, phi = 0, theta = 0.0, radius = 1, gain = 0, bufnum = 300, start = 0, duration = 1|
    var  sig, encoded, env, excitation, reverb;
        // excitation =  Dust.ar(100);
        // partials =  ({|i|SinOsc.ar( (i+1) * freq.lag(0.5) )}!10).sum;
        env = EnvGen.ar(Env.new(levels: [ 0, 1, 1, 0 ], times: [ 0.001, duration, 0.001 ]),1, doneAction: 2);
        sig =  PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum) * 1.00, 1, start, doneAction:2);
        // sig =  Ringz.ar( PinkNoise.ar(0.05) * Decay.ar( Impulse.ar(imp), 0.01) , freq, decay, 0.01 );
        reverb = FreeVerb.ar(sig, 0.1, 0.3, damp: 0.6, mul: 1);
        encoded = HoaEncodeDirection.ar(reverb *  gain ,
                                theta,
                                phi,
                                2.0,
                                order.asInteger);
    Out.ar(2,  encoded);
}).add
});
//~seriesInterpreted.do({|item,i| item.postln })
//~seriesInterpreted.flop[1].plot
//~seriesInterpreted.flop[1].minItem
//~seriesInterpreted.flop[1].maxItem
~duration = 0.4;
~lowNote = 80;
~highNote = ~lowNote + 24;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
~lastBuffNR = HOABinaural.lastBuffID.postln;
~score.add([ 0.0001, [ ‘b_allocRead’, 300 + 0, ~path++“TTS.wav”, 0, 0 ]], );
~wait = 0.0;
~score.add([ ~wait, [ ‘s_new’, (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);
~wait = 0.5;
~score.add([ ~wait, [ ‘s_new’, (\playBufferHOA++~order.asSymbol).asSymbol, -1, 2, 1001,
                      \theta, 0.linlin(-1.0,  1.0, -0.5pi, 0.5pi),
                      \phi,   1.linlin(-1.0,  1.0, -0.4pi, 0.4pi),
                      \bufnum,  300,
                      \duration, 7,
                      \gain, 0.1,
            ] ],);
            ~wait = ~wait + 7;
~seriesInterpreted.do({|item,i|
~score.add([ ~wait, [ ‘s_new’, (\discreteRingzPingHOA++~order.asSymbol).asSymbol, -1, 2, 1001,
                      \theta, item[0].linlin(-1.0,  1.0, -0.5pi, 0.5pi),
                      \phi,   item[1].linlin(~seriesInterpreted.flop[1].minItem,
                                             ~seriesInterpreted.flop[1].maxItem, -0.4pi, 0.4pi),
                      \freq,  item[1].linlin(~seriesInterpreted.flop[1].minItem,
                                             ~seriesInterpreted.flop[1].maxItem, 100, 2000),
                      \decay, 0.1.linlin( 0.0,  1.0, 0.008, 0.03),
                     // \imp,   1.0.linlin( 0.0,  1.0, 30, 70),
                      \gain, 0.01,
            ] ],);
    ~wait = ~wait + 0.002;
 });
~wait = ~wait + 1;
~score.add([~wait + 3, [0]] );
//~path = “/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/“;
~score.saveToFile(~path++“score.txt”);
~srvrOpts = ServerOptions.new;
~srvrOpts.numOutputBusChannels_(2);
~srvrOpts.memSize_(8192 * 40);  // you might need to increase the memory if we do massive multichannel
~srvrOpts.maxNodes = 1024 * 10;
~score.recordNRT(
    “/tmp/trashme”,
    ~path++“sound.wav”,
    sampleRate: 48000,
    headerFormat: “WAV”,
    sampleFormat: “int16”,
    options: ~srvrOpts
);
)
