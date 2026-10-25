/** Bounded dynamic-programming scheduler for self-describing grammar variants.
 * Selection of a template for aesthetic reasons DOES NOT add payload bits.
 * Each selected marker must be explicit and independently decoded by a carrier.
 */
export interface CapacityChoice {
  readonly id: string;
  readonly bits: number;
  /** Non-negative integer cost in abstract quality/word units. */
  readonly cost: number;
}
export interface ScheduledChunk {
  readonly id: string;
  readonly capacityBits: number;
  readonly usedBits: number;
  readonly paddingBits: number;
  readonly startBit: number;
}
export interface ScheduleOptions {
  readonly paddingCost?: number;
}

export function scheduleSentenceCapacities(
  totalBits: number, choices: readonly CapacityChoice[], options: ScheduleOptions = {}
): readonly ScheduledChunk[] {
  if (!Number.isSafeInteger(totalBits) || totalBits < 0 || totalBits > 50_000 ||
      !Array.isArray(choices) || choices.length < 1 || choices.length > 16 ||
      choices.some(c => !/^[a-z][a-z0-9-]{0,63}$/.test(c.id) ||
        !Number.isSafeInteger(c.bits) || c.bits < 1 || c.bits > 256 ||
        !Number.isSafeInteger(c.cost) || c.cost < 1 || c.cost > 100000) ||
      new Set(choices.map(c => c.id)).size !== choices.length) {
    throw new TypeError('Invalid sentence scheduling problem');
  }
  const padCost = options.paddingCost ?? 2;
  if (!Number.isSafeInteger(padCost) || padCost < 0 || padCost > 100000) {
    throw new TypeError('Invalid padding penalty');
  }
  const best = new Float64Array(totalBits + 1).fill(Infinity);
  const selected = new Int16Array(totalBits + 1).fill(-1);
  best[totalBits] = 0;
  for (let offset = totalBits - 1; offset >= 0; offset--) {
    for (let i = 0; i < choices.length; i++) {
      const c = choices[i]!;
      const end = Math.min(totalBits, offset + c.bits);
      const unused = c.bits - (end - offset);
      const cost = c.cost + padCost * unused + best[end]!;
      // Stable lexical tie-break: caller order determines choices of equal cost.
      if (cost < best[offset]!) { best[offset] = cost; selected[offset] = i; }
    }
  }
  const schedule: ScheduledChunk[] = [];
  for (let offset = 0; offset < totalBits;) {
    const c = choices[selected[offset]!]!;
    const used = Math.min(totalBits - offset, c.bits);
    schedule.push(Object.freeze({ id: c.id, capacityBits: c.bits,
      usedBits: used, paddingBits: c.bits - used, startBit: offset }));
    offset += used;
  }
  return Object.freeze(schedule);
}
