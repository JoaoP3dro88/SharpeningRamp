import sys
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QScrollArea, QFrame, QMessageBox, QInputDialog
)
from src import db_sqlite, scheduler_logic, db_sql_server

# Theme Styling Sheet
APP_STYLING = """
QMainWindow { background-color: #121212; }
QLabel { color: #ECEFF1; font-family: 'Segoe UI'; }
QPushButton {
    background-color: #1E1E1E; color: #ECEFF1; border: 1px solid #333333;
    padding: 8px 14px; border-radius: 4px; font-weight: bold;
}
QPushButton:hover { background-color: #2D2D2D; border: 1px solid #00E5FF; }
QPushButton:disabled { color: #555555; background-color: #151515; border: 1px solid #222222; }
QFrame#OrderCard {
    background-color: #1E1E1E; border: 1px solid #2C2C2C; border-radius: 6px; padding: 10px;
}
QFrame#OrderCard:hover { border: 1px solid #00E5FF; }
QFrame#MachineContainer {
    background-color: #161616; border: 2px dashed #2A2A2A; border-radius: 8px; margin: 4px;
}
"""

class DraggableOrderCard(QFrame):
    """Interactive Order Card mapped directly to the ERP data columns."""
    
    def __init__(self, order_data, is_production_mode=False, controller=None):
        super().__init__()
        self.setObjectName("OrderCard")
        self.order_data = order_data
        self.is_production_mode = is_production_mode
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Primary details mapping the SQL variables
        title_font = QFont("Segoe UI", 10, QFont.Bold)
        title = QLabel(f"ID: #{self.order_data['order_id']}")
        title.setFont(title_font)
        layout.addWidget(title)
        
        sap_info = QLabel(f"SAP Ref: {self.order_data['sap_order_number']}")
        sap_info.setStyleSheet("color: #B0BEC5; font-size: 11px;")
        layout.addWidget(sap_info)
        
        tool_info = QLabel(f"Tool: {self.order_data['tool_code']}")
        tool_info.setStyleSheet("color: #ECEFF1; font-size: 12px; font-weight: 500;")
        layout.addWidget(tool_info)
        
        # Bottom parameters row
        meta_layout = QHBoxLayout()
        qty = QLabel(f"Qty: {self.order_data['remaining_qty']} / {self.order_data['original_qty']}")
        qty.setStyleSheet("font-size: 11px; color: #00E5FF;")
        
        # Map LeadTimePlanejado (lead_time_days) to time representation
        lead_time = QLabel(f"LT: {self.order_data['estimated_time']} Days")
        lead_time.setStyleSheet("font-size: 11px; color: #FFB300;")
        
        meta_layout.addWidget(qty)
        meta_layout.addWidget(lead_time)
        layout.addLayout(meta_layout)
        
        # Action Buttons
        self.actions_widget = QWidget()
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 4, 0, 0)
        actions_layout.setSpacing(4)

        self.btn_complete = QPushButton("Complete")
        self.btn_partial = QPushButton("Partial")
        self.btn_delay = QPushButton("Delay")

        self.btn_complete.clicked.connect(self.on_complete)
        self.btn_partial.clicked.connect(self.on_partial)
        self.btn_delay.clicked.connect(self.on_delay)

        actions_layout.addWidget(self.btn_complete)
        actions_layout.addWidget(self.btn_partial)
        actions_layout.addWidget(self.btn_delay)
        layout.addWidget(self.actions_widget)

        # Remove: SEMPRE visível, em qualquer modo
        self.btn_remove = QPushButton("X")
        self.btn_remove.setStyleSheet("background-color: #C62828; color: #FFFFFF;")
        self.btn_remove.clicked.connect(self.on_remove)
        layout.addWidget(self.btn_remove)

        self.set_mode(self.is_production_mode)

    def set_mode(self, production_mode):
        self.is_production_mode = production_mode
        self.actions_widget.setVisible(production_mode)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_production_mode:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.order_data['order_id']))
            drag.setMimeData(mime)
            drag.exec_(Qt.MoveAction)

    def on_complete(self):
        m_name = self.order_data['machine_name']
        is_first = scheduler_logic.check_is_first_in_queue(self.order_data['order_id'], m_name)
        just = None
        if not is_first:
            just, ok = QInputDialog.getText(self, "Sequence Justification", "This order is out of sequence. Provide a mandatory explanation:")
            if not ok or not just.strip():
                return
        try:
            scheduler_logic.complete_order(self.order_data['order_id'], m_name, just)
            self.controller.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Execution Error", str(e))

    def on_partial(self):
        if self.order_data['remaining_qty'] <= 1:
            QMessageBox.information(self, "Use Complete", "Só resta 1 unidade — use o botão Complete em vez de Partial.")
            return
        m_name = self.order_data['machine_name']
        is_first = scheduler_logic.check_is_first_in_queue(self.order_data['order_id'], m_name)
        just = None
        if not is_first:
            just, ok = QInputDialog.getText(self, "Sequence Justification", "This order is out of sequence. Provide a mandatory explanation:")
            if not ok or not just.strip():
                return
                
        qty_done, ok_qty = QInputDialog.getInt(self, "Partial Completion", "How many tools were sharpened?", min=1, max=self.order_data['remaining_qty']-1)
        if not ok_qty:
            return
            
        try:
            scheduler_logic.partial_complete_order(self.order_data['order_id'], m_name, qty_done, just)
            self.controller.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Execution Error", str(e))

    def on_delay(self):
        m_name = self.order_data['machine_name']
        if not scheduler_logic.check_is_first_in_queue(self.order_data['order_id'], m_name):
            QMessageBox.warning(self, "Access Restriction", "Only the active item first in queue can be delayed.")
            return
        just, ok = QInputDialog.getText(self, "Delay Justification", "Provide a mandatory explanation for delay:")
        if ok and just.strip():
            scheduler_logic.delay_order(self.order_data['order_id'], m_name, just)
            self.controller.refresh_ui()

    def on_remove(self):
        just, ok = QInputDialog.getText(self, "Cancel / Remove Order", "State reason for removing this order:")
        if ok and just.strip():
            scheduler_logic.cancel_or_remove_order(self.order_data['order_id'], self.order_data.get('machine_name'), just)
            self.controller.refresh_ui()


