import proto.generated.RCLog as ProtoRCLog
import proto.generated.RoboCupSSL as ProtoRoboCupSSL
from pyrecordio.compressed_proto_record_reader import CompressedProtoRecordReader as ProtoRecordReader
from betterproto import Casing
import pandas as pd

def load_select_modules(logFile: str, list_modules: list) -> list:
    raw_data = []

    with open(logFile, "rb") as inp:
        reader = ProtoRecordReader(inp, ProtoRCLog.Log)

        for idx, logMsg in enumerate(reader):
            try:
                all_data = logMsg.to_dict(Casing.SNAKE, True)
            except IndexError as e:
                #print(f"⚠️ Registro {idx} contém enum inválido. Pulando...")
                continue  # ignora este registro problemático

            select_data = {'timestamp': logMsg.timestamp}

            for modField in list_modules:
                data_key = str(modField).lower().split('.')[-1]
                if data_key in all_data:
                    select_data[data_key] = all_data[data_key]

            if len(select_data.keys()) > 1:
                raw_data.append(select_data)

    return raw_data



def processed_frame_extract_ball_data_frame(filtered_data:list)-> pd.DataFrame:
    ball_data_list=[]

    for data in filtered_data:
        if 'processed_frame' in data:
            process_frame = data['processed_frame']
            data_line = {}
            timestamp =  process_frame['publish_timestamp']

            if timestamp == 0:
                continue

            data_line['timestamp'] = timestamp

            ball_data = process_frame['ball']

            if 'position' in ball_data:
                data_line['position_x'] = ball_data['position']['x']
                data_line['position_y'] = ball_data['position']['y']

            if 'velocity' in ball_data:
                data_line['velocity_x'] = ball_data['velocity']['x']
                data_line['velocity_y'] = ball_data['velocity']['y']
            
            if 'acceleration' in ball_data:
                data_line['acceleration_x'] = ball_data['acceleration']['x']
                data_line['acceleration_y'] = ball_data['acceleration']['y']

            ball_data_list.append(data_line)
    
    data_frame = pd.DataFrame(ball_data_list)

    return data_frame

def raw_frame_extract_ball_data_frame(filtered_data:list)-> pd.DataFrame:
    ball_data_list=[]

    for data in filtered_data:
        if 'raw_frame' in data and data['raw_frame']:
            
            for process_frame in data['raw_frame']:
            
                data_line = {}
                
                timestamp =  process_frame['publish_timestamp']

                if timestamp == 0:
                    continue

                if 'packet' in process_frame and 'detection' in process_frame['packet'] and process_frame['packet']['detection']['balls']:
                    ball_data = process_frame['packet']['detection']['balls'][0]
                    
                    data_line['timestamp'] = timestamp

                    if 'x' in ball_data and ball_data['x']:
                        data_line['position_x'] = ball_data['x']
                    if 'y' in ball_data:
                        data_line['position_y'] = ball_data['y']

                # if 'velocity' in ball_data:
                #     data_line['velocity_x'] = ball_data['velocity']['x']
                #     data_line['velocity_y'] = ball_data['velocity']['y']
                
                # if 'acceleration' in ball_data:
                #     data_line['acceleration_x'] = ball_data['acceleration']['x']
                #     data_line['acceleration_y'] = ball_data['acceleration']['y']

                    if not ball_data_list or (data_line['timestamp'] != ball_data_list[-1]['timestamp'] and data_line['position_x'] != ball_data_list[-1]['position_x'] and data_line['position_y'] != ball_data_list[-1]['position_y']):
                        ball_data_list.append(data_line)
    
    data_frame = pd.DataFrame(ball_data_list)

    return data_frame


