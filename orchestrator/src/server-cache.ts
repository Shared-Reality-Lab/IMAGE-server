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

interface CacheValue {
    reqData: string | object;
    preprocessor: string; 
    followupQuery?: string 
}

/** Server cache implementation for IMAGE based on memjs :  https://memjs.netlify.app/ */
export class ServerCache {
    memjsClient : Client;
    constructor(){
        this.memjsClient = Client.create();
    }
    async getResponseFromCache(hashedKey: string){
        try{
            const cacheResponse = await this.memjsClient.get(hashedKey);
            return cacheResponse && cacheResponse.value?.toString(); 
        } catch(error){
            console.debug("Error getting response from the cache");
            return undefined;
        }

    }
    
    async setResponseInCache(hashedKey: string, preprocessorType: string, value: Record<string, unknown>, timeout: number){
        console.debug(`storing data in memcache with key ${hashedKey}, name ${preprocessorType}`);
        try{
            await this.memjsClient.set(hashedKey, JSON.stringify({name: preprocessorType, data: value}), {expires: timeout});
        } catch(error){
            console.debug("Error setting response in the cache");
        }
    }
    
    constructCacheKey(data: Record<string, any>, preprocessor: string): string{
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
        const cacheKeyData: CacheValue  = { reqData: reqData, preprocessor: preprocessor };
        if(data["followup"] && data["followup"]["query"]){
            cacheKeyData["followupQuery"] = data["followup"]["query"] as string;
        }
        return hash(cacheKeyData);
    }
}
