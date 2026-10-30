from api import load_data

def refresh():
    return load_data("orders")
