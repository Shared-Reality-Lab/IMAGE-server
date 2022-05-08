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
 * If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.
 */
import fetch from "node-fetch";
import osc from "osc";

export type TTSResponse = {
    durations: number[];
    audio: string;
}

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

export async function sendOSC(jsonFile: string, outFile: string, server: string, port: number, path: string) {
    const oscPort = new osc.UDPPort({
        "remoteAddress": server,
        "remotePort": port,
        "localAddress": "0.0.0.0",
        "localPort": 0
    });

    return Promise.race<void>([
        new Promise<void>((resolve, reject) => {
            try {
                oscPort.on("message", (oscMsg: osc.OscMessage) => {
                    const arg = oscMsg["args"] as osc.Argument[];
                    if (arg[0] === "done") {
                        oscPort.close();
                        resolve();
                    }
                    else if (arg[0] === "fail") {
                        oscPort.close();
                        reject(oscMsg);
                    }
                });
                // Send command when ready
                oscPort.on("ready", () => {
                    oscPort.send({
                        "address": path,
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
        new Promise<void>((resolve, reject) => {
            setTimeout(() => {
                try {
                    oscPort.close();
                } catch (_) { /* noop */ }
                reject("Timeout");
            }, 5000);
        })
    ]);
}
