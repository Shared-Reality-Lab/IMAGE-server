import Docker from "dockerode";

export const docker = new Docker();
const _PREPROCESSOR_LABEL_ = "ca.mcgill.cim.bach.atp.preprocessor";
const _HANDLER_LABEL_ = "ca.mcgill.cim.bach.atp.handler";

export function getPreprocessorServices(containers: Docker.ContainerInfo[]) {
    const activePreprocessors = containers.filter(container => {
        return (container.State === "running") && (container.Labels[_PREPROCESSOR_LABEL_]);
    });
    return activePreprocessors.sort((first, second) => {
        const firstNum = Number(first.Labels[_PREPROCESSOR_LABEL_]);
        const secondNum = Number(second.Labels[_PREPROCESSOR_LABEL_]);
        return firstNum - secondNum;
    }).map(container => { return container.Labels["com.docker.compose.service"]; });
}

export function getHandlerServices(containers: Docker.ContainerInfo[]) {
    const activeHandlers = containers.filter(container => {
        return (container.State === "running") && (container.Labels[_HANDLER_LABEL_]) && (container.Labels[_HANDLER_LABEL_] === "enable");
    });
    return activeHandlers.map(container => { return container.Labels["com.docker.compose.service"]; });
}
