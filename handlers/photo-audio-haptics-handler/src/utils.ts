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
import Articles from "articles";
import pluralize from "pluralize";
import fetch from "node-fetch";
import osc from "osc";

export type TTSSegment = {
    value: string;
    type: string;
    label?: string;
    audio?: { offset: number, duration: number }
}

export type TTSResponse = {
    durations: number[];
    audio: string;
}

type ObjDet = {
    objects: {
        ID: number,
        type: string,
        centroid: [number, number],
        dimensions: [number, number, number, number],
    }[];
};

type ObjGroup = {
    grouped: { IDs: number[] }[];
    ungrouped: number[];
};

// Geometry information for locating points and contours
export type segGeometryInfo = {
    centroid: [number, number];
    contourPoints: [number, number, number, number];
}

// Can contain more than one item when objects are grouped
export type objGeometryInfo = {
    centroid: [number, number][];
    contourPoints: [number, number, number, number][];
}

export type SoundSegments = {
    name: string;
    offset: number;
    duration: number;
}[];

export function generateEmptyResponse(requestUUID: string): { "request_uuid": string, "timestamp": number, "renderings": Record<string, unknown>[] } {
    return {
        "request_uuid": requestUUID,
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": []
    };
}

export function generateIntro(secondCatData: { "category": string } | undefined): string {
    if (secondCatData) {
        const category = secondCatData["category"];
        if (category === "indoor" || category === "outdoor") {
            return "This " + category + " photo";
        }
    }
    return "This photo";
}

export function generateSemSeg(semSeg: { "segments": Record<string, unknown>[] }): [TTSSegment[], segGeometryInfo[]] {
    const segments = semSeg["segments"];

    // TTS
    const ttsData: TTSSegment[] = [];
    // Location data
    const posData: segGeometryInfo[] = [];
    ttsData.push({ "value": "contains the following outlines of regions:", "type": "text" });
    for (const segment of segments) {
        const newSeg = segment;
        newSeg["value"] = (newSeg["nameOfSegment"] as string) + ",";
        newSeg["type"] = "segment";
        newSeg["label"] = newSeg["nameOfSegment"] as string;

        const coord = segment["coord"] as [number, number, number, number];
        const centroid = segment["centroid"] as [number, number];
        const geoSeg = {
            "centroid": centroid,
            "contourPoints": coord
        };
        ttsData.push(newSeg as TTSSegment);
        posData.push(geoSeg as segGeometryInfo);
    }
    ttsData[ttsData.length - 1]["value"] = ttsData[ttsData.length - 1]["value"].replace(",", ".");
    ttsData[ttsData.length - 1]["value"] = "and " + ttsData[ttsData.length - 1]["value"];
    return [ttsData, posData];
}

export function generateObjDet(objDet: any, objGroup: ObjGroup): [TTSSegment[], objGeometryInfo[]] {
    const objects: TTSSegment[] = [];

    const hapticObjInfo: objGeometryInfo[] = [];
    const groupCentroidArray: Array<Array<number>> = [];
    const groupCoordArray: Array<Array<number>> = [];

    objects.push({ "type": "text", "value": "contains the following objects or people:" });
    for (const group of objGroup["grouped"]) {
        const objs = objDet["objects"].filter((x: { "ID": number }) => group["IDs"].includes(x["ID"]));
        const sType = (objs.length > 0) ? objs[0]["type"] : "object";
        const pType = pluralize(sType.trim());
        const object = {
            "type": "object",
            "objects": objs,
            "label": pType,
            "value": objs.length.toString() + " " + pType + ","
        };
        objects.push(object);

        const centroidArray: [number, number][] = [];
        const coordArray: [number, number, number, number][] = [];
        objs.map((obj: { [x: string]: any; }) => {
            const centroid = obj["centroid"];
            const coords = obj["dimensions"];
            centroidArray.push(centroid)
            coordArray.push(coords)
        })
        const geoObjSeg = {
            "centroid": centroidArray,
            "contourPoints": coordArray
        }
        hapticObjInfo.push(geoObjSeg);
    }
    for (const idx of objGroup["ungrouped"]) {
        const obj = objDet["objects"].find((x: { "ID": number }) => x["ID"] === idx);
        if (obj !== undefined) {
            objects.push({
                "type": "object",
                "objects": [obj],
                "label": obj["type"].trim(),
                "value": (Articles.articlize(obj["type"].trim()) as string) + ","
            } as TTSSegment);

            const geoObjSeg = {
                "centroid": obj["centroid"],
                "contourPoints": obj["dimensions"]
            }
            hapticObjInfo.push(geoObjSeg);
            // const centroid = obj["centroid"]
            // const coords = obj["dimensions"]         
            // groupCentroidArray.push(centroid);
            // groupCoordArray.push(coords);
        }
    }
    //hapticObjInfo.push(groupCentroidArray)
    objects[objects.length - 1]["value"] = objects[objects.length - 1]["value"].replace(",", ".");
    objects[objects.length - 1]["value"] = "and " + objects[objects.length - 1]["value"];
    return [objects, hapticObjInfo];
}

export async function getTTS(text: string[]): Promise<TTSResponse> {
    return fetch("http://espnet-tts/service/tts/segments", {
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": JSON.stringify({ "segments": text })
    }).then(resp => resp.json() as Promise<TTSResponse>);
}

/** Pushes SuperCollider audio data to passed audioArray. */
export async function sendOSC(jsonFile: string, outFile: string, server: string, port: number) {
    const oscPort = new osc.UDPPort({
        "remoteAddress": server,
        "remotePort": port,
        "localAddress": "0.0.0.0",
        "localPort": 0
    });

    return Promise.race<SoundSegments>([
        new Promise<SoundSegments>((resolve, reject) => {
            try {
                oscPort.on("message", (oscMsg: osc.OscMessage) => {
                    const arg = oscMsg["args"] as osc.Argument[];
                    if (arg[0] === "done") {
                        const respArry: SoundSegments = [];
                        console.log(respArry);
                        console.log(respArry.length);
                        if ((arg.length) > 1 && ((arg.length - 1) % 3 == 0)) {
                            for (let i = 1; i < arg.length; i += 3) {
                                respArry.push({
                                    "name": arg[i] as string,
                                    "offset": arg[i + 1] as number,
                                    "duration": arg[i + 2] as number
                                });
                            }
                        }
                        oscPort.close();
                        resolve(respArry);
                    }
                    else if (arg[0] === "fail") {
                        oscPort.close();
                        reject(oscMsg);
                    }
                });
                // Send command when ready
                oscPort.on("ready", () => {
                    oscPort.send({
                        "address": "/render/photo",
                        "args": [
                            { "type": "s", "value": jsonFile },
                            { "type": "s", "value": outFile }
                        ]
                    });
                });
                oscPort.open();
            } catch (e) {
                oscPort.close();
                reject(e);
            }
        }),
        new Promise<SoundSegments>((resolve, reject) => {
            setTimeout(() => {
                try {
                    oscPort.close();
                } catch (_) { /* noop */ }
                reject("Timeout");
            }, 5000);
        })
    ]);
}

export function renderingTitle(semseg: Record<string, unknown>, objDet: Record<string, unknown>, objGroup: Record<string, unknown>): string {
    const hasSemseg = semseg !== undefined;
    const hasObj = (objDet !== undefined) && (objGroup !== undefined);
    if (hasSemseg && hasObj) {
        return "Regions, things, and people";
    }
    else if (hasSemseg) {
        return "Outlines of regions";
    }
    else {
        return "Things and people";
    }
}