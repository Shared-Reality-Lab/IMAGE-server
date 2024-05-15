import { Client } from "memjs";
import hash from "object-hash";

/** Server cache implementation for IMAGE based on memcached:  */
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
        const reqCapabilities = data["capabilities"] as string[];
        const isDebugMode = reqCapabilities && reqCapabilities.includes("ca.mcgill.a11y.image.capability.DebugMode");
        let reqData : string | object = "";
        if(data["graphic"]){
            reqData = data["graphic"];
        } else if (data["placeID"]) {
            reqData = data["placeID"];
        } else if (data["coordinates"]){
            reqData = data["coordinates"];
        } else if(data["highChartsData"]){
            reqData = data["highChartsData"];
        }
        const cacheKeyData = {"reqData": reqData, "preprocessor": preprocessor, "debugMode":isDebugMode}
        return hash(cacheKeyData);
    }
}