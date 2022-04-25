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
    contourPoints: [number, number];
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
    // Point location and contour data
    const posData: segGeometryInfo[] = [];
    ttsData.push({ "value": "contains the following outlines of regions:", "type": "text" });
    for (const segment of segments) {
        const newSeg = segment;
        newSeg["value"] = (newSeg["name"] as string) + ",";
        newSeg["type"] = "segment";
        newSeg["label"] = newSeg["name"] as string;

        const coord = segment["contours"] as [number, number];
        const centroid = segment["centroid"] as [number, number];
        const locSeg = {
            "centroid": centroid,
            "contourPoints": coord
        };
        ttsData.push(newSeg as TTSSegment);
        posData.push(locSeg as segGeometryInfo);
    }
    ttsData[ttsData.length - 1]["value"] = ttsData[ttsData.length - 1]["value"].replace(",", ".");
    ttsData[ttsData.length - 1]["value"] = "and " + ttsData[ttsData.length - 1]["value"];
    return [ttsData, posData];
}

export function generateObjDet(objDet: ObjDet, objGroup: ObjGroup): [TTSSegment[], objGeometryInfo[]] {
    const objects: TTSSegment[] = [];
    const hapticObjInfo: objGeometryInfo[] = [];

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

        // Push point and location info by object group
        const centroids: [number, number][] = [];
        const coordinates: [number, number, number, number][] = [];
        objs.map(obj => {
            const centroid = obj["centroid"];
            const coords = obj["dimensions"];
            centroids.push(centroid)
            coordinates.push(coords)
        })
        const geoObjSeg = {
            "centroid": centroids,
            "contourPoints": coordinates
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
                "centroid": [obj["centroid"]],
                "contourPoints": [obj["dimensions"]]
            };
            hapticObjInfo.push(geoObjSeg);
        }
    }
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
        return "A navigable audio-haptic scene of segments and objects detected in the image";
    }
    else if (hasSemseg) {
        return "A navigable audio-haptic scene of segments detected in the image";
    }
    else if(hasObj) {
        return "A navigable audio-haptic scene of objects detected in the image";
    }
    else {
        return "A navigable audio-haptic scene";
    }
}