def processed_frame_extract_robot_data_frame(filtered_data:list, isAlly:bool, robot_id:int)-> pd.DataFrame:
    robot_data_list=[]

    robot_team = 'enemies'
    if isAlly:
        robot_team = 'allies'

    for data in filtered_data:
        if 'processed_frame' in data:
            process_frame = data['processed_frame']
            data_line = {}
                        
            timestamp = process_frame['publish_timestamp']

            if timestamp == 0:
                continue

            data_line['timestamp'] = timestamp
            
            if robot_team not in process_frame:
                continue

            robots = process_frame[robot_team]
            for robot in robots:
                if robot['id'] == robot_id:

                    if 'position' in robot:
                        data_line['position_x'] = robot['position']['x']
                        data_line['position_y'] = robot['position']['y']
                        data_line['position_w'] = robot['position']['omega']

                    if 'velocity' in robot:
                        data_line['velocity_x'] = robot['velocity']['x']
                        data_line['velocity_y'] = robot['velocity']['y']

                    robot_data_list.append(data_line)
                    
    data_frame = pd.DataFrame(robot_data_list)
    return data_frame

def processed_frame_extract_position_data(filtered_data:list)-> pd.DataFrame:
    # The dataframe returned by this function should have the columns: timestamp, position_x, position_y, id and whatObject

    heat_map_data_list = []

    for data in filtered_data:
        if 'processed_frame' in data: # processed_frame is a column
            process_frame = data['processed_frame']
            ball_data_line = {}
            timestamp = process_frame['publish_timestamp']

            if int(timestamp) == 0:
                continue
            
            # Get ball infos
            ball_data_line['timestamp'] = timestamp

            ball_data = process_frame['ball']

            if 'position' in ball_data:
                ball_data_line['position_x'] = ball_data['position']['x']
                ball_data_line['position_y'] = ball_data['position']['y']
                ball_data_line['whatObject'] = 'ball'
            
            heat_map_data_list.append(ball_data_line)

            robot_teams = ['allies', 'enemies']
            
            for robot_team in robot_teams:
                robots = process_frame[robot_team]

                for robot in robots:
                    robot_data_line = {}
                    robot_data_line['timestamp'] = timestamp

                    if 'position' in robot:
                        robot_data_line['position_x'] = robot['position']['x']
                        robot_data_line['position_y'] = robot['position']['y']
                        robot_data_line['id'] = robot['id']
                        robot_data_line['whatObject'] = robot_team
                    
                    heat_map_data_list.append(robot_data_line)    
    
    data_frame = pd.DataFrame(heat_map_data_list)
    return data_frame

def raw_frame_extract_robot_data_frame(raw_data:list, isBlue:bool, robot_id:int)-> pd.DataFrame:
    robot_data_list=[]

    robot_team = 'robots_yellow'
    if isBlue:
        robot_team = 'robots_blue'

    for data in raw_data:
        if 'raw_frame' in data and data['raw_frame']:

            for raw_frame in data['raw_frame']:

                data_line = {}
                            
                timestamp = raw_frame['publish_timestamp']

                if timestamp == 0:
                    continue

                data_line['timestamp'] = timestamp

                if 'packet' in raw_frame and 'detection' in raw_frame['packet'] and raw_frame['packet']['detection'][robot_team]:

                    robots = raw_frame['packet']['detection'][robot_team]
                    for robot in robots:
                        if robot['robot_id'] == robot_id:

                            data_line['position_x'] = robot['x']
                            data_line['position_y'] = robot['y']
                            data_line['position_w'] = robot['orientation']

                            robot_data_list.append(data_line)
                    
    data_frame = pd.DataFrame(robot_data_list)
    return data_frame

def telemetry_extract_robot_data_frame(filtered_data:list, robot_id:int)-> pd.DataFrame:
    telemetry_data_list=[]

    for data in filtered_data:
        if 'telemetry' in data:
            telemetries = data['telemetry']
            data_line = {}

            for robot in telemetries['telemetries']:

                timestamp = robot['receive_timestamp']

                if timestamp == 0:
                    continue

                if robot['id'] == robot_id:

                    data_line['timestamp'] = timestamp

                    if 'wheel1' in robot:
                        data_line['wheel1'] = robot['wheel1']
                        data_line['wheel2'] = robot['wheel2']
                        data_line['wheel3'] = robot['wheel3']
                        data_line['wheel4'] = robot['wheel4']
                    
                    if 'position' in robot:
                        data_line['position_x'] = robot['position']['x']
                        data_line['position_y'] = robot['position']['y']
                        data_line['position_w'] = robot['position']['omega']
                    
                    # if 'velocity' in robot:
                    #     data_line['velocity_x'] = robot['velocity']['x']
                    #     data_line['velocity_y'] = robot['velocity']['y']
                    #     data_line['velocity_w'] = robot['velocity']['omega']
                    
                    if 'dribbler_speed' in robot:
                        data_line['dribbler_speed'] = robot['dribbler_speed']
                    
                    if 'capacitor_charge' in robot:
                        data_line['capacitor_charge'] = robot['capacitor_charge']
                    
                    if 'dribbler_ball_contact' in robot:
                        data_line['dribbler_ball_contact'] = robot['dribbler_ball_contact']
                    
                    if 'battery' in robot:
                        data_line['battery'] = robot['battery']
                    
                    if 'count' in robot:
                        data_line['count'] = robot['count']
                    
                    telemetry_data_list.append(data_line)

    data_frame = pd.DataFrame(telemetry_data_list)
    
    return data_frame

