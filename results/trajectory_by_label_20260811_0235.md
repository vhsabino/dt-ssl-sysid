# Trajectory overlay by label — 20260811_0235

Window selection: per label, argmax(e_ideal - e_twin) at h = 1.5 s.
This is a per-label BEST CASE, not the median window.

| label | event | window | in hold-out | twin (m) | ideal (m) | rSim (m) |
|---|---|---|---|---|---|---|
| front_to_back | `front_to_back_01_01` | 19 | yes | 0.0039 | 0.2902 | 0.3262 |
| shoot_to_goal | `shoot_to_goal_12_01` | 19 | yes | 0.5587 | 1.6384 | 0.5225 |
| side_to_side | `side_to_side_01_06` | 13 | yes | 0.0564 | 0.6664 | 0.7218 |
| square | `square_01_05` | 6 | **no** | 0.0088 | 0.4163 | 0.3448 |

The frozen hold-out contains no `square` event, so that panel is drawn from an event outside the hold-out and is labelled as such.
