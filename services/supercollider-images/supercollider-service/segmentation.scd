"Semantic Segmentation Sonification".postln;

OSCdef.newMatching(\semseg, { |msg, time, addr, recvPort|
    var json = nil, ttsData = nil;
    "Received a message at /render/semanticSegmentation...".postln;
    "...but it was not implemented!".postln;
    addr.sendMsg(\status, \fail);
}, '/render/semanticSegmentation', nil);
