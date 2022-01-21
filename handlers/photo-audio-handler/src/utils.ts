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

export type TTSSegment = {
    value: string;
    type: string;
}

type ObjDet = {
    objects: { ID: number, type: string }[];
};

type ObjGroup = {
    grouped: { IDs: number[] }[];
    ungrouped: number[];
};

export function generateEmptyResponse(requestUUID: string): { "request_uuid": string, "timestamp": number, "renderings": Record<string, unknown>[] } {
    return {
        "request_uuid": requestUUID,
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": []
    };
}

export function generateIntro(secondCatData: { "category": string }): string {
    const category = secondCatData["category"];
    if (category === "indoor" || category === "outdoor") {
        return "This " + category + " photo";
    }
    return "This photo";
}

export function generateSemSeg(semSeg: { "segments": Record<string, unknown>[] }): TTSSegment[] {
    const segments = semSeg["segments"];
    const data: TTSSegment[] = [];
    data.push({"value": "contains the following outlines of regions:", "type": "text"});
    data.push(...segments.map(segment => {
        const newSeg = segment;
        newSeg["value"] = (newSeg["nameOfSegment"] as string) + ",";
        newSeg["type"] = "segment";
        return newSeg as TTSSegment;
    }));
    data[data.length-1]["value"] = data[data.length - 1]["value"].replace(",", ".");
    data[data.length-1]["value"] = "and " + data[data.length-1]["value"];
    return data;
}

export function generateObjDet(objDet: ObjDet, objGroup: ObjGroup): TTSSegment[] {
    const objects: TTSSegment[] = [];
    objects.push({"type": "text", "value": "contains the following objects or people:"});
    for (const group of objGroup["grouped"]) {
        const objs = objDet["objects"].filter((x: { "ID": number }) => group["IDs"].includes(x["ID"]));
        const sType = (objs.length > 0) ? objs[0]["type"] : "object";
        const pType = pluralize(sType.trim());
        const object = {
            "type": "object",
            "objects": objs,
            "value": objs.length.toString() + " " + pType + ","
        };
        objects.push(object);
    }
    for (const idx of objGroup["ungrouped"]) {
        const obj = objDet["objects"].find((x: { "ID": number }) => x["ID"] === idx);
        if (obj !== undefined) {
            objects.push({
                "type": "object",
                "objects": [obj],
                "value": (Articles.articlize(obj["type"].trim()) as string) + ","
            } as TTSSegment);
        }
    }
    objects[objects.length-1]["value"] = objects[objects.length - 1]["value"].replace(",", ".");
    objects[objects.length-1]["value"] = "and " + objects[objects.length-1]["value"];
    return objects;
}
