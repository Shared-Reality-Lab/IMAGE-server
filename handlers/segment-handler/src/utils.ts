export function generateEmptyResponse(requestUUID: string): { "request_uuid": string, "timestamp": number, "renderings": Record<string, unknown>[] } {
    return {
        "request_uuid": requestUUID,
        "timestamp": Math.round(Date.now() / 1000),
        "renderings": []
    };
}

type V2 = [number, number];

class V3 {
    x: number;
    y: number;
    z: number;

    constructor(x: number, y: number, z=0) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    mag(): number {
        return Math.hypot(this.x, this.y, this.z);
    }

    cross(b: V3): V3 {
        return new V3(
            this.y * b.z - this.z * b.y,
            this.z * b.x - this.x * b.z,
            this.x * b.y - this.y * b.x
        );
    }
}

/** Returns an angle between a reference point and another point on the contour with respect to the centroid. */
export function getContourRefAngle(center: V2, reference: V2, point: V2): number {
    const a = new V3(reference[0] - center[0], reference[1] - center[1]);
    const b = new V3(point[0] - center[0], point[1] - center[1]);
    return Math.asin(a.cross(b).mag() / (a.mag() * b.mag()));
}
