// https://medium.com/@jaiprajapati3/masking-of-sensitive-data-in-logs-700850e233f5
import winston from "winston";

const PII_LOG_LEVEL = 5;
const levels: Record<string, number> = {
    error: 0,
    warn: 1,
    info: 2,
    debug: 3,
    pii: PII_LOG_LEVEL
};

// extend Winston Logger Type to Include "pii"
interface ExtendedLogger extends winston.Logger {
    pii: (message: string) => void;
}

// create the logger instance
const logger: ExtendedLogger = winston.createLogger({
    levels,
    format: winston.format.combine(
        winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss" }),
        winston.format.printf(({ timestamp, level, message }) => {
            return `${timestamp ?? new Date().toISOString()} [${level.toUpperCase()}]: ${message}`;
        })
    ),
    transports: [new winston.transports.Console()]
}) as ExtendedLogger;

logger.pii = (message: string) => {
    if (process.env.PII_LOGGING_ENABLED === "true") {
        logger.log({
            level: "pii",
            message: message
        });
    }
};

export function configureLogging(): void {
    const logLevel = process.env.LOG_LEVEL?.toLowerCase() || "info";
    const piiLoggingEnabled = process.env.PII_LOGGING_ENABLED === "true";
    if (logLevel in levels) { // ensure levels exists
        logger.level = logLevel;
    } else {
        logger.level = "info"; // default if logLevel is invalid
    }

    if (piiLoggingEnabled) {
        logger.warn("Environment Unicorn: PII logging enabled!");
        logger.level = "pii";
    } else {
        logger.info("Environment Pegasus: PII logging is disabled.");
    }
}

export default logger;
