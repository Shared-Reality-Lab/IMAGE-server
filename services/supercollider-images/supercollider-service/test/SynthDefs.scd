// BINAURAL Decoder
// Note that this SynthDef uses the ar4Score method from HOABinaural and
// assumes the IRs to be loaded via loadbinauralIRs4Score2 starting with buffer ID 0
// second argument is the order for which IRs are loaded starting at 0

// this is a limiter

SynthDef(\limiterStereo,{ |level = 0.9, dur = 0.2, in = 0, out = 0|
	var sig;
	sig = In.ar(in, 2);
	Out.ar(out, sig * 0.1)
}).load(s);


5.do({|i|
	var order = i+1;
	SynthDef((\binauralDecodeNrt++(i+1)).asSymbol, { |in= 0, out=0|
	var decoded;
		decoded = HOABinaural.ar4Score(order, In.ar(in, (order+1).pow(2).asInteger ));
	Out.ar(out, decoded)
}).load(s);
});


5.do({|i|
	var order = i+1;
	SynthDef((\noiseBurstHOA++(i+1)).asSymbol, { |theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1|
	var sig, encoded;
	sig = WhiteNoise.ar(0.1) * EnvGen.ar( Env.perc, 1, doneAction:2 );
	encoded = HoaEncodeDirection.ar(sig, theta, phi, radius, order.asInteger);
	Out.ar(out, encoded)
}).load(s);
});


5.do({|i|
	var order = i+1;
	SynthDef((\pingHOA++(i+1)).asSymbol, { |freq= 1000, resonz = 0.5, theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1, mix = 0.33, room = 0.5, damp = 0.5|
	var sig, env, envGen, rev, encoded;
	env = Env([0, 1, 0], [0.01, 0.1], [5,-5]);
	envGen =  EnvGen.ar(env, doneAction: 0);
	sig = Ringz.ar( PinkNoise.ar(0.1) * envGen, freq, resonz) * AmpComp.kr(freq, 300);
	rev = FreeVerb.ar(sig, mix: mix, room: room, damp:damp);
	DetectSilence.ar(rev, doneAction:2);
	encoded = HoaEncodeDirection.ar(rev, theta, phi, radius, order.asInteger);
	Out.ar(out, encoded * gain)
}).load(s);
});


/*
~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 's_new', \limiterStereo, 1001, 0, 1, \dur, 0.001] ],);
~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1002, 2, 1001, \in, 2] ],);
~score.add([ 0.1, [ 's_new', (\noiseBurstHOA++~order.asSymbol).asSymbol, -1, 2, 1002, \theta,  0.5pi, \phi, 0.0pi, \radius, 0.4, \out, 2 ] ],);
~score.add([ 0.5, [ 's_new', (\noiseBurstHOA++~order.asSymbol).asSymbol, -1, 2, 1002, \theta,  0.0pi, \phi, 0.0pi, \radius, 0.4, \out, 2 ] ],);
~score.add([ 0.9, [ 's_new', (\noiseBurstHOA++~order.asSymbol).asSymbol, -1, 2, 1002, \theta, -0.5pi, \phi, 0.0pi, \radius, 0.4, \out, 2 ] ],);

~score.add([2.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);

*/


/*
~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 's_new', \limiterStereo, 1001, 0, 1, \level, 0.001] ],);
~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1002, 2, 1001, \in, 2] ],);
~score.add([ 0.1, [ 's_new', (\pingHOA++~order.asSymbol).asSymbol, -1, 2, 1002, \freq, 1800, \resonz, 0.01, \theta,  0.5pi, \phi, 0.0pi, \radius, 3,   \mix, 0.3, \room, 0.1, \out, 2, \gain, 0.5 ] ],);
~score.add([ 0.5, [ 's_new', (\pingHOA++~order.asSymbol).asSymbol, -1, 2, 1002, \freq, 1000, \resonz, 0.02, \theta,  0.0pi, \phi, 0.0pi, \radius, 0. 7, \mix, 0.3, \room, 0.9, \out, 2, \gain, 0.5 ] ],);
~score.add([ 0.9, [ 's_new', (\pingHOA++~order.asSymbol).asSymbol, -1, 2, 1002, \freq, 2000, \resonz, 0.005, \theta, -0.5pi, \phi, 0.0pi, \radius, 0.3, \mix, 0.3, \room, 0.9, \out, 2, \gain, 0.5 ] ],);

~score.add([5.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);
*/



