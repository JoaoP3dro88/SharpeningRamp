import pyodbc
from src.config_loader import get_sql_config
from src.queries import GET_ACTIVE_ORDERS_QUERY, GET_MACHINES_QUERY

def fetch_sql_server_data():
    """
    Attempts to fetch active orders and machines.
    Returns a dictionary of results if successful, raises an exception if connection fails.
    """
    cfg = get_sql_config()
    conn_str = (
        f"DRIVER={{{cfg['Driver']}}};"
        f"SERVER={cfg['Server']};"
        f"DATABASE={cfg['Database']};"
        f"UID={cfg['UID']};"
        f"PWD={cfg['PWD']};"
        f"Connection Timeout={cfg['Timeout']};"
    )
    
    orders = []
    machines = []
    
    # Establish connection with context manager
    with pyodbc.connect(conn_str) as conn:
        with conn.cursor() as cursor:
            # 1. Fetch Machines
            cursor.execute(GET_MACHINES_QUERY)
            columns = [column[0] for column in cursor.description]
            for row in cursor.fetchall():
                machines.append(dict(zip(columns, row)))
                
            # 2. Fetch Orders
            cursor.execute(GET_ACTIVE_ORDERS_QUERY)
            columns = [column[0] for column in cursor.description]
            for row in cursor.fetchall():
                orders.append(dict(zip(columns, row)))
                
    return {"machines": machines, "orders": orders}
