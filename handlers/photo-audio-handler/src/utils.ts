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
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.
 */
import Articles from "articles";
import pluralize from "pluralize";
import osc from "osc";

const MIN_OBJ_AREA = 0.0005; // For ungrouped objects only, for grouped objects applies to whole group.

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

type TranslationResponse = {
    translations: string[];
    src_lang: string;
    tgt_lang: string;
}

type Obj = { ID: number, type: string, area: number };

type ObjDet = {
    objects: Obj[];
};

type ObjGroup = {
    grouped: { IDs: number[] }[];
    ungrouped: number[];
};

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

export function generateSemSeg(semSeg: { "segments": Record<string, unknown>[] }): TTSSegment[] {
    const segments = semSeg["segments"];
    const data: TTSSegment[] = [];
    data.push({"value": "contains the following outlines of regions:", "type": "text"});
    data.push(...segments.map(segment => {
        const newSeg = segment;
        newSeg["value"] = (newSeg["name"] as string) + ",";
        newSeg["type"] = "segment";
        newSeg["label"] = newSeg["name"] as string;
        return newSeg as TTSSegment;
    }));
    data[data.length-1]["value"] = data[data.length - 1]["value"].replace(",", ".");
    if (data.length > 2) {
        data[data.length-1]["value"] = "and " + data[data.length-1]["value"];
    }
    return data;
}

export function filterObjectsBySize(objDet: ObjDet, objGroup: ObjGroup) {
    const groupsToDelete: number[] = [];
    for (const group of objGroup["grouped"]) {
        const objs = objDet["objects"].filter((x: { "ID": number }) => group["IDs"].includes(x["ID"])) as Obj[];
        const totalArea = objs.map(a => a.area).reduce((a, b) => a+ b, 0);
        if (totalArea < MIN_OBJ_AREA) {
            groupsToDelete.push(objGroup["grouped"].indexOf(group));
        }
    }
    for (const idx of groupsToDelete) {
        for (const objId of objGroup["grouped"][idx]["IDs"]) {
            objDet["objects"].splice(objDet["objects"].findIndex(obj => obj["ID"] === objId), 1);
        }
        delete objGroup["grouped"][idx];
    }

    const ungroupedToDelete: number[] = [];
    for (const idx of objGroup["ungrouped"]) {
        const obj = objDet["objects"].find((x: { "ID": number }) => x["ID"] === idx);
        if (obj && obj.area < MIN_OBJ_AREA) {
            ungroupedToDelete.push(idx);
        }
    }
    for (const idx of ungroupedToDelete) {
        objDet["objects"].splice(objDet["objects"].findIndex(obj => obj["ID"] === idx), 1);
        objGroup["ungrouped"].splice(objGroup["ungrouped"].indexOf(idx), 1);
    }
}


export function generateObjDet(objDet: ObjDet, objGroup: ObjGroup): TTSSegment[] {
    const objects: TTSSegment[] = [];
    objects.push({"type": "text", "value": "contains the following objects or people:"});
    for (const group of objGroup["grouped"]) {
        const objs = objDet["objects"].filter((x: { "ID": number }) => group["IDs"].includes(x["ID"])) as Obj[];
        const totalArea = objs.map(a => a.area).reduce((a, b) => a+ b, 0);
        if (totalArea > MIN_OBJ_AREA) {
            const sType = (objs.length > 0) ? objs[0]["type"] : "object";
            const pType = pluralize(sType.trim());
            const object = {
                "type": "object",
                "objects": objs,
                "label": pType,
                "value": objs.length.toString() + " " + pType + ","
            };
            objects.push(object);
        }
    }
    for (const idx of objGroup["ungrouped"]) {
        const obj = objDet["objects"].find((x: { "ID": number }) => x["ID"] === idx);
        if (obj !== undefined) {
            if (obj["area"] > MIN_OBJ_AREA) {
                objects.push({
                    "type": "object",
                    "objects": [obj],
                    "label": obj["type"].trim(),
                    "value": (Articles.articlize(obj["type"].trim()) as string) + ","
                } as TTSSegment);
            }
        }
    }
    objects[objects.length-1]["value"] = objects[objects.length - 1]["value"].replace(",", ".");
    if (objects.length > 2) {
        objects[objects.length-1]["value"] = "and " + objects[objects.length-1]["value"];
    }
    return objects;
}

export async function getTranslationSegments(text: string[], targetLang: string): Promise<TranslationResponse> {
  /**
   * Get translation from multilang-support service
   * @param text: text to be translated
   * @param targetLang: target language, in ISO 639-1 format
   * @returns {Promise<TranslationResponse>}
   */
  return fetch("http://multilang-support/service/translate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: text, targetLang: targetLang }),
  }).then((resp) => resp.json() as Promise<TranslationResponse>);
}

export async function getTTS(text: string[], language: string): Promise<TTSResponse> {
    let serviceURL: string;
    console.debug(`[getTTS()] Target Language: ${language}`);
    if (language == "fr")
        serviceURL = "http://espnet-tts-fr/service/tts/segments";
    else if (language == "en")
        serviceURL = "http://espnet-tts/service/tts/segments";
    else
        throw new Error("Language not supported");
    return fetch(serviceURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ segments: text }),
    }).then((resp) => resp.json() as Promise<TTSResponse>);
}

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
                                    "offset": arg[i+1] as number,
                                    "duration": arg[i+2] as number
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

export function renderingTitle(semseg: { "segments": Record<string, unknown>[] }, objDet: ObjDet, objGroup: ObjGroup): string {
    const hasSemseg = (semseg !== undefined) && (semseg["segments"].length > 0);
    const hasObj = (objDet !== undefined) && (objGroup !== undefined) && (objDet["objects"].length > 0);
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