class MachineContainer(QFrame):
    """Drag-and-Drop recipient container for specific machine lines."""
    
    def __init__(self, machine_name, controller):
        super().__init__()
        self.setObjectName("MachineContainer")
        self.setAcceptDrops(True)
        self.machine_name = machine_name
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        # Header Status
        header_layout = QHBoxLayout()
        title_font = QFont("Segoe UI", 11, QFont.Bold)
        self.lbl_title = QLabel(self.machine_name)
        self.lbl_title.setFont(title_font)
        
        self.lbl_time = QLabel("Allocated: 0d")
        self.lbl_time.setStyleSheet("color: #FFB300; font-weight: bold; font-size: 11px;")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_time)
        self.main_layout.addLayout(header_layout)
        
        # List Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #121212; border: none;")
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.cards_container)
        self.main_layout.addWidget(self.scroll)

    def set_orders(self, orders, is_production_mode):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        total_lead_time = 0.0
        for ord_data in orders:
            card = DraggableOrderCard(ord_data, is_production_mode, self.controller)
            self.cards_layout.addWidget(card)
            total_lead_time += ord_data['estimated_time'] or 0.0
            
        self.lbl_time.setText(f"Total LT: {total_lead_time:.1f}d")

    def dragEnterEvent(self, event):
        if not self.controller.is_production_mode:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if not self.controller.is_production_mode:
            event.acceptProposedAction()

    def dropEvent(self, event):
        order_id = event.mimeData().text()
        # Converte a posição do evento (relativa a self) para o referencial do cards_container
        local_pos = self.cards_container.mapFrom(self, event.position().toPoint())
        target_index = 0
        for i in range(self.cards_layout.count()):
            child = self.cards_layout.itemAt(i).widget()
            if child and local_pos.y() > (child.y() + child.height() / 2):
                target_index = i + 1

        self.controller.assign_order_to_machine(order_id, self.machine_name, target_index)
        event.acceptProposedAction()


