/*
 * Copyright (c) 2024 IMAGE Project, Shared Reality Lab, McGill University
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

import { Client } from "memjs";
import hash from "object-hash";

/** Server cache implementation for IMAGE based on memjs :  https://memjs.netlify.app/ */
export class ServerCache {
    memjsClient : Client;
    constructor(){
        this.memjsClient = Client.create();
    }
    async getResponseFromCache(hashedKey: string){
        const cacheResponse = await this.memjsClient.get(hashedKey);
        return cacheResponse && cacheResponse.value?.toString(); 
    }
    
    async setResponseInCache(hashedKey: string, value: string, timeout: number){
        console.debug(`storing data in memcache with key ${hashedKey}`);
        await this.memjsClient.set(hashedKey, value, {expires: timeout});
    }
    
    constructCacheKey(data: Record<string, unknown>, preprocessor: string): string{
        // const reqCapabilities = data["capabilities"] as string[];
        // const isDebugMode = reqCapabilities && reqCapabilities.includes("ca.mcgill.a11y.image.capability.DebugMode");
        let reqData : string | object = "";
        if(data["graphic"]){
            reqData = data["graphic"] as string;
        } else if (data["placeID"]) {
            reqData = data["placeID"] as string;
        } else if (data["coordinates"]){
            reqData = data["coordinates"] as object;
        } else if(data["highChartsData"]){
            reqData = data["highChartsData"] as object;
        }
        const cacheKeyData = {"reqData": reqData, "preprocessor": preprocessor}
        return hash(cacheKeyData);
    }
}