"""
Isolates all read-only SQL Server ERP queries.
These queries act as a data contract; changing columns here has zero impact on core system UI logic.
"""

# Query active tool sharpening orders from the last 12 months
GET_ACTIVE_ORDERS_QUERY = """
SELECT 
    IdOrdem AS id,
    NroOrdemSAP AS sap_order_number,
    Ferramenta AS tool,
    Quantidade AS qtty,
    LeadTimePlanejado AS lead_time_days,
    DataAbertura AS creation_date
FROM vw_TurnoverManagementOrders
WHERE Processo LIKE 'Afia%'
  AND Status LIKE 'Aberta'
  AND DataAbertura >= DATEADD(MONTH, -12, GETDATE())
ORDER BY DataAbertura DESC;
"""

# Query active sharpening line machines
GET_MACHINES_QUERY = """
SELECT DISTINCT 
    Machine AS machine_name
FROM ViewHistoricoAfiacao
WHERE Machine NOT LIKE 'Stream';
"""