SynthDef(\playBufferStereo,{ |buffNum = 0, start = 0, duration = 1, out = 0, stereoPos = 0.0, gain = 1|
	var sig;
		sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *
	          EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
	Out.ar(out, Pan2.ar(sig, stereoPos))
}).load(s);


5.do({|i|
	var order = i+1;
	SynthDef((\playBufferHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1, theta = 0.0, phi = 0.0, radius = 1.5, out = 2, gain = 1|
	var sig, encoded;
		sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *  EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
	    encoded = HoaEncodeDirection.ar(sig, theta, phi, radius, order.asInteger);
	Out.ar(out, encoded)
}).load(s);
});

// with reverb
5.do({|i|
	var order = i+1;
	SynthDef((\playBufferReverbHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1,
		                                                   theta = 0.0,
		                                                   phi = 0.0,
		                                                   radius = 1.5,
		                                                   mix = 0.33,
		                                                   room = 0.5,
		                                                   damp = 0.5,
		                                                   out = 2, gain = 1|
	var sig, encoded;
		sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *  EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
		sig = FreeVerb.ar(sig, mix: mix, room: room, damp: damp);
	    encoded = HoaEncodeDirection.ar(sig, theta, phi, radius, order.asInteger);
	Out.ar(out, encoded)
}).load(s);
});


/*
Oneshot static sample
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";

~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 'b_allocRead', 210, ~path++"gravel.wav", 0, 0 ]], );

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);

// ~score.add([ 0.1, [ 's_new', (\playBufferHOA++~order.asSymbol).asSymbol, -1, 2, 1001, \buffNum, 210, \start, 0, \duration, 5, \theta,  0.25pi, \phi, 0.0pi, \radius, 0.8, \out, 2 ] ],);
// with reverb
~score.add([ 0.1, [ 's_new', (\playBufferReverbHOA++~order.asSymbol).asSymbol, -1, 2, 1001, \buffNum, 210,
                                                                                            \start, 0,
                                                                                            \duration, 5,
                                                                                            \theta,  0.25pi,
                                                                                            \phi, 0.0pi,
                                                                                            \radius, 0.8,
                                                                                            \mix, 0.3,
                                                                                            \room, 0.9,
                                                                                            \damp, 0.99,
                                                                                            \out, 2 ] ],);

~score.add([5.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);

*/

5.do({|i|
	var order = i+1;
	SynthDef((\playBufferLinearMoveHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1,
		                                           thetaStart = 0.5pi, thetaStop = -0.5pi,
		                                           phiStart = 0.25pi, phiStop = -0.25pi,
		                                           radiusStart = 2.5, radiusStop = 0.5,
		                                           out = 2, gain = 1|
	var sig, encoded;
		sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *
		      EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;
		encoded = HoaEncodeDirection.ar(sig, Line.ar(thetaStart, thetaStop, duration),
			                                 Line.ar(phiStart, phiStop, duration),
			                                 Line.ar(radiusStart, radiusStop, duration),
			                                 order.asInteger);
	Out.ar(out, encoded)
}).load(s);
});


5.do({|i|
	var order = i+1;
	SynthDef((\playBufferLinearMoveReverbHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0, duration = 1,
		                                           thetaStart = 0.5pi, thetaStop = -0.5pi,
		                                           phiStart = 0.25pi, phiStop = -0.25pi,
		                                           radiusStart = 2.5, radiusStop = 0.5,
		                                           mix = 0.33,
		                                           room = 0.5,
		                                           damp = 0.5,
		                                           out = 2, gain = 1|
	var sig, encoded;
		sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start) *
		      EnvGen.ar( Env.new([0,1,1,0],[0.001, duration - 0.002, 0.001],[-1,-1,-1]), 1, doneAction: 2) ;

		sig = FreeVerb.ar(sig, mix: 0.33, room: 0.5, damp:0.5);
		encoded = HoaEncodeDirection.ar(sig, Line.ar(thetaStart, thetaStop, duration),
			                                 Line.ar(phiStart, phiStop, duration),
			                                 Line.ar(radiusStart, radiusStop, duration),
			                                 order.asInteger);
	Out.ar(out, encoded)
}).load(s);
});

