import express from "express";
import path from "path";
import { validate, version } from "uuid";
import { BASE_LOG_PATH } from "./pipeline";

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{43}$/;

export function mcpAudioHandler(basePath = BASE_LOG_PATH) {
    return (req: express.Request, res: express.Response) => {
        const { uuid, token } = req.params;
        if (!validate(uuid) || version(uuid) !== 4 || !TOKEN_PATTERN.test(token)) {
            res.sendStatus(404);
            return;
        }
        res.type("audio/mpeg").set("Accept-Ranges", "bytes");
        res.sendFile(path.join(uuid, "mcp-audio", `${token}.mp3`), { root: basePath, dotfiles: "deny" }, error => {
            if (!error) {
                return;
            }
            const fileError = error as NodeJS.ErrnoException & { status?: number };
            if (fileError.code === "ENOENT" || fileError.status === 404) {
                res.sendStatus(404);
                return;
            }
            console.error(`Unable to serve MCP audio artifact for request ${uuid}:`, error);
            if (!res.headersSent) {
                res.sendStatus(500);
            }
        });
    };
}
