import winreg
import pyodbc

DRIVER_NAME = "Rampa Afiacao ODBC Driver 17"
DRIVER_PATH = r"C:\Users\klj1ct\Desktop\SharpeningRamp\dist\Rampa de afiacao\drivers\odbc\msodbcsql17.dll"


def ensure_driver_registered(driver_path: str):
    """
    Registra o driver ODBC bundlado em HKCU (não exige admin),
    de forma idempotente -- seguro chamar toda vez.
    """
    base = r"SOFTWARE\ODBC\ODBCINST.INI"

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{base}\\{DRIVER_NAME}") as key:
        winreg.SetValueEx(key, "Driver", 0, winreg.REG_SZ, driver_path)
        winreg.SetValueEx(key, "Setup", 0, winreg.REG_SZ, driver_path)
        winreg.SetValueEx(key, "APILevel", 0, winreg.REG_SZ, "2")
        winreg.SetValueEx(key, "ConnectFunctions", 0, winreg.REG_SZ, "YYY")
        winreg.SetValueEx(key, "DriverODBCVer", 0, winreg.REG_SZ, "03.80")
        winreg.SetValueEx(key, "FileUsage", 0, winreg.REG_SZ, "0")
        winreg.SetValueEx(key, "SQLLevel", 0, winreg.REG_SZ, "1")
        winreg.SetValueEx(key, "UsageCount", 0, winreg.REG_DWORD, 1)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{base}\\ODBC Drivers") as key:
        winreg.SetValueEx(key, DRIVER_NAME, 0, winreg.REG_SZ, "Installed")

    print(f"Driver registrado em HKCU\\{base}\\{DRIVER_NAME}")


def testar_conexao():
    conn_str = (
        f"DRIVER={{{DRIVER_NAME}}};"
        f"SERVER=10.21.71.70;"
        f"DATABASE=ToolManagement;"
        f"UID=toolmanagementtableau;"
        f"PWD=toolmanagementtableaudev;"
        f"Connection Timeout=5;"
    )
    print(repr(conn_str))

    try:
        conn = pyodbc.connect(conn_str)
        print("Conectou com sucesso!")
        conn.close()
    except pyodbc.Error as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    ensure_driver_registered(DRIVER_PATH)
    testar_conexao()