/*
// Oneshot static sampler linear move
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";

~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 'b_allocRead', 210, ~path++"gravel.wav", 0, 0 ]], );

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);
~score.add([ 0.1, [ 's_new', (\playBufferLinearMoveReverbHOA++~order.asSymbol).asSymbol, -1, 2, 1001, \buffNum, 210, \start, 0, \duration, 5,
                                          \thetaStart,  0.5pi, \thetaStop,  -0.5pi,
                                          \phiStart, 0.35pi, \phiStop, -0.25pi,
                                          \radiusStart, 15.4, \radiusStop, 0.4,
                                          \mix, 0.3,
                                          \room, 0.9,
                                          \damp, 0.99,
                                          \out, 2 ] ],);

~score.add([5.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);





// Oneshot static stereo plus 3D audio
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 'b_allocRead', 210, ~path++"gravel.wav", 0, 0 ]], );

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);

~score.add([ 1.0, [ 's_new', \playBufferStereo, -1, 0, 1, \buffNum, 210, \start, 0, \duration, 5] ],);

~score.add([ 3, [ 's_new', (\playBufferLinearMoveReverbHOA++~order.asSymbol).asSymbol, -1, 2, 1001, \buffNum, 210, \start, 0, \duration, 5,
                                          \thetaStart,  0.5pi, \thetaStop,  -0.5pi,
                                          \phiStart, 0.35pi, \phiStop, -0.25pi,
                                          \radiusStart, 15.4, \radiusStop, 0.4,
                                          \mix, 0.25,
                                          \room, 0.9,
                                          \damp, 0.1,
                                          \out, 2 ] ],);

~score.add([9.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);

*/


5.do({|i|
	var order = i+1;
	SynthDef((\playBuffer4SegmentHOA++(i+1)).asSymbol, { |buffNum = 0, start = 0,
		                                                  theta = 0.0pi, phi = 0.0pi, radius = 2.5,
		                                                  out = 2, gain = 0, lag = 0.1|
	var sig, encoded;
		sig = PlayBuf.ar(1, bufnum: buffNum, rate: 1, trigger: 1, startPos: start, loop: 1);
		encoded = HoaEncodeDirection.ar(sig, theta.lag(lag),
			                                 phi.lag(lag),
			                                 radius.lag(lag),
			                                 order.asInteger);
		Out.ar(out, encoded * gain.lag(lag))
}).load(s);
});


// lloping over segments

/*
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);

// load soundfile specific for the segment
~score.add([ 0.0001, [ 'b_allocRead', 210, ~path++"sky.wav", 0, 0 ]], );

// beginning of the segment, launch the synth
~score.add([ 0.01, [ 's_new', (\playBuffer4SegmentHOA++~order.asSymbol).asSymbol, 1002, 2, 1001, \buffNum, 210] ],);

// move to the first position
~score.add([ 0.1, [ 'n_set', 1002, \theta, -0.5pi,  \phi, 0.0pi] ],);
// fade in
~score.add([ 0.1, [ 'n_set', 1002, \gain, 1.0] ],);
// this needs to loop over the outline of the segment
~score.add([ 0.3, [ 'n_set', 1002, \theta, -0.25pi, \phi, 0.1pi] ],);
~score.add([ 0.5, [ 'n_set', 1002, \theta, -0.1pi,  \phi, 0.2pi] ],);
~score.add([ 0.7, [ 'n_set', 1002, \theta,  0.1pi,  \phi, 0.2pi] ],);
~score.add([ 0.9, [ 'n_set', 1002, \theta,  0.25pi, \phi, 0.1pi] ],);
~score.add([ 1.1, [ 'n_set', 1002, \theta,  0.5pi,  \phi, 0.0pi] ],);
// end of segment fade out
~score.add([ 1.2, [ 'n_set', 1002, \gain, 0.0,] ],);
// free the synth
~score.add([ 1.3, [ '/n_free', 1001] ],);


~score.add([2.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);
*/



