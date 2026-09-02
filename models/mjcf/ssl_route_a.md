# dtssl MJCF route a (mujoco-velocity) — 12 robots

model: `dtssl-route-a`

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
| blue_0 | 8 | 2.4 | blue_0_x (slide), blue_0_y (slide), blue_0_yaw (hinge) |
| blue_1 | 8 | 2.4 | blue_1_x (slide), blue_1_y (slide), blue_1_yaw (hinge) |
| blue_2 | 8 | 2.4 | blue_2_x (slide), blue_2_y (slide), blue_2_yaw (hinge) |
| blue_3 | 8 | 2.4 | blue_3_x (slide), blue_3_y (slide), blue_3_yaw (hinge) |
| blue_4 | 8 | 2.4 | blue_4_x (slide), blue_4_y (slide), blue_4_yaw (hinge) |
| blue_5 | 8 | 2.4 | blue_5_x (slide), blue_5_y (slide), blue_5_yaw (hinge) |
| yellow_0 | 8 | 2.4 | yellow_0_x (slide), yellow_0_y (slide), yellow_0_yaw (hinge) |
| yellow_1 | 8 | 2.4 | yellow_1_x (slide), yellow_1_y (slide), yellow_1_yaw (hinge) |
| yellow_2 | 8 | 2.4 | yellow_2_x (slide), yellow_2_y (slide), yellow_2_yaw (hinge) |
| yellow_3 | 8 | 2.4 | yellow_3_x (slide), yellow_3_y (slide), yellow_3_yaw (hinge) |
| yellow_4 | 8 | 2.4 | yellow_4_x (slide), yellow_4_y (slide), yellow_4_yaw (hinge) |
| yellow_5 | 8 | 2.4 | yellow_5_x (slide), yellow_5_y (slide), yellow_5_yaw (hinge) |

## actuators

| name | type | joint | gain/range |
|---|---|---|---|
| blue_0_act_x | velocity | blue_0_x | 1152 -150 150 |
| blue_0_act_y | velocity | blue_0_y | 1152 -150 150 |
| blue_0_act_yaw | velocity | blue_0_yaw | 4.6656 -3 3 |
| blue_1_act_x | velocity | blue_1_x | 1152 -150 150 |
| blue_1_act_y | velocity | blue_1_y | 1152 -150 150 |
| blue_1_act_yaw | velocity | blue_1_yaw | 4.6656 -3 3 |
| blue_2_act_x | velocity | blue_2_x | 1152 -150 150 |
| blue_2_act_y | velocity | blue_2_y | 1152 -150 150 |
| blue_2_act_yaw | velocity | blue_2_yaw | 4.6656 -3 3 |
| blue_3_act_x | velocity | blue_3_x | 1152 -150 150 |
| blue_3_act_y | velocity | blue_3_y | 1152 -150 150 |
| blue_3_act_yaw | velocity | blue_3_yaw | 4.6656 -3 3 |
| blue_4_act_x | velocity | blue_4_x | 1152 -150 150 |
| blue_4_act_y | velocity | blue_4_y | 1152 -150 150 |
| blue_4_act_yaw | velocity | blue_4_yaw | 4.6656 -3 3 |
| blue_5_act_x | velocity | blue_5_x | 1152 -150 150 |
| blue_5_act_y | velocity | blue_5_y | 1152 -150 150 |
| blue_5_act_yaw | velocity | blue_5_yaw | 4.6656 -3 3 |
| yellow_0_act_x | velocity | yellow_0_x | 1152 -150 150 |
| yellow_0_act_y | velocity | yellow_0_y | 1152 -150 150 |
| yellow_0_act_yaw | velocity | yellow_0_yaw | 4.6656 -3 3 |
| yellow_1_act_x | velocity | yellow_1_x | 1152 -150 150 |
| yellow_1_act_y | velocity | yellow_1_y | 1152 -150 150 |
| yellow_1_act_yaw | velocity | yellow_1_yaw | 4.6656 -3 3 |
| yellow_2_act_x | velocity | yellow_2_x | 1152 -150 150 |
| yellow_2_act_y | velocity | yellow_2_y | 1152 -150 150 |
| yellow_2_act_yaw | velocity | yellow_2_yaw | 4.6656 -3 3 |
| yellow_3_act_x | velocity | yellow_3_x | 1152 -150 150 |
| yellow_3_act_y | velocity | yellow_3_y | 1152 -150 150 |
| yellow_3_act_yaw | velocity | yellow_3_yaw | 4.6656 -3 3 |
| yellow_4_act_x | velocity | yellow_4_x | 1152 -150 150 |
| yellow_4_act_y | velocity | yellow_4_y | 1152 -150 150 |
| yellow_4_act_yaw | velocity | yellow_4_yaw | 4.6656 -3 3 |
| yellow_5_act_x | velocity | yellow_5_x | 1152 -150 150 |
| yellow_5_act_y | velocity | yellow_5_y | 1152 -150 150 |
| yellow_5_act_yaw | velocity | yellow_5_yaw | 4.6656 -3 3 |

## sites

`centre_mark`, `blue_0_dribbler`, `blue_0_kicker`, `blue_1_dribbler`, `blue_1_kicker`, `blue_2_dribbler`, `blue_2_kicker`, `blue_3_dribbler`, `blue_3_kicker`, `blue_4_dribbler`, `blue_4_kicker`, `blue_5_dribbler`, `blue_5_kicker`, `yellow_0_dribbler`, `yellow_0_kicker`, `yellow_1_dribbler`, `yellow_1_kicker`, `yellow_2_dribbler`, `yellow_2_kicker`, `yellow_3_dribbler`, `yellow_3_kicker`, `yellow_4_dribbler`, `yellow_4_kicker`, `yellow_5_dribbler`, `yellow_5_kicker`

## compiled sizes

nbody=18 njnt=37 nq=43 nv=42 nu=36 ngeom=155 nsite=25 timestep=0.00208333
