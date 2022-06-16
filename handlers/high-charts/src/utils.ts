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

/**
 * The function will return the string representing the graph title and axes information
 * @param highChartsData 
 * @returns graphInfo string
 */
export function getGraphInfo(highChartsData: any): string{
    const chartsData = structuredClone(highChartsData);
    const title = chartsData.title || chartsData.series[0].name || 'Untitled Chart';
    const xAxis = chartsData.axes.find((axes: { axis: string; })=>axes.axis == "xAxis");
    const yAxis = chartsData.axes.find((axes: { axis: string; })=>axes.axis == "yAxis");
    let xStart = xAxis.dataMin;
    let xEnd = xAxis.dataMax;
    let yStart = yAxis.dataMin;
    let yEnd = yAxis.dataMax;
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    if (xAxis.type.lowerCase() == "datetime"){
        xAxis.dataMin = new Date(xAxis.dataMin);
        xAxis.dataMax = new Date(xAxis.dataMax);
        xStart = `${xAxis.dataMin.getDate()} ${monthNames[xAxis.dataMin.getMonth()]} ${xAxis.dataMin.getYear()}`;
        xEnd = `${xAxis.dataMax.getDate()} ${monthNames[xAxis.dataMax.getMonth()]} ${xAxis.dataMax.getYear()}`
    } 
    if (yAxis.type.lowerCase() == "datetime"){
        yAxis.dataMin = new Date(yAxis.dataMin);
        yAxis.dataMax = new Date(yAxis.dataMax);
        yStart = `${yAxis.dataMin.getDate()} ${monthNames[yAxis.dataMin.getMonth()]} ${yAxis.dataMin.getYear()}`;
        yEnd = `${yAxis.dataMax.getDate()} ${monthNames[yAxis.dataMax.getMonth()]} ${yAxis.dataMax.getYear()}`
    } 
    let xAxisInfo = `${xAxis.axis} , ${xAxis.title} from ${xStart} to ${xEnd}`;
    let yAxisInfo = `${yAxis.axis} , ${yAxis.title} from ${yStart} to ${yEnd}`;
    return `${title} , ${xAxisInfo} , ${yAxisInfo}`;
}
