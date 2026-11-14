/**
 * Tracks backend playback epochs so stale model audio cannot resume after an
 * interruption.
 *
 * The backend tags every JSON `audio.chunk` and `playback.interrupted` event
 * with the epoch that owns the following output. Binary frames carry no epoch
 * marker, so a binary frame is accepted only when a matching tagged JSON chunk
 * arrived first and no interrupt is pending. Untagged or epoch-mismatched
 * binary frames are dropped.
 */
export class PlaybackEpochTracker {
  private current = 0;
  private pending?: number;
  private expected?: number;

  get currentEpoch(): number {
    return this.current;
  }

  onReady(epoch: number | undefined): void {
    if (typeof epoch === 'number' && epoch >= this.current) this.current = epoch;
  }

  /** Records the epoch announced for the next binary frame. */
  onChunkMeta(epoch: number | undefined): void {
    this.expected = typeof epoch === 'number' ? epoch : undefined;
  }

  /** Called when the user interrupts; the next epoch is not auditable yet. */
  onLocalInterrupt(): void {
    this.pending = (this.pending ?? this.current) + 1;
  }

  /** The backend acknowledges an interrupt with its new epoch. */
  onServerInterrupt(epoch: number | undefined): void {
    if (typeof epoch === 'number' && epoch >= this.current) this.current = epoch;
    if (typeof epoch === 'number' && (this.pending === undefined || epoch >= this.pending)) {
      this.pending = undefined;
    }
    this.expected = undefined;
  }

  onTurnComplete(epoch: number | undefined): void {
    if (typeof epoch === 'number' && epoch >= this.current) {
      this.current = epoch;
      if (this.pending === undefined || epoch >= this.pending) this.pending = undefined;
    }
  }

  /** Consumes one pending chunk tag; returns whether the binary frame may play. */
  acceptBinary(): boolean {
    const expected = this.expected;
    this.expected = undefined;
    return (
      expected !== undefined &&
      expected === this.current &&
      this.pending === undefined
    );
  }
}
