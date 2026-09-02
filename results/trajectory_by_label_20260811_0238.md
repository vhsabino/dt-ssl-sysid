# Trajectory overlay by label - 20260811_0238

Window selection: per label, argmax( min(e_ideal, e_rsim) - e_twin ) at h = 1.5 s,
i.e. the window with the largest twin margin over the BEST competing plant.
This is a per-label BEST CASE, not the median window. Declared in the caption.

| label | event | window | in hold-out | twin (m) | ideal (m) | rSim (m) |
|---|---|---|---|---|---|---|
| front_to_back | `front_to_back_01_01` | 19 | yes | 0.0039 | 0.2902 | 0.3262 |
| shoot_to_goal | `shoot_to_goal_09_01` | 12 | yes | 0.1804 | 1.2008 | 1.0299 |
| side_to_side | `side_to_side_01_06` | 13 | yes | 0.0564 | 0.6664 | 0.7218 |
| square | `square_01_02` | 15 | **no** | 0.1544 | 0.5619 | 0.6655 |

The frozen hold-out (config/holdout_events.json) contains no `square` event
(1 front_to_back, 4 side_to_side, 5 shoot_to_goal), so the square panel is drawn
from an event outside the hold-out and is marked as such in the figure.
