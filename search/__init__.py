from . import open_ai_upwork_main

def search(input_data, limit_st, offset, keys):
    return open_ai_upwork_main.search(input_data, limit_st, offset, keys)