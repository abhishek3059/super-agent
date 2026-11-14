# Stop playback across the provider boundary

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Evidence | [PH-01 offline fixes](../implementation/r01-10-acceptance.md#offline-fixes) |

The browser and bridge can clear playback before a provider finishes
the old turn. Advancing the browser epoch alone lets late provider PCM
look fresh. Test the local acknowledgement, late PCM, terminal provider
event, and next turn in that order.

The native diagnostic now distinguishes a provider interruption event
from natural completion. An in-process SDK test proves local event
ordering. It does not prove live provider behavior.
