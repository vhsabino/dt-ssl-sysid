/*
 * parameter_estimation_model_with_ros_v2.h
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

#ifndef parameter_estimation_model_with_ros_v2_h_
#define parameter_estimation_model_with_ros_v2_h_
#ifndef parameter_estimation_model_with_ros_v2_COMMON_INCLUDES_
#define parameter_estimation_model_with_ros_v2_COMMON_INCLUDES_
#include "rtwtypes.h"
#include "rtw_continuous.h"
#include "rtw_solver.h"
#include "rt_logging.h"
#include "rt_nonfinite.h"
#include "math.h"
#endif             /* parameter_estimation_model_with_ros_v2_COMMON_INCLUDES_ */

#include "parameter_estimation_model_with_ros_v2_types.h"
#include <math.h>
#include <float.h>
#include <string.h>
#include <stddef.h>

/* Macros for accessing real-time model data structure */
#ifndef rtmGetFinalTime
#define rtmGetFinalTime(rtm)           ((rtm)->Timing.tFinal)
#endif

#ifndef rtmGetRTWLogInfo
#define rtmGetRTWLogInfo(rtm)          ((rtm)->rtwLogInfo)
#endif

#ifndef rtmGetErrorStatus
#define rtmGetErrorStatus(rtm)         ((rtm)->errorStatus)
#endif

#ifndef rtmSetErrorStatus
#define rtmSetErrorStatus(rtm, val)    ((rtm)->errorStatus = (val))
#endif

#ifndef rtmGetStopRequested
#define rtmGetStopRequested(rtm)       ((rtm)->Timing.stopRequestedFlag)
#endif

#ifndef rtmSetStopRequested
#define rtmSetStopRequested(rtm, val)  ((rtm)->Timing.stopRequestedFlag = (val))
#endif

#ifndef rtmGetStopRequestedPtr
#define rtmGetStopRequestedPtr(rtm)    (&((rtm)->Timing.stopRequestedFlag))
#endif

#ifndef rtmGetT
#define rtmGetT(rtm)                   (rtmGetTPtr((rtm))[0])
#endif

#ifndef rtmGetTFinal
#define rtmGetTFinal(rtm)              ((rtm)->Timing.tFinal)
#endif

#ifndef rtmGetTPtr
#define rtmGetTPtr(rtm)                ((rtm)->Timing.t)
#endif

#define parameter_estimation_model_with_ros_v2_M (parameter_estimation_model_w_M)

/* Block signals (default storage) */
typedef struct {
  real_T DiscreteTransferFcn;          /* '<S5>/Discrete Transfer Fcn' */
  real_T DiscreteTransferFcn1;         /* '<S5>/Discrete Transfer Fcn1' */
  real_T DiscreteTransferFcn2;         /* '<S5>/Discrete Transfer Fcn2' */
  real_T DiscreteTransferFcn3;         /* '<S5>/Discrete Transfer Fcn3' */
  real_T Gain5;                        /* '<S1>/Gain5' */
  real_T UnitDelay;                    /* '<S5>/Unit Delay' */
  real_T Sum;                          /* '<S5>/Sum' */
  real_T Sum_f;                        /* '<S59>/Sum' */
  real_T UnitDelay3;                   /* '<S5>/Unit Delay3' */
  real_T Sum6;                         /* '<S5>/Sum6' */
  real_T Sum_h;                        /* '<S111>/Sum' */
  real_T UnitDelay1;                   /* '<S5>/Unit Delay1' */
  real_T Sum2;                         /* '<S5>/Sum2' */
  real_T Sum_j;                        /* '<S163>/Sum' */
  real_T UnitDelay2;                   /* '<S5>/Unit Delay2' */
  real_T Sum4;                         /* '<S5>/Sum4' */
  real_T Sum_a;                        /* '<S215>/Sum' */
  real_T FromWorkspace;                /* '<S1>/From Workspace' */
  real_T FromWorkspace1;               /* '<S1>/From Workspace1' */
  real_T FromWorkspace2;               /* '<S1>/From Workspace2' */
  real_T vx;                           /* '<S1>/MATLAB Function1' */
  real_T vy;                           /* '<S1>/MATLAB Function1' */
  real_T w1;                           /* '<S1>/MATLAB Function' */
  real_T w2;                           /* '<S1>/MATLAB Function' */
  real_T w3;                           /* '<S1>/MATLAB Function' */
  real_T w4;                           /* '<S1>/MATLAB Function' */
} B_parameter_estimation_model__T;

