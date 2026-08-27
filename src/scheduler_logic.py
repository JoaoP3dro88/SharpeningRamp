import sqlite3
from src import db_sqlite

def sync_sql_server_to_sqlite(orders, sql_machines):
    """
    Syncs the exact SQL Server query outputs into local SQLite.
    Keeps existing queue priorities and order states intact.
    """
    db_sqlite.save_machines_cache(sql_machines)
    
    with db_sqlite.get_connection() as conn:
        existing = {row['order_id']: dict(row) for row in conn.execute("SELECT * FROM assignments").fetchall()}
        
        for ord_data in orders:
            order_id = str(ord_data['id'])
            if order_id not in existing:
                conn.execute(
                    """INSERT INTO assignments 
                       (order_id, sap_order_number, machine_name, queue_position, status, 
                        original_qty, remaining_qty, estimated_time, tool_code, open_date)
                       VALUES (?, ?, NULL, -1, 'pending', ?, ?, ?, ?, ?)""",
                    (
                        order_id,
                        str(ord_data['sap_order_number']) if ord_data['sap_order_number'] is not None else "",
                        int(ord_data['qtty']) if ord_data['qtty'] is not None else 0,
                        int(ord_data['qtty']) if ord_data['qtty'] is not None else 0,
                        float(ord_data['lead_time_days']) if ord_data['lead_time_days'] is not None else 0.0,
                        str(ord_data['tool']) if ord_data['tool'] is not None else "",
                        str(ord_data['creation_date']) if ord_data['creation_date'] is not None else ""
                    )
                )
                db_sqlite.log_status_event("IMPORT", order_id, None, "NONE", "pending", justification="Imported from SAP View", conn=conn)
        conn.commit()

def get_unassigned_orders():
    with db_sqlite.get_connection() as conn:
        rows = conn.execute("SELECT * FROM assignments WHERE machine_name IS NULL AND status IN ('pending', 'partial') ORDER BY last_updated DESC").fetchall()
        return [dict(r) for r in rows]

def get_machine_queues():
    with db_sqlite.get_connection() as conn:
        rows = conn.execute("SELECT * FROM assignments WHERE machine_name IS NOT NULL AND status IN ('pending', 'partial', 'delayed') ORDER BY machine_name, queue_position ASC").fetchall()
        queues = {}
        for row in rows:
            m = row['machine_name']
            if m not in queues:
                queues[m] = []
            queues[m].append(dict(row))
        return queues

def update_queue_positions(machine_name, ordered_ids):
    with db_sqlite.get_connection() as conn:
        for idx, o_id in enumerate(ordered_ids):
            row = conn.execute("SELECT machine_name, queue_position, status FROM assignments WHERE order_id = ?", (o_id,)).fetchone()
            if row:
                old_mach, old_pos, old_status = row['machine_name'], row['queue_position'], row['status']
                if old_mach != machine_name or old_pos != idx:
                    conn.execute("UPDATE assignments SET machine_name = ?, queue_position = ?, last_updated = CURRENT_TIMESTAMP WHERE order_id = ?", (machine_name, idx, o_id))
                    db_sqlite.log_status_event("REORDER", o_id, machine_name, old_status, old_status, before_pos=old_pos, after_pos=idx, conn=conn)
        conn.commit()

def check_is_first_in_queue(order_id, machine_name):
    with db_sqlite.get_connection() as conn:
        row = conn.execute(
            "SELECT order_id FROM assignments WHERE machine_name = ? AND status IN ('pending', 'partial', 'delayed') ORDER BY queue_position ASC LIMIT 1",
            (machine_name,)
        ).fetchone()
        return row and str(row['order_id']) == str(order_id)

