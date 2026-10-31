/**
 * FitVision Advanced Pose Matching & Action Recognition Engine
 * Based on skeletal vector similarity and OneEuroFilter smoothing.
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

    constructor(
        private minCutoff: number = 1.0, 
        private beta: number = 0.0, 
        private dCutoff: number = 1.0
    ) {}

    private alpha(cutoff: number, deltaT: number): number {
        const tau = 1.0 / (2 * Math.PI * cutoff);
        return 1.0 / (1.0 + tau / deltaT);
    }

    filter(value: number, timestamp: number): number {
        if (this.lastTime === null) {
            this.lastValue = value;
            this.lastTime = timestamp;
            return value;
        }

        const deltaT = (timestamp - this.lastTime) / 1000.0;
        const dValue = (value - this.lastValue!) / deltaT;
        const dAlpha = this.alpha(this.dCutoff, deltaT);
        const filteredDValue = this.lastDerivValue === null ? dValue : dAlpha * dValue + (1 - dAlpha) * this.lastDerivValue;
        
        const cutoff = this.minCutoff + this.beta * Math.abs(filteredDValue);
        const a = this.alpha(cutoff, deltaT);
        const filteredValue = a * value + (1 - a) * this.lastValue!;

        this.lastValue = filteredValue;
        this.lastDerivValue = filteredDValue;
        this.lastTime = timestamp;
        return filteredValue;
    }
}

/**
 * PoseNormalization: Normalizes landmarks based on torso length.
 * Makes the algorithm invariant to camera-to-person distance.
 */
export function normalizeLandmarks(landmarks: Point[]) {
    // MediaPipe indices: 11(L shoulder), 12(R shoulder), 23(L hip), 24(R hip)
    const midShoulder = {
        x: (landmarks[11].x + landmarks[12].x) / 2,
        y: (landmarks[11].y + landmarks[12].y) / 2
    };
    const midHip = {
        x: (landmarks[23].x + landmarks[24].x) / 2,
        y: (landmarks[23].y + landmarks[24].y) / 2
    };
    
    // Torso length as the scaling unit
    const torsoLength = Math.sqrt(
        Math.pow(midShoulder.x - midHip.x, 2) + Math.pow(midShoulder.y - midHip.y, 2)
    );

    return landmarks.map(p => ({
        x: (p.x - midHip.x) / torsoLength,
        y: (p.y - midHip.y) / torsoLength,
        z: p.z / torsoLength
    }));
}

/**
 * Geometric Vector Similarity: Calculates cosine similarity between vectors.
 * A more robust way than just simple angles.
 */
export function calculateCosineSimilarity(v1: {x:number,y:number}, v2: {x:number,y:number}) {
    const dot = v1.x * v2.x + v1.y * v2.y;
    const mag1 = Math.sqrt(v1.x*v1.x + v1.y*v1.y);
    const mag2 = Math.sqrt(v2.x*v2.x + v2.y*v2.y);
    return dot / (mag1 * mag2);
}

/**
 * Calculates the angle between three points in degrees (2D).
 * @param a Point A (start)
 * @param b Point B (vertex)
 * @param c Point C (end)
 */
export function calculateAngle(a: Point, b: Point, c: Point) {
    if (!a || !b || !c || a.visibility! < 0.5 || b.visibility! < 0.5 || c.visibility! < 0.5) return null;
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    if (angle > 180.0) angle = 360 - angle;
    return angle;
}

/**
 * Reference Pose Database (Signature Based)
 * Based on crowdsourced optimal form data.
 */
export const ExerciseSignatures = {
    // SQUAT bottom phase signature
    squat_down: {
        // Pairs of indices forming a vector (e.g., [24, 26] is Hip -> Knee)
        vectors: [
            { from: 24, to: 26, weight: 1.0 }, // Thigh segment
            { from: 26, to: 28, weight: 0.8 }, // Shin segment
            { from: 12, to: 24, weight: 0.5 }  // Back segment
        ],
        // Normalized target directions (approximate)
        targets: [
            { x: 0.8, y: 0.6 },  // Thigh angled down
            { x: 0.2, y: 0.98 }, // Shin nearly vertical
            { x: 0.1, y: -0.99 } // Back straight/upright
        ]
    },
    pushup_down: {
        vectors: [
            { from: 12, to: 14, weight: 1.0 }, // Upper arm
            { from: 14, to: 16, weight: 0.8 }, // forearm
            { from: 12, to: 24, weight: 0.7 }  // Trunk
        ],
        targets: [
          { x: 0.9, y: 0.4 },
          { x: 0.1, y: 0.98 },
          { x: 0.95, y: -0.1 }
        ]
    },
    plank: {
        vectors: [
            { from: 11, to: 23, weight: 1.0 }, // Torso
            { from: 23, to: 27, weight: 1.0 }, // Thigh (Left)
            { from: 24, to: 28, weight: 1.0 }  // Thigh (Right)
        ],
        targets: [
            { x: 1.0, y: 0.0 }, // Horizontal
            { x: 1.0, y: 0.0 },
            { x: 1.0, y: 0.0 }
        ]
    },
    jumping_jack_up: {
        vectors: [
            { from: 11, to: 15, weight: 1.0 }, // Right arm
            { from: 12, to: 16, weight: 1.0 }, // Left arm
            { from: 23, to: 27, weight: 0.8 }, // Right leg
            { from: 24, to: 28, weight: 0.8 }  // Left leg
        ],
        targets: [
            { x: 0.5, y: -0.8 }, 
            { x: -0.5, y: -0.8 },
            { x: 0.5, y: 0.8 },
            { x: -0.5, y: 0.8 }
        ]
    }
};

/**
 * Advanced Pose Signature Matching
 * Compares current normalized body vectors against a target signature.
 * Returns a score from 0.0 to 1.0
 */
export function matchPoseSignature(normalizedLandmarks: Point[], signatureKey: keyof typeof ExerciseSignatures) {
    const signature = ExerciseSignatures[signatureKey];
    let totalScore = 0;
    let totalWeight = 0;

    signature.vectors.forEach((v, idx) => {
        const from = normalizedLandmarks[v.from];
        const to = normalizedLandmarks[v.to];
        const target = signature.targets[idx];

        if (from && to) {
            const currentVec = {
                x: to.x - from.x,
                y: to.y - from.y
            };
            const similarity = calculateCosineSimilarity(currentVec, target);
            // Map similarity [-1, 1] to [0, 1]
            const score = (similarity + 1) / 2;
            totalScore += score * v.weight;
            totalWeight += v.weight;
        }
    });

    return totalWeight > 0 ? totalScore / totalWeight : 0;
}