/* Block states (default storage) for system '<Root>' */
typedef struct {
  ros_slros2_internal_block_Pub_T obj; /* '<S11>/SinkBlock' */
  ros_slros2_internal_block_Pub_T obj_d;/* '<S10>/SinkBlock' */
  ros_slros2_internal_block_Pub_T obj_m;/* '<S9>/SinkBlock' */
  real_T DiscreteTransferFcn_states[2];/* '<S5>/Discrete Transfer Fcn' */
  real_T DiscreteTransferFcn1_states[2];/* '<S5>/Discrete Transfer Fcn1' */
  real_T DiscreteTransferFcn2_states[2];/* '<S5>/Discrete Transfer Fcn2' */
  real_T DiscreteTransferFcn3_states[2];/* '<S5>/Discrete Transfer Fcn3' */
  real_T UnitDelay_DSTATE;             /* '<S5>/Unit Delay' */
  real_T Integrator_DSTATE;            /* '<S50>/Integrator' */
  real_T UnitDelay3_DSTATE;            /* '<S5>/Unit Delay3' */
  real_T Integrator_DSTATE_m;          /* '<S102>/Integrator' */
  real_T UnitDelay1_DSTATE;            /* '<S5>/Unit Delay1' */
  real_T Integrator_DSTATE_i;          /* '<S154>/Integrator' */
  real_T UnitDelay2_DSTATE;            /* '<S5>/Unit Delay2' */
  real_T Integrator_DSTATE_e;          /* '<S206>/Integrator' */
  real_T TransportDelay_RWORK[2049];   /* '<S1>/Transport Delay' */
  real_T TransportDelay1_RWORK[2049];  /* '<S1>/Transport Delay1' */
  real_T TransportDelay2_RWORK[2049];  /* '<S1>/Transport Delay2' */
  struct {
    void *TimePtr;
    void *DataPtr;
    void *RSimInfoPtr;
  } FromWorkspace3_PWORK;              /* '<S1>/From Workspace3' */

  struct {
    void *TimePtr;
    void *DataPtr;
    void *RSimInfoPtr;
  } FromWorkspace5_PWORK;              /* '<S1>/From Workspace5' */

  struct {
    void *TimePtr;
    void *DataPtr;
    void *RSimInfoPtr;
  } FromWorkspace4_PWORK;              /* '<S1>/From Workspace4' */

  void *TransportDelay_PWORK[2];       /* '<S1>/Transport Delay' */
  void *TransportDelay1_PWORK[2];      /* '<S1>/Transport Delay1' */
  void *TransportDelay2_PWORK[2];      /* '<S1>/Transport Delay2' */
  struct {
    void *TimePtr;
    void *DataPtr;
    void *RSimInfoPtr;
  } FromWorkspace_PWORK;               /* '<S1>/From Workspace' */

  struct {
    void *TimePtr;
    void *DataPtr;
    void *RSimInfoPtr;
  } FromWorkspace1_PWORK;              /* '<S1>/From Workspace1' */

  struct {
    void *TimePtr;
    void *DataPtr;
    void *RSimInfoPtr;
  } FromWorkspace2_PWORK;              /* '<S1>/From Workspace2' */

  struct {
    int_T PrevIndex;
  } FromWorkspace3_IWORK;              /* '<S1>/From Workspace3' */

  struct {
    int_T PrevIndex;
  } FromWorkspace5_IWORK;              /* '<S1>/From Workspace5' */

  struct {
    int_T PrevIndex;
  } FromWorkspace4_IWORK;              /* '<S1>/From Workspace4' */

  int_T TransportDelay_IWORK[4];       /* '<S1>/Transport Delay' */
  int_T TransportDelay1_IWORK[4];      /* '<S1>/Transport Delay1' */
  int_T TransportDelay2_IWORK[4];      /* '<S1>/Transport Delay2' */
  struct {
    int_T PrevIndex;
  } FromWorkspace_IWORK;               /* '<S1>/From Workspace' */

  struct {
    int_T PrevIndex;
  } FromWorkspace1_IWORK;              /* '<S1>/From Workspace1' */

  struct {
    int_T PrevIndex;
  } FromWorkspace2_IWORK;              /* '<S1>/From Workspace2' */

  boolean_T objisempty;                /* '<S11>/SinkBlock' */
  boolean_T objisempty_h;              /* '<S10>/SinkBlock' */
  boolean_T objisempty_m;              /* '<S9>/SinkBlock' */
} DW_parameter_estimation_model_T;

