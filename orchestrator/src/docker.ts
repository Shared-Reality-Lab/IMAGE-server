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
import { PreprocessorInfo } from "./server";
import Docker from "dockerode";

export const docker = new Docker();

const _REQUIRED_LABEL_ = "ca.mcgill.a11y.image.required_dependencies";
const _OPTIONAL_LABEL_ = "ca.mcgill.a11y.image.optional_dependencies";
const _PREPROCESSOR_LABEL_ = "ca.mcgill.a11y.image.preprocessor";
const _HANDLER_LABEL_ = "ca.mcgill.a11y.image.handler";
const _PORT_LABEL_ = "ca.mcgill.a11y.image.port";
const _CACHE_TIMEOUT_LABEL = "ca.mcgill.a11y.image.cacheTimeout";
const _ORCHESTRATOR_ID_ = process.env.HOSTNAME as string;
export const DEFAULT_ROUTE_NAME = "default";
const _ROUTE_LABEL_ = "ca.mcgill.a11y.image.route";
const _MODIFY_REQUEST_LABEL_ = "ca.mcgill.a11y.image.modifyRequest";

function getOrchestratorNetworks(containers: Docker.ContainerInfo[]): string[] {
    const container = containers.filter(c => c.Id.startsWith(_ORCHESTRATOR_ID_)).shift();
    if (container) {
        return Object.values(container.NetworkSettings.Networks).map(a => a.NetworkID);
    } else {
        console.error("Could not find the orchestrator container! This should not happen!");
        return [];
    }
}

//Returns the containers that running and share a network with the Orchestrator's networks 
export function getFilteredContainers(containers: Docker.ContainerInfo[]) : Docker.ContainerInfo[] {
    //Get the networks that the Orchestrator is connected to 
    const orchestratorNetworks = getOrchestratorNetworks(containers);
    //filter through the containers list and check which are connected to any of the orchestrator networks 
    const filteredContainers = containers.filter(container => {
        //network of container
        const networks = container.NetworkSettings.Networks || {};
        //get network id of the container
        const containerNetworkIds = Object.values(networks).map(net => net.NetworkID);
        //return the container if one of its IDs is part of the orchestrator networks
        const isInTargetNetwork = containerNetworkIds.some(id => orchestratorNetworks.includes(id));
        return isInTargetNetwork;
    });
    //Only return the containers that are running 
    return filteredContainers.filter(c => c.State === "running");  
}

function isPartOfRoute(container: Docker.ContainerInfo, route: string) {
    const containerName = container.Labels["com.docker.compose.service"];
    if (container.Labels[_ROUTE_LABEL_] !== undefined) {
        const routeString = container.Labels[_ROUTE_LABEL_];
        if (/^\w+(,\w+)*$/.test(routeString)) {
            const routes = container.Labels[_ROUTE_LABEL_].split(",");
            console.debug(containerName + " has routes " + routes);
            return routes.includes(route);
        }
        console.warn("String " + routeString + " is not a valid route label (" + containerName + ")");
    }
    // Fallback case - should not be reached when a valid route label is set
    console.info("Using default route (\"" + DEFAULT_ROUTE_NAME + "\") for " + containerName);
    return route === DEFAULT_ROUTE_NAME;
}

export function getPreprocessorServices(containers: Docker.ContainerInfo[], route: string) {
    const activePreprocessors = containers.filter(container =>
        container.State === "running" &&
        container.Labels[_PREPROCESSOR_LABEL_] &&
        isPartOfRoute(container, route)
    );
    return activePreprocessors.sort((first, second) => {
        const firstNum = Number(first.Labels[_PREPROCESSOR_LABEL_]);
        const secondNum = Number(second.Labels[_PREPROCESSOR_LABEL_]);
        return firstNum - secondNum;
    }).map(container => {
        const portLabel = container.Labels[_PORT_LABEL_];
        const priorityLabel = Number(container.Labels[_PREPROCESSOR_LABEL_]);
        const cacheTimeout = Number(container.Labels[_CACHE_TIMEOUT_LABEL] || 0);
        const modifyRequest = Boolean(container.Labels[_MODIFY_REQUEST_LABEL_] || false);

        let port;
        if (portLabel !== undefined) {
            port = parseInt(portLabel, 10);
            if (isNaN(port)) {
                port = 80;
            }
        } else {
            port = 80;
        }
        return [container.Labels["com.docker.compose.service"], port, priorityLabel, cacheTimeout, modifyRequest];
    });
}

