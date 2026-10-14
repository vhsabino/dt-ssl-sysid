# dtssl MJCF route b (mujoco-rollers) — 2 robots

model: `dtssl-route-b`

## option

| key | value |
|---|---|
| cone | elliptic |
| gravity | 0 0 -9.81 |
| impratio | 10 |
| integrator | Euler |
| iterations | 100 |
| noslip_iterations | 1 |
| solver | Newton |
| timestep | 0.00208333 |

## bodies (rollers collapsed)

| body | geoms | mass (kg) | joints |
|---|---|---|---|
| field_lines | 47 | 0 |  |
| goal_left | 3 | 0 |  |
| goal_right | 3 | 0 |  |
| boundary | 4 | 0 |  |
| ball | 1 | 0.046 | ball_root (free) |
| blue_0 | 8 | 2.4 | blue_0_root (free) |
| blue_0_wheel0 | 1 | 0.15 | blue_0_wheel0 (hinge) |
| blue_0_wheel1 | 1 | 0.15 | blue_0_wheel1 (hinge) |
| blue_0_wheel2 | 1 | 0.15 | blue_0_wheel2 (hinge) |
| blue_0_wheel3 | 1 | 0.15 | blue_0_wheel3 (hinge) |
| yellow_0 | 8 | 2.4 | yellow_0_root (free) |
| yellow_0_wheel0 | 1 | 0.15 | yellow_0_wheel0 (hinge) |
| yellow_0_wheel1 | 1 | 0.15 | yellow_0_wheel1 (hinge) |
| yellow_0_wheel2 | 1 | 0.15 | yellow_0_wheel2 (hinge) |
| yellow_0_wheel3 | 1 | 0.15 | yellow_0_wheel3 (hinge) |
| … 96 roller bodies (`*_roller<j>`, free hinge, ellipsoid) | | | |

## actuators

| name | type | joint | gain/range |
|---|---|---|---|
| blue_0_act_wheel0 | velocity | blue_0_wheel0 | 0.1 -1.5 1.5 |
| blue_0_act_wheel1 | velocity | blue_0_wheel1 | 0.1 -1.5 1.5 |
| blue_0_act_wheel2 | velocity | blue_0_wheel2 | 0.1 -1.5 1.5 |
| blue_0_act_wheel3 | velocity | blue_0_wheel3 | 0.1 -1.5 1.5 |
| yellow_0_act_wheel0 | velocity | yellow_0_wheel0 | 0.1 -1.5 1.5 |
| yellow_0_act_wheel1 | velocity | yellow_0_wheel1 | 0.1 -1.5 1.5 |
| yellow_0_act_wheel2 | velocity | yellow_0_wheel2 | 0.1 -1.5 1.5 |
| yellow_0_act_wheel3 | velocity | yellow_0_wheel3 | 0.1 -1.5 1.5 |

## sites

`centre_mark`, `blue_0_dribbler`, `blue_0_kicker`, `yellow_0_dribbler`, `yellow_0_kicker`

## compiled sizes

nbody=112 njnt=107 nq=125 nv=122 nu=8 ngeom=179 nsite=5 timestep=0.00208333