5.do({|i|
	var order = i+1;
	SynthDef((\playKlankNoise4SegmentHOA++(i+1)).asSymbol, { |midinote = 60,
		                                                  theta = 0.0pi, phi = 0.0pi, radius = 2.5,
		                                                  out = 2, gain = 0, lag = 0.1|
	var sig, encoded;
		sig = Klank.ar(`[{|i|  (i+1) + 0.01.rand2 }!30, {|i| 1/(i+1) }!30, {|i| 2/(i+1) }!30], BrownNoise.ar(0.001) + Dust.ar(50, 0.5) , midinote.midicps  );
		encoded = HoaEncodeDirection.ar(sig, theta.lag(lag),
			                                 phi.lag(lag),
			                                 radius.lag(lag),
			                                 order.asInteger);
		Out.ar(out, encoded * gain.lag(lag))
}).load(s);
});




/*

~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~order = 5;
~score = Score.new;
HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);

// load soundfile specific for the segment

// beginning of the segment, launch the synth
~score.add([ 0.01, [ 's_new', (\playKlankNoise4SegmentHOA++~order.asSymbol).asSymbol, 1002, 2, 1001, \midinote, 45] ],);

// move to the first position
~score.add([ 0.1, [ 'n_set', 1002, \theta, -0.5pi,  \phi, 0.0pi] ],);
// fade in
~score.add([ 0.1, [ 'n_set', 1002, \gain, 0.1] ],);
// this needs to loop over the outline of the segment
~score.add([ 0.3, [ 'n_set', 1002, \theta, -0.25pi, \phi, 0.1pi] ],);
~score.add([ 0.5, [ 'n_set', 1002, \theta, -0.1pi,  \phi, 0.2pi] ],);
~score.add([ 0.7, [ 'n_set', 1002, \theta,  0.1pi,  \phi, -0.2pi] ],);
~score.add([ 0.9, [ 'n_set', 1002, \theta,  0.25pi, \phi, -0.1pi] ],);
~score.add([ 1.1, [ 'n_set', 1002, \theta,  0.5pi,  \phi, 0.0pi] ],);
// end of segment fade out
~score.add([ 1.2, [ 'n_set', 1002, \gain, 0.0,] ],);
// free the synth
~score.add([ 1.3, [ '/n_free', 1001] ],);


~score.add([2.0, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);


*/



// PIE CHART   PIE CHART   PIE CHART   PIE CHART   PIE CHART   PIE CHART   PIE CHART   PIE CHART   PIE CHART   PIE CHART


5.do({|i|
	var order = i+1;
SynthDef((\playMovingVoiceHOA++(i+1)).asSymbol,{|freq = 100, blend = 0.5, bright = 0, duration = 3, phi = 0, thetaStart= -0.5pi, thetaEnd=  0.5pi, radius = 1, gain = 1|
    var va = Vowel(\a, \bass),
        vi = Vowel(\i, \soprano),
        sig, line, encoded, segduration, env, reverb;
		segduration = ((thetaEnd - thetaStart) / 2pi) * duration;
		env = EnvGen.kr(Env.new([0,1,1,0],[0.01, segduration, 0.01]), 1.0, doneAction: Done.none);
		sig =  BPFStack.ar( Decay.ar(Impulse.ar(freq), 0.01) * PinkNoise.ar(0.9) , va.blend(vi, blend).brightenExp(bright, 1), widthMods: 5 ) * env;
		reverb = FreeVerb.ar(sig, 0.33, 0.9, damp: 0.9, mul: 500);
	encoded = HoaEncodeDirection.ar(reverb *  gain,
			                    Line.ar(thetaStart, thetaEnd, segduration + 0.02),
			                    phi,
			                    2.0,
			                    order.asInteger);
    Out.ar(2,  encoded);
}).add
});




/*
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~order = 5;
~score = Score.new;
~duration = 2;

//~wedges = ({10.0.rand}!5).normalizeSum;
//~wedges = ~wedges.sort({|a,b| a> b});
~wedges = [0.5, 0.2, 0.1, 0.07, 0.08];

~wedges = ~wedges.integrate;
~wedges = ~wedges!2;
~wedges = ~wedges.flop.flat;
~wedges = ~wedges.drop(-1);
~wedges = ~wedges.addFirst(0.0);
~arcs = ~wedges.linlin(0.0, 1.0 , 0.0, 2pi);
~arcs = ~arcs.clump(2);

HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);
// beginning of the piechart wedge, launch the synth


~wait = 0;

~arcs.do({|item,i|
~thetaStart = ~arcs[i][0]; ~thetaEnd = ~arcs[i][1];

~percetage = ((~thetaEnd - ~thetaStart) / 2pi) ;
~percetage.postln;
~score.add([ ~wait, [ 's_new', (\playMovingVoiceHOA++~order.asSymbol).asSymbol, 1002 + i, 2, 1001,
                             \freq, ~percetage.linlin(0.0,1.0, 1.0,0.0).linexp(0.0,1.0, 4.0, 40),
                             \blend, ~percetage.linlin(0,1,0,1),
                             \bright, ~percetage.linlin(0,1,0.8,2.0),
                             \gain, ~percetage.linlin(0,1,0.2,1.0),
                             \thetaStart, ~thetaStart,
                             \thetaEnd, ~thetaEnd,
                             \duration, ~duration] ],);

~wait = ~wait + ( ((~thetaEnd - ~thetaStart) / 2pi) * ~duration ) + 0.3 + 0.1;
});

// free the synth not really necessary
// ~score.add([ 7, [ '/n_free', 1001] ],);

~score.add([7.1, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);

*/



5.do({|i|
	var order = i+1;
SynthDef((\playVoicePingHOA++(i+1)).asSymbol,{|freq = 100, blend = 0.5, bright = 0, duration = 0.5, phi = 0, theta = 0.0, radius = 1, gain = 1, lag = 0.01|
    var va = Vowel(\a, \bass),
        vi = Vowel(\i, \bass),
        sig, encoded, env, partials, excitation, reverb;
		excitation = WhiteNoise.ar(0.1);
		partials =  Klank.ar(`[{|i| i+1}!20, nil, {0.4}!20] , excitation, freq.lag(lag));
		sig =  BPFStack.ar( partials , va.blend(vi, blend.lag(lag)).brightenExp(bright.lag(lag), 1), widthMods: 5 ) ;
		reverb = FreeVerb.ar(sig, 0.22, 0.5, damp: 0.9, mul: 500) * env;
	encoded = HoaEncodeDirection.ar(reverb *  gain,
			                    theta.lag(lag),
			                    phi.lag(lag),
			                    2.0,
			                    order.asInteger);
    Out.ar(2,  encoded);
}).add
});