/* Parameters (default storage) */
struct P_parameter_estimation_model__T_ {
  real_T K_Matrix[12];                 /* Variable: K_Matrix
                                        * Referenced by: '<Root>/Constant'
                                        */
  real_T Ki_initial;                   /* Variable: Ki_initial
                                        * Referenced by:
                                        *   '<S5>/Constant1'
                                        *   '<S5>/Constant3'
                                        *   '<S5>/Constant5'
                                        *   '<S5>/Constant7'
                                        */
  real_T Kp_initial;                   /* Variable: Kp_initial
                                        * Referenced by:
                                        *   '<S5>/Constant'
                                        *   '<S5>/Constant2'
                                        *   '<S5>/Constant4'
                                        *   '<S5>/Constant6'
                                        */
  real_T Ts;                           /* Variable: Ts
                                        * Referenced by:
                                        *   '<S1>/Gain3'
                                        *   '<S1>/Gain4'
                                        *   '<S1>/Gain5'
                                        */
  real_T den_d[3];                     /* Variable: den_d
                                        * Referenced by:
                                        *   '<S5>/Discrete Transfer Fcn'
                                        *   '<S5>/Discrete Transfer Fcn1'
                                        *   '<S5>/Discrete Transfer Fcn2'
                                        *   '<S5>/Discrete Transfer Fcn3'
                                        */
  real_T num_d[3];                     /* Variable: num_d
                                        * Referenced by:
                                        *   '<S5>/Discrete Transfer Fcn'
                                        *   '<S5>/Discrete Transfer Fcn1'
                                        *   '<S5>/Discrete Transfer Fcn2'
                                        *   '<S5>/Discrete Transfer Fcn3'
                                        */
  real_T t_delay;                      /* Variable: t_delay
                                        * Referenced by:
                                        *   '<S1>/Transport Delay'
                                        *   '<S1>/Transport Delay1'
                                        *   '<S1>/Transport Delay2'
                                        */
  real_T DiscretePIDController_InitialCo;
                              /* Mask Parameter: DiscretePIDController_InitialCo
                               * Referenced by: '<S50>/Integrator'
                               */
  real_T DiscretePIDController1_InitialC;
                              /* Mask Parameter: DiscretePIDController1_InitialC
                               * Referenced by: '<S102>/Integrator'
                               */
  real_T DiscretePIDController3_InitialC;
                              /* Mask Parameter: DiscretePIDController3_InitialC
                               * Referenced by: '<S154>/Integrator'
                               */
  real_T DiscretePIDController4_InitialC;
                              /* Mask Parameter: DiscretePIDController4_InitialC
                               * Referenced by: '<S206>/Integrator'
                               */
  SL_Bus_geometry_msgs_Pose Constant_Value;/* Computed Parameter: Constant_Value
                                            * Referenced by: '<S2>/Constant'
                                            */
  SL_Bus_geometry_msgs_Pose Constant_Value_a;/* Computed Parameter: Constant_Value_a
                                              * Referenced by: '<S4>/Constant'
                                              */
  SL_Bus_geometry_msgs_Twist Constant_Value_j;/* Computed Parameter: Constant_Value_j
                                               * Referenced by: '<S3>/Constant'
                                               */
  real_T Multiply_Gain;                /* Expression: 1
                                        * Referenced by: '<S1>/Multiply'
                                        */
  real_T DiscreteTransferFcn_InitialStat;/* Expression: 0
                                          * Referenced by: '<S5>/Discrete Transfer Fcn'
                                          */
  real_T DiscreteTransferFcn1_InitialSta;/* Expression: 0
                                          * Referenced by: '<S5>/Discrete Transfer Fcn1'
                                          */
  real_T DiscreteTransferFcn2_InitialSta;/* Expression: 0
                                          * Referenced by: '<S5>/Discrete Transfer Fcn2'
                                          */
  real_T DiscreteTransferFcn3_InitialSta;/* Expression: 0
                                          * Referenced by: '<S5>/Discrete Transfer Fcn3'
                                          */
  real_T Constant3_Value;              /* Expression: 0
                                        * Referenced by: '<S1>/Constant3'
                                        */
  real_T Multiply1_Gain;               /* Expression: 1
                                        * Referenced by: '<S1>/Multiply1'
                                        */
  real_T Constant_Value_c;             /* Expression: -0.0002
                                        * Referenced by: '<S1>/Constant'
                                        */
  real_T Constant1_Value;              /* Expression: 0
                                        * Referenced by: '<S1>/Constant1'
                                        */
  real_T Constant2_Value;              /* Expression: -0.0002
                                        * Referenced by: '<S1>/Constant2'
                                        */
  real_T TransportDelay_InitOutput;    /* Expression: 0
                                        * Referenced by: '<S1>/Transport Delay'
                                        */
  real_T TransportDelay1_InitOutput;   /* Expression: 0
                                        * Referenced by: '<S1>/Transport Delay1'
                                        */
  real_T TransportDelay2_InitOutput;   /* Expression: 0
                                        * Referenced by: '<S1>/Transport Delay2'
                                        */
  real_T UnitDelay_InitialCondition;   /* Expression: 0
                                        * Referenced by: '<S5>/Unit Delay'
                                        */
  real_T Integrator_gainval;           /* Computed Parameter: Integrator_gainval
                                        * Referenced by: '<S50>/Integrator'
                                        */
  real_T UnitDelay3_InitialCondition;  /* Expression: 0
                                        * Referenced by: '<S5>/Unit Delay3'
                                        */
  real_T Integrator_gainval_i;       /* Computed Parameter: Integrator_gainval_i
                                      * Referenced by: '<S102>/Integrator'
                                      */
  real_T UnitDelay1_InitialCondition;  /* Expression: 0
                                        * Referenced by: '<S5>/Unit Delay1'
                                        */
  real_T Integrator_gainval_h;       /* Computed Parameter: Integrator_gainval_h
                                      * Referenced by: '<S154>/Integrator'
                                      */
  real_T UnitDelay2_InitialCondition;  /* Expression: 0
                                        * Referenced by: '<S5>/Unit Delay2'
                                        */
  real_T Integrator_gainval_c;       /* Computed Parameter: Integrator_gainval_c
                                      * Referenced by: '<S206>/Integrator'
                                      */
};

