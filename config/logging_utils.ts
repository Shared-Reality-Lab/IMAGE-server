// https://medium.com/@jaiprajapati3/masking-of-sensitive-data-in-logs-700850e233f5
import winston from "winston";
import * as dotenv from "dotenv";

dotenv.config(); 
const PII_LOG_LEVEL = 5;

const levels = {
    error: 0,
    warn: 1,
    info: 2,
    debug: 3,
    pii: PII_LOG_LEVEL 
};

// log format (timestamp + message)
const logFormat = winston.format.printf(({ timestamp, level, message }) => {
    return `${timestamp} [${level.toUpperCase()}]: ${message}`;
});

// create the logger instance
const logger = winston.createLogger({
    levels,
    format: winston.format.combine(
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        logFormat
    ),
    transports: [new winston.transports.Console()]
});

// custom PII log-level method, only log when enabled
logger.pii = (message: string) => {
    if (process.env.PII_LOGGING_ENABLED === "true") {
        logger.log("pii", message);
    }
};

export function configureLogging(): void {
    const logLevel = process.env.LOG_LEVEL?.toLowerCase() || "info";
    const piiLoggingEnabled = process.env.PII_LOGGING_ENABLED === "true";

    // set the base logging level
    logger.level = levels.hasOwnProperty(logLevel) ? logLevel : "info";

    if (piiLoggingEnabled) {
        logger.warn("Environment Unicorn: PII logging enabled!");
        logger.level = "pii";
    } else {
        logger.info("Environment Pegasus: PII logging is disabled.");
    }
}

export default logger;
