from . import open_ai_upwork_main

def search(input_file_path, limit_st, limit_tot):
    return open_ai_upwork_main.search(input_file_path, limit_st, limit_tot)