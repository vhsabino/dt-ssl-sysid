# `ros_bridge/` — conversores bus↔mensagem ROS 2 (fev/2026, ARQUIVADO)

Era `matlab/ros_bridge/`. Funções `+bus_conv_fcns/+ros2/+busToMsg/+geometry_msgs/{Point,Pose,
Quaternion,Twist,Vector3}.m` **geradas pelo Simulink** (copyright MathWorks 2021) para os modelos
`parameter_estimation_model_with_ros{,_v2}.slx` e `archive/rl/rl_model_with_ros.slx`, que publicavam
a pose do robô/bola em tópicos ROS 2 (visualizadores em `legacy/archive/old_viewers/`).

Esta é a **única cópia** mantida: `archive/bus_conv_fcns_legacy/` (duplicata byte-a-byte,
verificada com `diff -r` em 02/09/2026) foi removida. ROS 2 saiu do fluxo do projeto; os modelos
`with_ros*` são descartados pelo `tools/apply_refactor_manifest.json`. Sem entradas no CHANGELOG.
