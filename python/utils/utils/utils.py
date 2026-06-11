from datetime import datetime
import pathlib
import pandas as pd
import enum
import numpy as np

class LogFields(enum.Enum):
    RAW_FRAME = 0
    PROCESSED_FRAME = 1
    RAW_REFEREE = 2
    REFEREE = 3
    TELEMETRY = 4
    ROBOTS_COMMAND = 5

def output_path()->str:
    out_dir = './output_files'
    out_path = pathlib.Path(out_dir).resolve()
    return str(out_path)

OUTPUT_DIR = output_path()

def data_frame_to_csv(data_frame:pd.DataFrame, select_columns:list, file_name:str=None):
    if file_name is None:
        file_name = get_current_date_time()

    file_name = file_name.split('.')[0]
    data_frame[select_columns].to_csv(output_path() + '/' + file_name + '.csv')

def get_current_date_time():
    now = datetime.now()
    return now.strftime("%d-%m-%Y_%H:%M:%S")

def gel_2d_length_in_column(frame, column_name:str) -> pd.DataFrame:
    return np.sqrt(frame[(column_name +'_x')]**2 + frame[(column_name +'_y')]**2)