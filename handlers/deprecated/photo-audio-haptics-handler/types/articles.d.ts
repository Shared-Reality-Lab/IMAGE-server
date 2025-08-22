declare module "articles" {
    export function articlize(...inputs: string[]): string|string[];
    export function find(word: string, obj?: Record<string, unknown>, article?: string): string;
}