/*
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~order = 5;
~score = Score.new;
~duration = 0.1;

~xPoints = {|i| i * 0.1}!100;
~xyPoints = ~xPoints.collect({|item,i| [item, (item).sin]  });
~xyPoints.flop.plot;

~yMin = ~xyPoints.flop[1].minItem;
~yMax = ~xyPoints.flop[1].maxItem;

~xMin = ~xyPoints.flop[0].minItem;
~xMax = ~xyPoints.flop[0].maxItem;


HOABinaural.loadbinauralIRs4Score2(~score, ~order);
HOABinaural.lastBuffID.postln;

~score.add([ 0.0, [ 's_new', (\binauralDecodeNrt++~order.asSymbol).asSymbol, 1001, 0, 1, \in, 2] ],);
// beginning of the piechart wedge, launch the synth

~wait = 0;

~xyPoints.do({|item,i|
~score.add([ ~wait, [ 's_new', (\playVoicePingHOA++~order.asSymbol).asSymbol, 1002 + i, 2, 1001,
                             \freq, item[1].linlin(~yMin, ~yMax, 40,52).midicps,
                             \blend, item[1].linlin(~yMin, ~yMax, 1.0,0.0),
                             \bright, item[1].linlin(~yMin, ~yMax, 1.0,2.0),
                             \gain, 0.001,
                             \theta, item[0].linlin(~xMin, ~xMax, -0.5pi, 0.5pi),
                             \phi, item[1].linlin(~yMin, ~yMax, -0.3pi, 0.3pi),
                             \duration, ~duration] ],);

~wait = ~wait + (~duration * 0.5);
});

// free the synth not really necessary
// ~score.add([ ~wait + 1, [ '/n_free', 1001] ],);

~score.add([~wait + 1.1, [0]] );
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";
~score.saveToFile(~path++"score.txt");


~srvrOpts = ServerOptions.new;
~srvrOpts.numOutputBusChannels_(2);
~srvrOpts.memSize_(8192 * 8);

~score.recordNRT(
    "/tmp/trashme",
	~path++"testscore.wav",
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ~srvrOpts
);

*/