export function generateContours(JSONObj:any, IDs:number, dim_x:number, dim_y:number){
    var res = new Array(60);
    for (var i = 0; i < res.length; i++) {
        res[i] = new Int8Array(40);
    }
    for (var i = 0 ; i < 60; i++) {
      for (var j = 0; j < 40; j++)  {
        res[i][j] = 0;
      }
    }
    
      for (var j = 0; j < JSONObj.length; j++)  {
        for (var k = 0; k < JSONObj[j].contours.length; k++) {
          var coordarray = new Array();
          for (var i = 0; i < JSONObj[j].contours[k].coordinates.length; i) {
            var s_x = JSONObj[j].contours[k].coordinates[i][0];
            var s_y = JSONObj[j].contours[k].coordinates[i][1]; 
            coordarray.push([s_x, s_y]);
            var t = 0;
            do {
              console.log("t: ", t)
              t++;
              var e_x = JSONObj[j].contours[k].coordinates[(i + t) % JSONObj[j].contours[k].coordinates.length][0];
              var e_y = JSONObj[j].contours[k].coordinates[(i + t) % JSONObj[j].contours[k].coordinates.length][1];
              console.log("s: ", s_x, " e_x: ", e_x);
              var x1 = Math.floor(s_x * dim_x );
              var x2 = Math.floor(e_x * dim_x );
              var y1 = Math.floor(s_y * dim_y );
              var y2 = Math.floor(e_y * dim_y );
              console.log("x1, x2:", x1, " , ", x2)

            } while(x1 == x2 && y1 == y2)
            i = i + t;
          }
        
          var trun_array = new Array();
          for (var i = 0; i < coordarray.length; i++) {
            var s_x = coordarray[i][0];
            var s_y = coordarray[i][1]; 
            
            //eliminate out-of-screen segments
            if (s_x > 1.0 || s_x < 0.0) continue;
            else if (s_y > 1.0 || s_y < 0.0) continue;
            else trun_array.push([s_x, s_y]); // put in only START point (last segment's endpoint would be same to the first point.)
          }
          simplify(trun_array, 0.02);
          //fillmode consideration

            for (var x = 1; x < 59; x++)  {
              for (var y = 1; y < 39; y++)  {
                var px = x / 60.0;
                var py = y / 40.0;
                //console.log (px, py);
                if (isInside(trun_array, trun_array.length, px, py)) res[x][y] = 1;
              }
            }
          
          //console.log(trun_array);
          for (var i = 0; i < trun_array.length; i++) {
            var s_x = Math.floor(trun_array[i][0] * dim_x );
            var s_y = Math.floor(trun_array[i][1] * dim_y ); 
            var e_x = Math.floor(trun_array[(i+1) % trun_array.length][0] * dim_x);
            var e_y = Math.floor(trun_array[(i+1) % trun_array.length][1] * dim_y); 
            if (s_x >= dim_x) s_x = dim_x-1;
            if (s_y >= dim_y) s_y = dim_y-1;
            if (e_x >= dim_x) e_x = dim_x-1;
            if (e_y >= dim_y) e_y = dim_y-1;
            //console.log(s_x, s_y, e_x, e_y);
            //convert and draw lines
            if (s_x == e_x && s_y == e_y) {
              //console.log(s_x, s_y)
              res[s_x][s_y] = 1;
            }
            else if (s_x == e_x)  {
              var x = s_x;
              if (s_y < e_y)  {
                for (var y = s_y; y < e_y; y++)  {
                  //console.log(x, y);
                  res[x][y] = 1;
                }
              }
              else{
                for (var y = s_y; y > e_y; y--)  {
                  res[x][y] = 1;
                }
              }
            }
            else if (s_y == e_y)  {
              var y = s_y;
              if (s_x < e_x)  {
                for (var x = s_x; x < e_x; x++)  {
                  res[x][y] = 1;
                }
              }
              else{
                for (var x = s_x; x > e_x; x--)  {
                  res[x][y] = 1;
                }
              }
            }
            else  {
              // drawing by interpolation, since it's 60*40, 120 points iteration should be enough (LCM)
              for (var t = 0; t < 1; t = t + (1/120.0)) {
                x = Math.floor(s_x * t + e_x * (1.00-t) );
                y = Math.floor(s_y * t + e_y * (1.00-t) );
                res[x][y] = 1;  
              }
            }
          }
        }
      }
    
    return res;

}

function isInside(polygon:number[][], n:number, px:number, py:number)
{
    // There must be at least 3 vertices in polygon[]
    if (n < 3)
    {
        return false;
    } 
    // Create a point for line segment from p to infinite
    var extremex = 999;
    var extremey = py;

    // Count intersections of the above line with sides of polygon
    var count = 0
    var i = 0;
    do
    {
        var next = (i + 1) % n;
        // Check if the line segment from 'p' to 'extreme' intersects with the line
        // segment from 'polygon[i]' to 'polygon[next]'
        if (doIntersect(polygon[i][0], polygon[i][1], polygon[next][0], polygon[next][1], px, py, extremex, extremey))
        {
            // If the point 'p' is collinear with line segment 'i-next', then check if it lies
            // on segment. If it lies, return true, otherwise false
            if (orientation(polygon[i][0], polygon[i][1], px, py, polygon[next][0], polygon[next][1]) == 0)
            {
                return onSegment(polygon[i][0], polygon[i][1], px, py, polygon[next][0], polygon[next][1]);
            }
            count++;
        }
        i = next;
    } while (i != 0);
    // Return true if count is odd, false otherwise
    return (count % 2 == 1); 
}

