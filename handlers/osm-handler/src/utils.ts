/*
 * Copyright (c) 2022 IMAGE Project, Shared Reality Lab, McGill University
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
import fetch from "node-fetch";
import osc from "osc";

export type Rendering = {
    type_id: string;
    description: string;
    data: Record<string, unknown>;
    metadata?: { homepage: string };
}

export type TTSResponse = {
    durations: number[];
    audio: string;
}

export type StreetNode = {
    id: number;
    lat: number;
    lon: number;
    POI_IDs?: number[];
}

export type POI = {
    id: number;
    lat: number;
    lon: number;
    cat: string;
    name?: string;
    audio?: { offset: number, duration: number };
}

export type Street = {
    street_id: number;
    street_name?: string;
    street_type?: string;
    surface?: string;
    oneway?: string;
    sidewalk?: string;
    maxspeed?: string;
    lanes?: string;
    nodes?: StreetNode[];
    audio?: { offset: number, duration: number };
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

export async function getTTS(text: string[]): Promise<TTSResponse> {
    return fetch("http://espnet-tts/service/tts/segments", {
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": JSON.stringify({ "segments": text })
    }).then(resp => resp.json() as Promise<TTSResponse>);
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
                        "address": "/render/map/osmStreets",
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
            }, 10000);
        })
    ]);
}