def robots_command_extract_robot_data_frame(filtered_data:list, robot_id:int)-> pd.DataFrame:
    robot_command_data_list=[]

    for data in filtered_data:
        if 'robots_command' in data:
            navigation = data['robots_command']['navigation']
            data_line = {}

            for robot in navigation:

                timestamp = robot['publish_timestamp']

                if timestamp == 0:
                    continue

                if robot['id'] == robot_id:

                    data_line['timestamp'] = timestamp

                    if 'move' in robot:
                        data_line['move_x'] = robot['move']['x']
                        data_line['move_y'] = robot['move']['y']
                        data_line['move_w'] = robot['move']['omega']
                    
                    if 'actuation' in robot:
                        data_line['actuation_kick_strength'] = robot['actuation']['kick_strength']
                        data_line['actuation_front'] = robot['actuation']['front']
                        data_line['actuation_chip'] = robot['actuation']['chip']
                        data_line['actuation_front'] = robot['actuation']['charge']
                        data_line['actuation_dribbler'] = robot['actuation']['dribbler']
                        data_line['actuation_dribbler_velocity'] = robot['actuation']['dribbler_velocity']
                    
                    robot_command_data_list.append(data_line)

    data_frame = pd.DataFrame(robot_command_data_list)
    
    return data_frame

def extract_processed_frame_data(filtered_data: list) -> pd.DataFrame:
    """
    Extrai dados da bola e de todos os robôs de cada processed_frame
    e retorna um DataFrame único com todas as informações.
    """
    combined_data_list = []

    for data in filtered_data:
        if 'processed_frame' not in data:
            continue

        frame = data['processed_frame']
        timestamp = frame.get('publish_timestamp', 0)

        if timestamp == 0:
            continue

        # --- Dados da bola ---
        ball_line = {'timestamp': timestamp}
        ball = frame.get('ball', {})

        if 'position' in ball:
            ball_line['ball_pos_x'] = ball['position'].get('x')
            ball_line['ball_pos_y'] = ball['position'].get('y')

        if 'velocity' in ball:
            ball_line['ball_vel_x'] = ball['velocity'].get('x')
            ball_line['ball_vel_y'] = ball['velocity'].get('y')

        if 'acceleration' in ball:
            ball_line['ball_acc_x'] = ball['acceleration'].get('x')
            ball_line['ball_acc_y'] = ball['acceleration'].get('y')

        # Adiciona linha da bola
        combined_data_list.append(ball_line)

        # --- Dados dos robôs ---
        for team in ['allies', 'enemies']:
            robots = frame.get(team, [])
            for robot in robots:
                robot_line = {'timestamp': timestamp, 'team': team, 'robot_id': robot.get('id')}

                if 'position' in robot:
                    robot_line['pos_x'] = robot['position'].get('x')
                    robot_line['pos_y'] = robot['position'].get('y')
                    robot_line['pos_w'] = robot['position'].get('omega')

                if 'velocity' in robot:
                    robot_line['vel_x'] = robot['velocity'].get('x')
                    robot_line['vel_y'] = robot['velocity'].get('y')

                combined_data_list.append(robot_line)
                # Converte para DataFrame único
    df = pd.DataFrame(combined_data_list)
    return df