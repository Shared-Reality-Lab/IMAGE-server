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
import Docker from "dockerode";

export const docker = new Docker();
const _PREPROCESSOR_LABEL_ = "ca.mcgill.a11y.image.preprocessor";
const _HANDLER_LABEL_ = "ca.mcgill.a11y.image.handler";
const _PORT_LABEL_ = "ca.mcgill.a11y.image.port";
const _CACHE_TIMEOUT_LABEL = "ca.mcgill.a11y.image.cacheTimeout";
const _ORCHESTRATOR_ID_ = process.env.HOSTNAME as string;
export const DEFAULT_ROUTE_NAME = "default";
const _ROUTE_LABEL_ = "ca.mcgill.a11y.image.route";

function getOrchestratorNetworks(containers: Docker.ContainerInfo[]): string[] {
    const container = containers.filter(c => c.Id.startsWith(_ORCHESTRATOR_ID_)).shift();
    if (container) {
        return Object.values(container.NetworkSettings.Networks).map(a => a.NetworkID);
    } else {
        console.error("Could not find the orchestrator container! This should not happen!");
        return [];
    }
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
    const orchestratorNetworks = getOrchestratorNetworks(containers);
    const activePreprocessors = containers.filter(container => {
        const matchingNetworks = Object.values(container.NetworkSettings.Networks)
                                    .filter(network => orchestratorNetworks.includes(network.NetworkID));
        return (container.State === "running") && (container.Labels[_PREPROCESSOR_LABEL_]) && (matchingNetworks.length > 0) && isPartOfRoute(container, route);
    });
    return activePreprocessors.sort((first, second) => {
        const firstNum = Number(first.Labels[_PREPROCESSOR_LABEL_]);
        const secondNum = Number(second.Labels[_PREPROCESSOR_LABEL_]);
        return firstNum - secondNum;
    }).map(container => {
        const portLabel = container.Labels[_PORT_LABEL_];
        const priorityLabel = Number(container.Labels[_PREPROCESSOR_LABEL_]);
        const cacheTimeout = Number(container.Labels[_CACHE_TIMEOUT_LABEL] || 0);

        let port;
        if (portLabel !== undefined) {
            port = parseInt(portLabel, 10);
            if (isNaN(port)) {
                port = 80;
            }
        } else {
            port = 80;
        }
        return [container.Labels["com.docker.compose.service"], port, priorityLabel, cacheTimeout];
    });
}

export function getHandlerServices(containers: Docker.ContainerInfo[], route: string) {
    const orchestratorNetworks = getOrchestratorNetworks(containers);
    const activeHandlers = containers.filter(container => {
        const matchingNetworks = Object.values(container.NetworkSettings.Networks)
                                    .filter(network => orchestratorNetworks.includes(network.NetworkID));
        return (container.State === "running") && (container.Labels[_HANDLER_LABEL_]) && (container.Labels[_HANDLER_LABEL_] === "enable") && (matchingNetworks.length > 0) && isPartOfRoute(container, route);
    });
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