class SchedulerMainWindow(QMainWindow):
    """Main window coordinating state, synchronization, and layout."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Titan Sharpening Scheduler")
        self.resize(1366, 768)
        self.setStyleSheet(APP_STYLING)
        
        self.is_production_mode = (db_sqlite.get_app_mode() == 'production')
        self.init_ui()
        self.refresh_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header Controls
        top_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Refresh SQL Server Data")
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)
        
        self.lbl_mode_status = QLabel("Current Mode: PLANNING")
        self.lbl_mode_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #00E5FF;")
        
        self.btn_toggle_mode = QPushButton("Switch to Production Mode")
        self.btn_toggle_mode.clicked.connect(self.toggle_mode)
        
        top_layout.addWidget(self.btn_refresh)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_mode_status)
        top_layout.addWidget(self.btn_toggle_mode)
        main_layout.addLayout(top_layout)
        
        # Grid Content Layout
        content_layout = QHBoxLayout()
        
        # Unassigned Pool
        unassigned_frame = QFrame()
        unassigned_frame.setFixedWidth(300)
        unassigned_frame.setStyleSheet("background-color: #161616; border-radius: 8px;")
        unassigned_layout = QVBoxLayout(unassigned_frame)
        
        lbl_unassigned = QLabel("📋 Unassigned Orders")
        lbl_unassigned.setFont(QFont("Segoe UI", 11, QFont.Bold))
        unassigned_layout.addWidget(lbl_unassigned)
        
        self.unassigned_scroll = QScrollArea()
        self.unassigned_scroll.setWidgetResizable(True)
        self.unassigned_scroll.setStyleSheet("background: transparent; border: none;")
        self.unassigned_container = QWidget()
        self.unassigned_cards_layout = QVBoxLayout(self.unassigned_container)
        self.unassigned_cards_layout.setAlignment(Qt.AlignTop)
        self.unassigned_scroll.setWidget(self.unassigned_container)
        unassigned_layout.addWidget(self.unassigned_scroll)
        content_layout.addWidget(unassigned_frame)
        
        # Scrollable Grid of Machines
        self.machines_area = QWidget()
        self.machines_layout = QHBoxLayout(self.machines_area)
        self.machines_layout.setContentsMargins(0, 0, 0, 0)
        
        machines_scroll = QScrollArea()
        machines_scroll.setWidgetResizable(True)
        machines_scroll.setStyleSheet("background: transparent; border: none;")
        machines_scroll.setWidget(self.machines_area)
        
        content_layout.addWidget(machines_scroll)
        main_layout.addLayout(content_layout)
        
        self.update_mode_ui_elements()

    def update_mode_ui_elements(self):
        if self.is_production_mode:
            self.lbl_mode_status.setText("🔒 Mode: PRODUCTION ACTIVE")
            self.lbl_mode_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #FF1744;")
            self.btn_toggle_mode.setText("🔓 Switch to Planning Mode")
            self.btn_refresh.setEnabled(False)
        else:
            self.lbl_mode_status.setText("✏️ Mode: PLANNING")
            self.lbl_mode_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #00E5FF;")
            self.btn_toggle_mode.setText("🔒 Begin Production Session")
            self.btn_refresh.setEnabled(True)

    def toggle_mode(self):
        self.is_production_mode = not self.is_production_mode
        db_sqlite.set_app_mode('production' if self.is_production_mode else 'planning')
        self.update_mode_ui_elements()
        self.refresh_ui()

    def on_refresh_clicked(self):
        try:
            data = db_sql_server.fetch_sql_server_data()
            scheduler_logic.sync_sql_server_to_sqlite(data['orders'], data['machines'])
            QMessageBox.information(self, "Success", "Synchronized successfully with local SQLite.")
        except Exception as e:
            QMessageBox.warning(self, "Connection Resiliency Active", f"Using offline cache.\nDetails: {str(e)}")
        self.refresh_ui()

    def assign_order_to_machine(self, order_id, machine_name, target_idx):
        queues = scheduler_logic.get_machine_queues()
        mach_queue = queues.get(machine_name, [])
        ordered_ids = [str(o['order_id']) for o in mach_queue]
        
        if order_id in ordered_ids:
            ordered_ids.remove(order_id)
        ordered_ids.insert(target_idx, order_id)
        
        scheduler_logic.update_queue_positions(machine_name, ordered_ids)
        self.refresh_ui()

    def refresh_ui(self):
        # 1. Refresh Unassigned Pool
        while self.unassigned_cards_layout.count():
            item = self.unassigned_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        unassigned_orders = scheduler_logic.get_unassigned_orders()
        for ord_data in unassigned_orders:
            card = DraggableOrderCard(ord_data, self.is_production_mode, self)
            self.unassigned_cards_layout.addWidget(card)
            
        # 2. Rebuild Machine Views
        m_list = db_sqlite.get_cached_machines()
        if not m_list:
            m_list = ["Station-01", "Station-02"]  # Default offline development machines
            
        while self.machines_layout.count():
            item = self.machines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        queues = scheduler_logic.get_machine_queues()
        for machine_name in m_list:
            container = MachineContainer(machine_name, self)
            container.set_orders(queues.get(machine_name, []), self.is_production_mode)
            self.machines_layout.addWidget(container)