/* Real-time Model Data Structure */
struct tag_RTM_parameter_estimation__T {
  const char_T *errorStatus;
  RTWLogInfo *rtwLogInfo;
  RTWSolverInfo solverInfo;

  /*
   * Timing:
   * The following substructure contains information regarding
   * the timing information for the model.
   */
  struct {
    uint32_T clockTick0;
    uint32_T clockTickH0;
    time_T stepSize0;
    uint32_T clockTick1;
    uint32_T clockTickH1;
    struct {
      uint8_T TID[2];
    } TaskCounters;

    time_T tFinal;
    SimTimeStep simTimeStep;
    boolean_T stopRequestedFlag;
    time_T *t;
    time_T tArray[2];
  } Timing;
};

/* Block parameters (default storage) */
extern P_parameter_estimation_model__T parameter_estimation_model_wi_P;

/* Block signals (default storage) */
extern B_parameter_estimation_model__T parameter_estimation_model_wi_B;

/* Block states (default storage) */
extern DW_parameter_estimation_model_T parameter_estimation_model_w_DW;

/* Model entry point functions */
extern void parameter_estimation_model_with_ros_v2_initialize(void);
extern void parameter_estimation_model_with_ros_v2_step(void);
extern void parameter_estimation_model_with_ros_v2_terminate(void);

