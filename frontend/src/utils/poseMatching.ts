/**
 * Shared pose utilities: OneEuroFilter smoothing and torso-length normalisation.
 * Action recognition lives in `poseRecognition.ts`.
 */

export interface Point {
    x: number;
    y: number;
    z: number;
    visibility?: number;
}

/**
 * OneEuroFilter: A lightweight filter for reducing jitter in real-time signals.
 * Excellent for smoothing pose landmarks while maintaining low latency.
 */
export class OneEuroFilter {
    private lastValue: number | null = null;
    private lastDerivValue: number | null = null;
    private lastTime: number | null = null;
    private minCutoff: number;
    private beta: number;
    private dCutoff: number;

    constructor(minCutoff = 1.0, beta = 0.0, dCutoff = 1.0) {
        this.minCutoff = minCutoff;
        this.beta = beta;
        this.dCutoff = dCutoff;
    }

    private alpha(cutoff: number, deltaT: number): number {
        const tau = 1.0 / (2 * Math.PI * cutoff);
        return 1.0 / (1.0 + tau / deltaT);
    }

    filter(value: number, timestamp: number): number {
        if (!Number.isFinite(value)) {
            return this.lastValue ?? 0;
        }

        if (this.lastTime === null || this.lastValue === null) {
            this.lastValue = value;
            this.lastTime = timestamp;
            return value;
        }

        const deltaT = (timestamp - this.lastTime) / 1000.0;
        // Duplicate or out-of-order frames would make the derivative explode.
        if (!Number.isFinite(deltaT) || deltaT <= 0) {
            this.lastTime = timestamp;
            return this.lastValue;
        }

        const dValue = (value - this.lastValue) / deltaT;
        const dAlpha = this.alpha(this.dCutoff, deltaT);
        const filteredDValue = this.lastDerivValue === null ? dValue : dAlpha * dValue + (1 - dAlpha) * this.lastDerivValue;

        const cutoff = this.minCutoff + this.beta * Math.abs(filteredDValue);
        const a = this.alpha(cutoff, deltaT);
        const filteredValue = a * value + (1 - a) * this.lastValue;

        this.lastValue = filteredValue;
        this.lastDerivValue = filteredDValue;
        this.lastTime = timestamp;
        return filteredValue;
    }

    reset() {
        this.lastValue = null;
        this.lastDerivValue = null;
        this.lastTime = null;
    }
}

/**
 * PoseNormalization: Normalizes landmarks based on torso length.
 * Makes the algorithm invariant to camera-to-person distance.
 */
export function normalizeLandmarks(landmarks: Point[]) {
    if (!landmarks || landmarks.length < 25) return landmarks;

    // MediaPipe indices: 11(L shoulder), 12(R shoulder), 23(L hip), 24(R hip)
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];
    if (!leftShoulder || !rightShoulder || !leftHip || !rightHip) return landmarks;

    const midShoulder = {
        x: (leftShoulder.x + rightShoulder.x) / 2,
        y: (leftShoulder.y + rightShoulder.y) / 2
    };
    const midHip = {
        x: (leftHip.x + rightHip.x) / 2,
        y: (leftHip.y + rightHip.y) / 2
    };

    // Torso length as the scaling unit; never divide by zero on a collapsed pose.
    const torsoLength = Math.max(
        1e-6,
        Math.sqrt(
            Math.pow(midShoulder.x - midHip.x, 2) + Math.pow(midShoulder.y - midHip.y, 2)
        )
    );

    return landmarks.map(p => ({
        x: (p.x - midHip.x) / torsoLength,
        y: (p.y - midHip.y) / torsoLength,
        z: p.z / torsoLength
    }));
}

