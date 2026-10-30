from api import fetch_data

def refresh():
    return fetch_data("orders")
