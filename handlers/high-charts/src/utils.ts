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
import osc from "osc";

export type TTSResponse = {
    durations: number[];
    audio: string;
}

export type TranslationResponse = {
  translations: string[];
  src_lang: string;
  tgt_lang: string;
};

export function generateEmptyResponse(requestUUID: string): { "request_uuid": string, "timestamp": number, "renderings": Record<string, unknown>[] } {
    return {
        "request_uuid": requestUUID,
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": []
    };
}

export async function getTTS(text: string[], targetLanguage: string): Promise<TTSResponse> {
    let ttsUrl:string;
    if (targetLanguage === "en") {
        ttsUrl = "http://espnet-tts/service/tts/segments";
    } else if (targetLanguage === "fr") {
        ttsUrl = "http://espnet-tts-fr/service/tts/segments";
    }
    else {
        console.error(`Unsupported language: ${targetLanguage}`);
        throw new Error(`Unsupported language: ${targetLanguage}`);
    }
    return fetch(ttsUrl, {
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

export async function getTranslationSegments(
  text: string[],
  targetLang: string
): Promise<TranslationResponse> {
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
    body: JSON.stringify({ segments: text, tgt_lang: targetLang }),
  }).then((resp) => resp.json() as Promise<TranslationResponse>);
}            


/**
 * The function will return the string representing the graph title and axes information
 * @param highChartsData
 * @returns graphInfo string
 */
export function getGraphInfo(highChartsData: any): string{
    const title = highChartsData.title || highChartsData.series[0].name || 'Untitled Chart';
    const xAxis = highChartsData.axes.find((axes: { axis: string; })=>axes.axis === "xAxis");
    const yAxis = highChartsData.axes.find((axes: { axis: string; })=>axes.axis === "yAxis");
    let xStart = xAxis.dataMin;
    let xEnd = xAxis.dataMax;
    let yStart = yAxis.dataMin;
    let yEnd = yAxis.dataMax;
    if (xAxis.type.toLowerCase() === "datetime"){
        const xDataMin = new Date(xAxis.dataMin);
        const xDataMax = new Date(xAxis.dataMax);
        xStart = new Intl.DateTimeFormat('en-GB', {day:'numeric', month: 'long', year:'numeric'}).format(xDataMin)
        xEnd = new Intl.DateTimeFormat('en-GB', {day:'numeric', month: 'long', year:'numeric'}).format(xDataMax)
    }
    if (yAxis.type.toLowerCase() === "datetime"){
        const yDataMin = new Date(yAxis.dataMin);
        const yDataMax = new Date(yAxis.dataMax);
        yStart = new Intl.DateTimeFormat('en-GB', {day:'numeric', month: 'long', year:'numeric'}).format(yDataMin)
        yEnd = new Intl.DateTimeFormat('en-GB', {day:'numeric', month: 'long', year:'numeric'}).format(yDataMax)
    }
    const xAxisInfo = `x Axis,${xAxis.title},from ${xStart} to ${xEnd}`;
    const yAxisInfo = `y Axis,${yAxis.title},from ${yStart} to ${yEnd}`;
    return `${title}. ${xAxisInfo}. ${yAxisInfo}`;
}