function doIntersect(p1x:number, p1y:number, q1x:number, q1y:number, p2x:number, p2y:number, q2x:number, q2y:number) {
    // Find the four orientations needed for
    // general and special cases
    var o1 = orientation(p1x, p1y, q1x, q1y, p2x, p2y);
    var o2 = orientation(p1x, p1y, q1x, q1y, q2x, q2y);
    var o3 = orientation(p2x, p2y, q2x, q2y, p1x, p1y);
    var o4 = orientation(p2x, p2y, q2x, q2y, q1x, q1y);
    // General case
    if (o1 != o2 && o3 != o4)
    {
        return true;
    }
      // Special Cases
    // p1, q1 and p2 are collinear and
    // p2 lies on segment p1q1
    if (o1 == 0 && onSegment(p1x, p1y, p2x, p2y, q1x, q1y))
    {
        return true;
    }
    // p1, q1 and p2 are collinear and
    // q2 lies on segment p1q1
    if (o2 == 0 && onSegment(p1x, p1y, q2x, q2y, q1x, q1y))
    {
        return true;
    }
    // p2, q2 and p1 are collinear and
    // p1 lies on segment p2q2
    if (o3 == 0 && onSegment(p2x, p2y, p1x, p1y, q2x, q2y))
    {
        return true;
    }
    // p2, q2 and q1 are collinear and
    // q1 lies on segment p2q2
    if (o4 == 0 && onSegment(p2x, p2y, q1x, q1y, q2x, q2y))
    {
        return true;
    }
    // Doesn't fall in any of the above cases
    return false;
  }

  function orientation(px:number, py:number, qx:number, qy:number, rx:number, ry:number) {
    var val = (qy - py) * (rx - qx) - (qx - px) * (ry - qy);
    if (Math.abs(val) < 0.0000001) {
        return 0; // collinear // very small value: neglect
    }
    return (val > 0) ? 1 : 2; // clock or counterclock wise
  }

  function onSegment(px:number, py:number, qx:number, qy:number, rx:number, ry:number)
  {
    if (qx <= Math.max(px, rx) && qx >= Math.min(px, rx) && qy <= Math.max(py, ry) && qy >= Math.min(py, ry)) {
        return true;
    }
    return false;
  }

  function simplify(points:any, tolerance:number) {
    if (points.length <= 2) return points;
    var sqTolerance = tolerance !== undefined ? tolerance * tolerance : 1;
    points = simplifyDouglasPeucker(points, sqTolerance);
    return points;
  }

  function simplifyDouglasPeucker(points:any, sqTolerance:any) {
    var last = points.length - 1;
  
    var simplified = [points[0]];
    simplifyDPStep(points, 0, last, sqTolerance, simplified);
    simplified.push(points[last]);
  
    return simplified;
  }

  function simplifyDPStep(points:any, first:any, last:any, sqTolerance:any, simplified:any) {
    var maxSqDist = sqTolerance;
    var index;
    for (var i = first + 1; i < last; i++) {
      var sqDist = getSqSegDist(points[i][0], points[i][1], points[first][0], points[first][1], points[last][0], points[last][1]);
      if (sqDist > maxSqDist) {
          index = i;
          maxSqDist = sqDist;
      }
    }
    if (maxSqDist > sqTolerance) {
        if (index - first > 1) simplifyDPStep(points, first, index, sqTolerance, simplified);
        simplified.push(points[index]);
        if (last - index > 1) simplifyDPStep(points, index, last, sqTolerance, simplified);
    }
  }

  function getSqSegDist(px:number, py:number, p1x:number, p1y:number, p2x:number, p2y:number) {
    var x = p1x;
    var y = p1y;
    var dx = p2x - p1x;
    var dy = p2y - p1y;

    if (dx !== 0 || dy !== 0) {
        var t = ((px - x) * dx + (py - y) * dy) / (dx * dx + dy * dy);
        if (t > 1) {
            x = p2x;
            y = p2y;
        } else if (t > 0) {
            x += dx * t;
            y += dy * t;
        }
    }
    dx = px - x;
    dy = py - y;
    return dx * dx + dy * dy;
  }