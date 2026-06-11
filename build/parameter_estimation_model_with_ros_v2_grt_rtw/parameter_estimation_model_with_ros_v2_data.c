/*
 * parameter_estimation_model_with_ros_v2_data.c
 *
 * Prerelease License - for engineering feedback and testing purposes
 * only. Not for sale.
 *
 * Code generation for model "parameter_estimation_model_with_ros_v2".
 *
 * Model version              : 1.78
 * Simulink Coder version : 26.1 (R2026a) 20-Nov-2025
 * C source code generated on : Mon May 11 10:58:40 2026
 *
 * Target selection: grt.tlc
 * Note: GRT includes extra infrastructure and instrumentation for prototyping
 * Embedded hardware selection: Intel->x86-64 (Windows64)
 * Code generation objectives: Unspecified
 * Validation result: Not run
 */

#include "parameter_estimation_model_with_ros_v2.h"

/* Block parameters (default storage) */
P_parameter_estimation_model__T parameter_estimation_model_wi_P = {
  /* Variable: K_Matrix
   * Referenced by: '<Root>/Constant'
   */
  { -0.3, -0.2546, -0.3, -0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 },

  /* Variable: Ki_initial
   * Referenced by:
   *   '<S5>/Constant1'
   *   '<S5>/Constant3'
   *   '<S5>/Constant5'
   *   '<S5>/Constant7'
   */
  6.434,

  /* Variable: Kp_initial
   * Referenced by:
   *   '<S5>/Constant'
   *   '<S5>/Constant2'
   *   '<S5>/Constant4'
   *   '<S5>/Constant6'
   */
  0.3194,

  /* Variable: Ts
   * Referenced by:
   *   '<S1>/Gain3'
   *   '<S1>/Gain4'
   *   '<S1>/Gain5'
   */
  0.0167,

  /* Variable: den_d
   * Referenced by:
   *   '<S5>/Discrete Transfer Fcn'
   *   '<S5>/Discrete Transfer Fcn1'
   *   '<S5>/Discrete Transfer Fcn2'
   *   '<S5>/Discrete Transfer Fcn3'
   */
  { 1.0, -0.87368383963538521, 0.0 },

  /* Variable: num_d
   * Referenced by:
   *   '<S5>/Discrete Transfer Fcn'
   *   '<S5>/Discrete Transfer Fcn1'
   *   '<S5>/Discrete Transfer Fcn2'
   *   '<S5>/Discrete Transfer Fcn3'
   */
  { 0.0, 0.11748649148671116, 0.00028669859518516932 },

  /* Variable: t_delay
   * Referenced by:
   *   '<S1>/Transport Delay'
   *   '<S1>/Transport Delay1'
   *   '<S1>/Transport Delay2'
   */
  0.0167,

  /* Mask Parameter: DiscretePIDController_InitialCo
   * Referenced by: '<S50>/Integrator'
   */
  0.0,

  /* Mask Parameter: DiscretePIDController1_InitialC
   * Referenced by: '<S102>/Integrator'
   */
  0.0,

  /* Mask Parameter: DiscretePIDController3_InitialC
   * Referenced by: '<S154>/Integrator'
   */
  0.0,

  /* Mask Parameter: DiscretePIDController4_InitialC
   * Referenced by: '<S206>/Integrator'
   */
  0.0,

  /* Computed Parameter: Constant_Value
   * Referenced by: '<S2>/Constant'
   */
  {
    {
      0.0,                             /* x */
      0.0,                             /* y */
      0.0                              /* z */
    },                                 /* position */

    {
      0.0,                             /* x */
      0.0,                             /* y */
      0.0,                             /* z */
      0.0                              /* w */
    }                                  /* orientation */
  },

  /* Computed Parameter: Constant_Value_a
   * Referenced by: '<S4>/Constant'
   */
  {
    {
      0.0,                             /* x */
      0.0,                             /* y */
      0.0                              /* z */
    },                                 /* position */

    {
      0.0,                             /* x */
      0.0,                             /* y */
      0.0,                             /* z */
      0.0                              /* w */
    }                                  /* orientation */
  },

  /* Computed Parameter: Constant_Value_j
   * Referenced by: '<S3>/Constant'
   */
  {
    {
      0.0,                             /* x */
      0.0,                             /* y */
      0.0                              /* z */
    },                                 /* linear */

    {
      0.0,                             /* x */
      0.0,                             /* y */
      0.0                              /* z */
    }                                  /* angular */
  },

  /* Expression: 1
   * Referenced by: '<S1>/Multiply'
   */
  1.0,

  /* Expression: 0
   * Referenced by: '<S5>/Discrete Transfer Fcn'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S5>/Discrete Transfer Fcn1'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S5>/Discrete Transfer Fcn2'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S5>/Discrete Transfer Fcn3'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S1>/Constant3'
   */
  0.0,

  /* Expression: 1
   * Referenced by: '<S1>/Multiply1'
   */
  1.0,

  /* Expression: -0.0002
   * Referenced by: '<S1>/Constant'
   */
  -0.0002,

  /* Expression: 0
   * Referenced by: '<S1>/Constant1'
   */
  0.0,

  /* Expression: -0.0002
   * Referenced by: '<S1>/Constant2'
   */
  -0.0002,

  /* Expression: 0
   * Referenced by: '<S1>/Transport Delay'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S1>/Transport Delay1'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S1>/Transport Delay2'
   */
  0.0,

  /* Expression: 0
   * Referenced by: '<S5>/Unit Delay'
   */
  0.0,

  /* Computed Parameter: Integrator_gainval
   * Referenced by: '<S50>/Integrator'
   */
  0.0167,

  /* Expression: 0
   * Referenced by: '<S5>/Unit Delay3'
   */
  0.0,

  /* Computed Parameter: Integrator_gainval_i
   * Referenced by: '<S102>/Integrator'
   */
  0.0167,

  /* Expression: 0
   * Referenced by: '<S5>/Unit Delay1'
   */
  0.0,

  /* Computed Parameter: Integrator_gainval_h
   * Referenced by: '<S154>/Integrator'
   */
  0.0167,

  /* Expression: 0
   * Referenced by: '<S5>/Unit Delay2'
   */
  0.0,

  /* Computed Parameter: Integrator_gainval_c
   * Referenced by: '<S206>/Integrator'
   */
  0.0167
};
