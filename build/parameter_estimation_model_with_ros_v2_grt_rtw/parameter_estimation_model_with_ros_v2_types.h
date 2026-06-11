/*
 * parameter_estimation_model_with_ros_v2_types.h
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

#ifndef parameter_estimation_model_with_ros_v2_types_h_
#define parameter_estimation_model_with_ros_v2_types_h_
#include "rtwtypes.h"
#ifndef DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Point_
#define DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Point_

typedef struct {
  real_T x;
  real_T y;
  real_T z;
} SL_Bus_geometry_msgs_Point;

#endif

#ifndef DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Quaternion_
#define DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Quaternion_

typedef struct {
  real_T x;
  real_T y;
  real_T z;
  real_T w;
} SL_Bus_geometry_msgs_Quaternion;

#endif

#ifndef DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Pose_
#define DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Pose_

typedef struct {
  SL_Bus_geometry_msgs_Point position;
  SL_Bus_geometry_msgs_Quaternion orientation;
} SL_Bus_geometry_msgs_Pose;

#endif

#ifndef DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Vector3_
#define DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Vector3_

typedef struct {
  real_T x;
  real_T y;
  real_T z;
} SL_Bus_geometry_msgs_Vector3;

#endif

#ifndef DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Twist_
#define DEFINED_TYPEDEF_FOR_SL_Bus_geometry_msgs_Twist_

typedef struct {
  SL_Bus_geometry_msgs_Vector3 linear;
  SL_Bus_geometry_msgs_Vector3 angular;
} SL_Bus_geometry_msgs_Twist;

#endif

#ifndef struct_tag_sJ4ih70VmKcvCeguWN0mNVF
#define struct_tag_sJ4ih70VmKcvCeguWN0mNVF

struct tag_sJ4ih70VmKcvCeguWN0mNVF
{
  real_T sec;
  real_T nsec;
};

#endif                                 /* struct_tag_sJ4ih70VmKcvCeguWN0mNVF */

#ifndef typedef_sJ4ih70VmKcvCeguWN0mNVF
#define typedef_sJ4ih70VmKcvCeguWN0mNVF

typedef struct tag_sJ4ih70VmKcvCeguWN0mNVF sJ4ih70VmKcvCeguWN0mNVF;

#endif                                 /* typedef_sJ4ih70VmKcvCeguWN0mNVF */

#ifndef struct_tag_iN0konlvN1acOwru0lZ0kF
#define struct_tag_iN0konlvN1acOwru0lZ0kF

struct tag_iN0konlvN1acOwru0lZ0kF
{
  boolean_T matlabCodegenIsDeleted;
  int32_T isInitialized;
  boolean_T isSetupComplete;
  boolean_T QOSAvoidROSNamespaceConventions;
};

#endif                                 /* struct_tag_iN0konlvN1acOwru0lZ0kF */

#ifndef typedef_ros_slros2_internal_block_Pub_T
#define typedef_ros_slros2_internal_block_Pub_T

typedef struct tag_iN0konlvN1acOwru0lZ0kF ros_slros2_internal_block_Pub_T;

#endif                             /* typedef_ros_slros2_internal_block_Pub_T */

/* Parameters (default storage) */
typedef struct P_parameter_estimation_model__T_ P_parameter_estimation_model__T;

/* Forward declaration for rtModel */
typedef struct tag_RTM_parameter_estimation__T RT_MODEL_parameter_estimation_T;

#endif                     /* parameter_estimation_model_with_ros_v2_types_h_ */
