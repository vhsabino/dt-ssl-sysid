# Welcome to the documentation of the data_select folder!

The main component of this folder is the *data_filter_operator.py* file, which contains the functions:

1. load_select_modules
2. processed_frame_extract_ball_data_frame
3. raw_frame_extract_ball_data_frame
4. processed_frame_extract_robot_data_frame
5. processed_frame_extract_position_data
6. telemetry_extract_robot_data_frame
7. robots_command_extract_robot_data_frame

## 5. processed_frame_extract_position_data

Returns a dataframe containing information about the position in X and Y axis for every object in the field (enemies, allies and ball). To do this, the function filters the data list returned by `load_select_modules` by creating lines that contains the ball information and the robots information for each instance of data in the data list. These information are **timestamp, position_x, position_y, id of robot and whatObject**, which is useful to filter the objects by allies, enemies and ball. After creating the lines, they are appended to an unique list that is converted to a dataframe, which is returned.