def complete_order(order_id, machine_name, out_of_order_justification=None):
    is_first = check_is_first_in_queue(order_id, machine_name)
    if not is_first and not out_of_order_justification:
         raise ValueError("Sequence violation! Out-of-order execution requires a justification.")
        
    with db_sqlite.get_connection() as conn:
        rec = conn.execute("SELECT * FROM assignments WHERE order_id = ?", (order_id,)).fetchone()
        conn.execute("UPDATE assignments SET status = 'completed', machine_name = NULL, queue_position = -1, completed_qty = remaining_qty, remaining_qty = 0, last_updated = CURRENT_TIMESTAMP WHERE order_id = ?", (order_id,))
        
        db_sqlite.log_status_event(
            "COMPLETE", order_id, machine_name, rec['status'], "completed",
            before_pos=rec['queue_position'], after_pos=-1, qty_change=rec['remaining_qty'], justification=out_of_order_justification, conn=conn
        )
        conn.commit()
    rebuild_queue_indices(machine_name)

def partial_complete_order(order_id, machine_name, qty_done, out_of_order_justification=None):
    with db_sqlite.get_connection() as conn:
        rec = conn.execute("SELECT * FROM assignments WHERE order_id = ?", (order_id,)).fetchone()
        rem_qty = rec['remaining_qty'] - qty_done
        if rem_qty < 0:
            raise ValueError("Sharpened quantity cannot exceed current remaining balance.")
            
        is_first = check_is_first_in_queue(order_id, machine_name)
        if not is_first and not out_of_order_justification:
            raise ValueError("Sequence violation! Out-of-order execution requires justification.")
            
        if rem_qty == 0:
            complete_order(order_id, machine_name, out_of_order_justification)
            return

        conn.execute(
            """UPDATE assignments SET 
               status = 'partial', machine_name = NULL, queue_position = -1, 
               completed_qty = completed_qty + ?, remaining_qty = ?, 
               last_updated = CURRENT_TIMESTAMP 
               WHERE order_id = ?""",
            (qty_done, rem_qty, order_id)
        )
        db_sqlite.log_status_event(
            "PARTIAL", order_id, machine_name, rec['status'], "partial",
            before_pos=rec['queue_position'], after_pos=-1, qty_change=qty_done, justification=out_of_order_justification, conn=conn
        )
        conn.commit()
    rebuild_queue_indices(machine_name)

def delay_order(order_id, machine_name, justification):
    if not check_is_first_in_queue(order_id, machine_name):
        raise ValueError("Only the active item first in queue can be delayed.")
        
    with db_sqlite.get_connection() as conn:
        max_pos = conn.execute("SELECT COALESCE(MAX(queue_position), 0) FROM assignments WHERE machine_name = ?", (machine_name,)).fetchone()[0]
        rec = conn.execute("SELECT queue_position FROM assignments WHERE order_id = ?", (order_id,)).fetchone()
        
        conn.execute(
            "UPDATE assignments SET queue_position = ?, status = 'pending', last_updated = CURRENT_TIMESTAMP WHERE order_id = ?",
            (max_pos + 1, order_id)
        )
        db_sqlite.log_status_event(
            "DELAY", order_id, machine_name, "pending", "delayed",
            before_pos=rec['queue_position'], after_pos=max_pos + 1, justification=justification, conn=conn
        )
        conn.commit()
    rebuild_queue_indices(machine_name)

def cancel_or_remove_order(order_id, machine_name=None, justification="Manual cancellation"):
    with db_sqlite.get_connection() as conn:
        rec = conn.execute("SELECT * FROM assignments WHERE order_id = ?", (order_id,)).fetchone()
        conn.execute("UPDATE assignments SET status = 'cancelled', machine_name = NULL, queue_position = -1, last_updated = CURRENT_TIMESTAMP WHERE order_id = ?", (order_id,))
        db_sqlite.log_status_event("CANCEL", order_id, machine_name, rec['status'], "cancelled", justification=justification, conn=conn)
        conn.commit()
    if machine_name:
        rebuild_queue_indices(machine_name)

def rebuild_queue_indices(machine_name):
    with db_sqlite.get_connection() as conn:
        rows = conn.execute(
            "SELECT order_id FROM assignments WHERE machine_name = ? AND status IN ('pending', 'partial', 'delayed') ORDER BY queue_position ASC",
            (machine_name,)
        ).fetchall()
        for idx, row in enumerate(rows):
            conn.execute("UPDATE assignments SET queue_position = ? WHERE order_id = ?", (idx, row['order_id']))
        conn.commit()