/* Real-time Model object */
extern RT_MODEL_parameter_estimation_T *const parameter_estimation_model_w_M;

/*-
 * The generated code includes comments that allow you to trace directly
 * back to the appropriate location in the model.  The basic format
 * is <system>/block_name, where system is the system number (uniquely
 * assigned by Simulink) and block_name is the name of the block.
 *
 * Use the MATLAB hilite_system command to trace the generated code back
 * to the model.  For example,
 *
 * hilite_system('<S3>')    - opens system 3
 * hilite_system('<S3>/Kp') - opens and selects block Kp which resides in S3
 *
 * Here is the system hierarchy for this model
 *
 * '<Root>' : 'parameter_estimation_model_with_ros_v2'
 * '<S1>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin'
 * '<S2>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/Blank Message'
 * '<S3>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/Blank Message1'
 * '<S4>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/Blank Message2'
 * '<S5>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control'
 * '<S6>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/MATLAB Function'
 * '<S7>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/MATLAB Function1'
 * '<S8>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/MATLAB Function2'
 * '<S9>'   : 'parameter_estimation_model_with_ros_v2/Digital Twin/Publish'
 * '<S10>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Publish1'
 * '<S11>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Publish2'
 * '<S12>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller'
 * '<S13>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1'
 * '<S14>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3'
 * '<S15>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4'
 * '<S16>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Anti-windup'
 * '<S17>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/D Gain'
 * '<S18>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/External Derivative'
 * '<S19>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Filter'
 * '<S20>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Filter ICs'
 * '<S21>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/I Gain'
 * '<S22>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Ideal P Gain'
 * '<S23>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Ideal P Gain Fdbk'
 * '<S24>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Integrator'
 * '<S25>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Integrator ICs'
 * '<S26>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/N Copy'
 * '<S27>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/N Gain'
 * '<S28>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/P Copy'
 * '<S29>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Parallel P Gain'
 * '<S30>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Reset Signal'
 * '<S31>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Saturation'
 * '<S32>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Saturation Fdbk'
 * '<S33>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Sum'
 * '<S34>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Sum Fdbk'
 * '<S35>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tracking Mode'
 * '<S36>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tracking Mode Sum'
 * '<S37>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tsamp - Integral'
 * '<S38>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tsamp - Ngain'
 * '<S39>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/postSat Signal'
 * '<S40>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/preInt Signal'
 * '<S41>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/preSat Signal'
 * '<S42>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Anti-windup/Passthrough'
 * '<S43>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/D Gain/Disabled'
 * '<S44>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/External Derivative/Disabled'
 * '<S45>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Filter/Disabled'
 * '<S46>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Filter ICs/Disabled'
 * '<S47>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/I Gain/External Parameters'
 * '<S48>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Ideal P Gain/Passthrough'
 * '<S49>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Ideal P Gain Fdbk/Disabled'
 * '<S50>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Integrator/Discrete'
 * '<S51>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Integrator ICs/Internal IC'
 * '<S52>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/N Copy/Disabled wSignal Specification'
 * '<S53>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/N Gain/Disabled'
 * '<S54>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/P Copy/Disabled'
 * '<S55>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Parallel P Gain/External Parameters'
 * '<S56>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Reset Signal/Disabled'
 * '<S57>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Saturation/Passthrough'
 * '<S58>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Saturation Fdbk/Disabled'
 * '<S59>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Sum/Sum_PI'
 * '<S60>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Sum Fdbk/Disabled'
 * '<S61>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tracking Mode/Disabled'
 * '<S62>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tracking Mode Sum/Passthrough'
 * '<S63>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tsamp - Integral/TsSignalSpecification'
 * '<S64>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/Tsamp - Ngain/Passthrough'
 * '<S65>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/postSat Signal/Forward_Path'
 * '<S66>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/preInt Signal/Internal PreInt'
 * '<S67>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller/preSat Signal/Forward_Path'
 * '<S68>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Anti-windup'
 * '<S69>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/D Gain'
 * '<S70>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/External Derivative'
 * '<S71>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Filter'
 * '<S72>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Filter ICs'
 * '<S73>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/I Gain'
 * '<S74>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Ideal P Gain'
 * '<S75>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Ideal P Gain Fdbk'
 * '<S76>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Integrator'
 * '<S77>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Integrator ICs'
 * '<S78>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/N Copy'
 * '<S79>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/N Gain'
 * '<S80>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/P Copy'
 * '<S81>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Parallel P Gain'
 * '<S82>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Reset Signal'
 * '<S83>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Saturation'
 * '<S84>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Saturation Fdbk'
 * '<S85>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Sum'
 * '<S86>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Sum Fdbk'
 * '<S87>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tracking Mode'
 * '<S88>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tracking Mode Sum'
 * '<S89>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tsamp - Integral'
 * '<S90>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tsamp - Ngain'
 * '<S91>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/postSat Signal'
 * '<S92>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/preInt Signal'
 * '<S93>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/preSat Signal'
 * '<S94>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Anti-windup/Passthrough'
 * '<S95>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/D Gain/Disabled'
 * '<S96>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/External Derivative/Disabled'
 * '<S97>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Filter/Disabled'
 * '<S98>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Filter ICs/Disabled'
 * '<S99>'  : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/I Gain/External Parameters'
 * '<S100>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Ideal P Gain/Passthrough'
 * '<S101>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Ideal P Gain Fdbk/Disabled'
 * '<S102>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Integrator/Discrete'
 * '<S103>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Integrator ICs/Internal IC'
 * '<S104>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/N Copy/Disabled wSignal Specification'
 * '<S105>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/N Gain/Disabled'
 * '<S106>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/P Copy/Disabled'
 * '<S107>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Parallel P Gain/External Parameters'
 * '<S108>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Reset Signal/Disabled'
 * '<S109>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Saturation/Passthrough'
 * '<S110>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Saturation Fdbk/Disabled'
 * '<S111>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Sum/Sum_PI'
 * '<S112>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Sum Fdbk/Disabled'
 * '<S113>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tracking Mode/Disabled'
 * '<S114>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tracking Mode Sum/Passthrough'
 * '<S115>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tsamp - Integral/TsSignalSpecification'
 * '<S116>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/Tsamp - Ngain/Passthrough'
 * '<S117>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/postSat Signal/Forward_Path'
 * '<S118>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/preInt Signal/Internal PreInt'
 * '<S119>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller1/preSat Signal/Forward_Path'
 * '<S120>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Anti-windup'
 * '<S121>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/D Gain'
 * '<S122>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/External Derivative'
 * '<S123>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Filter'
 * '<S124>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Filter ICs'
 * '<S125>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/I Gain'
 * '<S126>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Ideal P Gain'
 * '<S127>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Ideal P Gain Fdbk'
 * '<S128>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Integrator'
 * '<S129>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Integrator ICs'
 * '<S130>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/N Copy'
 * '<S131>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/N Gain'
 * '<S132>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/P Copy'
 * '<S133>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Parallel P Gain'
 * '<S134>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Reset Signal'
 * '<S135>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Saturation'
 * '<S136>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Saturation Fdbk'
 * '<S137>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Sum'
 * '<S138>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Sum Fdbk'
 * '<S139>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tracking Mode'
 * '<S140>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tracking Mode Sum'
 * '<S141>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tsamp - Integral'
 * '<S142>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tsamp - Ngain'
 * '<S143>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/postSat Signal'
 * '<S144>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/preInt Signal'
 * '<S145>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/preSat Signal'
 * '<S146>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Anti-windup/Passthrough'
 * '<S147>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/D Gain/Disabled'
 * '<S148>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/External Derivative/Disabled'
 * '<S149>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Filter/Disabled'
 * '<S150>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Filter ICs/Disabled'
 * '<S151>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/I Gain/External Parameters'
 * '<S152>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Ideal P Gain/Passthrough'
 * '<S153>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Ideal P Gain Fdbk/Disabled'
 * '<S154>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Integrator/Discrete'
 * '<S155>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Integrator ICs/Internal IC'
 * '<S156>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/N Copy/Disabled wSignal Specification'
 * '<S157>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/N Gain/Disabled'
 * '<S158>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/P Copy/Disabled'
 * '<S159>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Parallel P Gain/External Parameters'
 * '<S160>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Reset Signal/Disabled'
 * '<S161>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Saturation/Passthrough'
 * '<S162>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Saturation Fdbk/Disabled'
 * '<S163>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Sum/Sum_PI'
 * '<S164>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Sum Fdbk/Disabled'
 * '<S165>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tracking Mode/Disabled'
 * '<S166>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tracking Mode Sum/Passthrough'
 * '<S167>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tsamp - Integral/TsSignalSpecification'
 * '<S168>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/Tsamp - Ngain/Passthrough'
 * '<S169>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/postSat Signal/Forward_Path'
 * '<S170>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/preInt Signal/Internal PreInt'
 * '<S171>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller3/preSat Signal/Forward_Path'
 * '<S172>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Anti-windup'
 * '<S173>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/D Gain'
 * '<S174>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/External Derivative'
 * '<S175>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Filter'
 * '<S176>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Filter ICs'
 * '<S177>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/I Gain'
 * '<S178>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Ideal P Gain'
 * '<S179>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Ideal P Gain Fdbk'
 * '<S180>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Integrator'
 * '<S181>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Integrator ICs'
 * '<S182>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/N Copy'
 * '<S183>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/N Gain'
 * '<S184>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/P Copy'
 * '<S185>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Parallel P Gain'
 * '<S186>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Reset Signal'
 * '<S187>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Saturation'
 * '<S188>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Saturation Fdbk'
 * '<S189>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Sum'
 * '<S190>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Sum Fdbk'
 * '<S191>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tracking Mode'
 * '<S192>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tracking Mode Sum'
 * '<S193>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tsamp - Integral'
 * '<S194>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tsamp - Ngain'
 * '<S195>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/postSat Signal'
 * '<S196>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/preInt Signal'
 * '<S197>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/preSat Signal'
 * '<S198>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Anti-windup/Passthrough'
 * '<S199>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/D Gain/Disabled'
 * '<S200>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/External Derivative/Disabled'
 * '<S201>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Filter/Disabled'
 * '<S202>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Filter ICs/Disabled'
 * '<S203>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/I Gain/External Parameters'
 * '<S204>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Ideal P Gain/Passthrough'
 * '<S205>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Ideal P Gain Fdbk/Disabled'
 * '<S206>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Integrator/Discrete'
 * '<S207>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Integrator ICs/Internal IC'
 * '<S208>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/N Copy/Disabled wSignal Specification'
 * '<S209>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/N Gain/Disabled'
 * '<S210>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/P Copy/Disabled'
 * '<S211>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Parallel P Gain/External Parameters'
 * '<S212>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Reset Signal/Disabled'
 * '<S213>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Saturation/Passthrough'
 * '<S214>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Saturation Fdbk/Disabled'
 * '<S215>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Sum/Sum_PI'
 * '<S216>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Sum Fdbk/Disabled'
 * '<S217>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tracking Mode/Disabled'
 * '<S218>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tracking Mode Sum/Passthrough'
 * '<S219>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tsamp - Integral/TsSignalSpecification'
 * '<S220>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/Tsamp - Ngain/Passthrough'
 * '<S221>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/postSat Signal/Forward_Path'
 * '<S222>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/preInt Signal/Internal PreInt'
 * '<S223>' : 'parameter_estimation_model_with_ros_v2/Digital Twin/Control/Discrete PID Controller4/preSat Signal/Forward_Path'
 */
#endif                           /* parameter_estimation_model_with_ros_v2_h_ */
