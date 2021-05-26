"MINIMAL TEST IS LOADED".postln;

~minimalTest =

{|inputFile, outputFile|
// define our score

	inputFile.postln;
	outputFile.postln;

~score = Score.new;

~sndPathScene = inputFile.asString;

~bufnumScene = Server.default.bufferAllocator.alloc(1);


SoundFile.use( ~sndPathScene,
              {arg soundFile;
                  ~headerFormat = soundFile.headerFormat;
                  ~sampleFormat = soundFile.sampleFormat;
                  ~sampleRate = soundFile.sampleRate;
                  ~sceneDuration = soundFile.duration;
               }
);

// define an encoding and decoding synth
SynthDef(\swoosh, {
    Out.ar(0, EnvGen.ar( Env(),1, doneAction:2)
		*
    SplayAz.arFill(2, 10, {
        Ringz.ar(WhiteNoise.ar(0.001),
        XLine.kr(exprand(100.0,5000.0), exprand(100.0,5000.0), 3),
        0.5)
    }));
}).load;

SynthDef(\playBuf, {arg buffer;
    var src, panned;
    // play TTS file from a buffer
    src = PlayBuf.ar(1, buffer, BufRateScale.kr(buffer));
	// encode in first oder Ambisonics B-format
		panned = Pan2.ar(src, Line.ar(-1, 1, ~sceneDuration));
    // decode our B-format signal to binaural
    Out.ar(0, panned);
}).load;




~score.add([ 0.0, [ 'b_allocRead', ~bufnumScene, ~sndPathScene, 0, 0 ]], );


// add commands to instantiate synth
~score.add([ 0.0, [ 's_new', '\playBuf', 1001, 0, 1, 'buffer', ~bufnumScene ] ],);
~score.add([ ~sceneDuration * 0.5, [ 's_new', '\swoosh', 1002, 0, 1 ] ],);

~score.add([ ~sceneDuration + 0.1, [ 'b_free', ~bufnumScene ]]);


// add the needed dummy command to stop NRT
~score.add([~sceneDuration + 0.2, [0]] );

// render our ~score to a sound file
~score.recordNRT(
    "/tmp/trashme",
    outputFile,
    sampleRate: 48000,
	headerFormat: "WAV",
	sampleFormat: "int16",
    options: ServerOptions.new.numOutputBusChannels_(2)
);

};


OSCdef.newMatching(\renderer1, {|msg, time, addr, recvPort|
	~minimalTest.(inputFile:  msg[1].asString, outputFile:  msg[2].asString );
    addr.sendMsg(\status);
}, '/render', nil);

OSCdef.newMatching(\pingpong, {|msg, time, addr, recvPort|
    "Pong".postln;
    addr.sendMsg(\pong);
}, '/ping', nil);

/*
~path = "/Users/floriangrond/Documents/PROJECTS/2021-ATP/Rendering/";

~minimalTest.(outputFile:  ~path++"swoosh.wav".standardizePath );

m = NetAddr("127.0.0.1", 57120); // loopback

m.sendMsg("/render", ~path++"example.wav", ~path++"renderoutput.wav"  );
*/