export function getHandlerServices(containers: Docker.ContainerInfo[], route: string) {
    const activeHandlers = containers.filter(container =>
        container.State === "running" &&
        container.Labels[_HANDLER_LABEL_] &&
        container.Labels[_HANDLER_LABEL_] === "enable" &&
        isPartOfRoute(container, route) 
    );

    return activeHandlers.map(container => {
        const portLabel = container.Labels[_PORT_LABEL_];
        let port;
        if (portLabel !== undefined) {
            port = parseInt(portLabel, 10);
            if (isNaN(port)) {
                port = 80;
            }
        } else {
            port = 80;
        }
        return [container.Labels["com.docker.compose.service"], port];
    });
}

//Returns the optional preprocessors/handlers needed for the given preprocessor/handler to run 
//Optional services: enhance functionality but are not strictly required for execution.
export function getOptional(containers: Docker.ContainerInfo[], serviceName: string, servicesArray: PreprocessorInfo[]) : PreprocessorInfo[]{
    try{   
        //Find the container for the service name passed
        const container = containers.find(c => c.Labels?.["com.docker.compose.service"] === serviceName);
        if(!container){
            console.error(`Could not find the container for the service:  ${serviceName}`);
            return [];
        }
        if (container.Labels?.[_OPTIONAL_LABEL_] == undefined) {
            console.warn(`Warning: The optional dependencies label is missing for service:  "${container.Labels["com.docker.compose.service"]}".`);
            return [];
        }
       
        const optionalServices = container.Labels[_OPTIONAL_LABEL_];
        let optionalArr : string[] = [];
        
        //convert from string to array of strings 
        if(optionalServices != ""){    //if the preprocessor has dependencies
            optionalArr = optionalServices ? optionalServices.split(",").filter(Boolean) : [];
        }
        
        //filter through the array of preprocessor & handler names and return an array of their actual values
        return servicesArray.filter(function (p) { return optionalArr.includes(p[0] as string); });
        
    } catch(error){
        console.error(`Error while getting optional dependencies for ${serviceName}:`, error);
        return [];
    }

}

//Returns the required preprocessors/handlers needed for the given preprocessor/handler to run 
export function getRequired(containers: Docker.ContainerInfo[], serviceName: string, servicesArray: PreprocessorInfo[]) : PreprocessorInfo[]{
    try{
        //Find the container for the service name passed
        const container = containers.find(c => c.Labels?.["com.docker.compose.service"] === serviceName);
        if(!container){
            console.error(`Could not find the container for the service: ${serviceName}`);
            return [];
        }
        if (container.Labels?.[_REQUIRED_LABEL_] == undefined) {
            console.warn(`Warning: The required dependencies label is missing for service: "${serviceName}".`);
            return [];
        }

        const requiredServices = container.Labels[_REQUIRED_LABEL_];
        let requiredArr : string[] = [];
        
        //convert from string to array of strings 
        if(requiredServices != ""){    //if the preprocessor/handler has dependencies
            requiredArr = requiredServices.split(",").filter(Boolean);
        }
        
        //filter through the array of preprocessor & handler names and return an array of their actual values
        return servicesArray.filter(function (p) { return requiredArr.includes(p[0] as string); });
    } catch(error){
        console.error(`Error while getting required dependencies for ${serviceName}:`, error);
        return [];
    }
} 

