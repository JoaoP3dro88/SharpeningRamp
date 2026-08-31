import sys
from PySide6.QtCore import Qt, QMimeData, QTimer
from PySide6.QtGui import QDrag, QFont, QColor, QPainter
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QFrame, QMessageBox, QInputDialog,
    QGraphicsDropShadowEffect, QAbstractButton
)
from src import db_sqlite, scheduler_logic, db_sql_server

# ------------------------------------------------------------------
# Theme: paleta clara, moderna e amigável (substitui o tema dark antigo)
# ------------------------------------------------------------------
COLORS = {
    "bg": "#F4F6FA",
    "surface": "#FFFFFF",
    "border": "#E2E5EA",
    "text": "#1F2937",
    "text_muted": "#6B7280",
    "primary": "#4F46E5",
    "primary_hover": "#EEF2FF",
    "success": "#10B981",
    "success_bg": "#ECFDF5",
    "warning": "#F59E0B",
    "warning_bg": "#FFFBEB",
    "danger": "#EF4444",
    "danger_bg": "#FEF2F2",
    "info": "#0EA5E9",
    "info_bg": "#F0F9FF",
}

APP_STYLING = f"""
QMainWindow {{ 
    background-color: {COLORS['bg']}; 
}}

QWidget {{ 
    font-family: 'Segoe UI', 'Inter', sans-serif; 
}}

QLabel {{ 
    color: {COLORS['text']};
}}

QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid transparent;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {COLORS['primary_hover']};
    border: 1px solid {COLORS['primary']};
    color: {COLORS['primary']};
}}
QPushButton:pressed {{ background-color: #E0E7FF; }}
QPushButton:disabled {{
    color: #B0B7C3; background-color: #F9FAFB; border: 1px solid #EEF0F3;
}}

QFrame#MachineContainer {{
    background-color: #FAFBFD;
    border-radius: 14px;
}}

QFrame#UnassignedPanel {{
    background-color: #FAFBFD;
    border-radius: 14px;
}}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0px; }}
QScrollBar::handle:vertical {{ background: #D1D5DB; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #9CA3AF; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 0px 0px 0px; }}
QScrollBar::handle:horizontal {{ background: #D1D5DB; border-radius: 5px; min-width: 32px; }}
QScrollBar::handle:horizontal:hover {{ background: #9CA3AF; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QDialog, QMessageBox, QInputDialog {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
}}
QLineEdit, QSpinBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid #D7DBE3;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {COLORS['primary']};
}}
"""


def soft_shadow(blur=20, y_offset=3, alpha=25):
    """Cria uma sombra suave para dar sensação de profundidade aos cards."""
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(17, 24, 39, alpha))
    return effect


class ToggleSwitch(QAbstractButton):
    """Switch estilo iOS para alternar entre Planejamento e Produção."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(52, 28)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        track_color = QColor(COLORS["danger"]) if self.isChecked() else QColor("#D1D5DB")
        painter.setBrush(track_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)

        knob_d = self.height() - 4
        knob_x = self.width() - knob_d - 2 if self.isChecked() else 2
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_x, 2, knob_d, knob_d)


class HorizontalScrollArea(QScrollArea):
    """QScrollArea que também rola na horizontal usando a roda do mouse.

    Necessário porque, com muitas máquinas lado a lado, o usuário precisa
    navegar horizontalmente e a roda do mouse por padrão só rola no eixo
    vertical (o que fazia o conteúdo parecer 'cortado' e sem forma de
    ser alcançado).
    """

    def wheelEvent(self, event):
        if self.horizontalScrollBar().maximum() > 0:
            delta = event.angleDelta().y() or event.angleDelta().x()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)


def make_badge(text, fg, bg):
    """Label estilo 'pill' usado para status/metadados (qty, lead time, etc)."""
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {fg};
        background-color: {bg};
        font-size: 11px;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 9px;
    """)
    return lbl


class DraggableOrderCard(QFrame):
    """Interactive Order Card mapped directly to the ERP data columns."""

    def __init__(self, order_data, is_production_mode=False, controller=None):
        super().__init__()
        self.setObjectName("OrderCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.order_data = order_data
        self.is_production_mode = is_production_mode
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        # Borda aplicada diretamente no widget (não depende da cascata de QSS
        # herdada do QMainWindow, que pode ser "cortada" por stylesheets
        # intermediários definidos em widgets pais, como os containers de scroll)
        self.setStyleSheet(f"""
            #OrderCard {{
                background-color: {COLORS['surface']};
                border: 1.5px solid #B7BEC9;
                border-radius: 12px;
            }}
            #OrderCard:hover {{
                border: 1.5px solid {COLORS['primary']};
            }}
        """)
        # Borda fina + sombra em todo card, para deixar claro onde ele começa e termina
        self.setGraphicsEffect(soft_shadow(blur=14, y_offset=2, alpha=25))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Linha 1: ID da ordem + ferramenta + botão remover (ícone), tudo lado a lado
        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        title = QLabel(f"⋮⋮ #{self.order_data['order_id']}")
        title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        header_row.addWidget(title)

        tool_info = QLabel(f"🔧 {self.order_data['tool_code']}")
        tool_info.setStyleSheet(f"color: {COLORS['primary']}; font-size: 11px; font-weight: 600;")
        header_row.addWidget(tool_info)
        header_row.addStretch()

        # Remove: SEMPRE visível, agora como ícone compacto no cabeçalho
        self.btn_remove = QPushButton("🗑")
        self.btn_remove.setToolTip("Remover")
        self.btn_remove.setFixedSize(22, 22)
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #FECACA;
                border-radius: 6px;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                border: 1px solid #EF4444;
            }
        """)
        self.btn_remove.clicked.connect(self.on_remove)
        header_row.addWidget(self.btn_remove)
        layout.addLayout(header_row)

        # Linha 2: SAP ref + data de abertura, lado a lado
        info_row = QHBoxLayout()
        info_row.setSpacing(10)
        sap_info = QLabel(f"SAP: {self.order_data['sap_order_number']}")
        sap_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        open_date = QLabel(f"📅 {self.order_data['open_date']}")
        open_date.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        info_row.addWidget(sap_info)
        info_row.addWidget(open_date)
        info_row.addStretch()
        layout.addLayout(info_row)

        # Linha 3: badges (quantidade + lead time)
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(6)
        qty = make_badge(
            f"Qtd: {self.order_data['remaining_qty']}/{self.order_data['original_qty']}",
            COLORS["info"], COLORS["info_bg"]
        )
        lead_time = make_badge(
            f"⏱ {self.order_data['estimated_time']}d",
            COLORS["warning"], COLORS["warning_bg"]
        )
        meta_layout.addWidget(qty)
        meta_layout.addWidget(lead_time)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Botões de ação (modo produção) — compactos, só ícone com tooltip
        self.actions_widget = QWidget()
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 4, 0, 0)
        actions_layout.setSpacing(4)

        self.btn_complete = QPushButton("✓")
        self.btn_complete.setToolTip("Completar")
        self.btn_complete.setStyleSheet(self._action_style(COLORS["success"], COLORS["success_bg"]))

        self.btn_partial = QPushButton("◐")
        self.btn_partial.setToolTip("Parcial")
        self.btn_partial.setStyleSheet(self._action_style(COLORS["warning"], COLORS["warning_bg"]))

        self.btn_delay = QPushButton("⏸")
        self.btn_delay.setToolTip("Atrasar")
        self.btn_delay.setStyleSheet(self._action_style(COLORS["danger"], COLORS["danger_bg"]))

        self.btn_complete.clicked.connect(self.on_complete)
        self.btn_partial.clicked.connect(self.on_partial)
        self.btn_delay.clicked.connect(self.on_delay)

        actions_layout.addWidget(self.btn_complete)
        actions_layout.addWidget(self.btn_partial)
        actions_layout.addWidget(self.btn_delay)
        actions_layout.addStretch()
        layout.addWidget(self.actions_widget)

        self.set_mode(self.is_production_mode)

    @staticmethod
    def _action_style(color, bg):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {bg};
                border-radius: 6px;
                font-size: 12px;
                padding: 0px;
                min-width: 26px;
                max-width: 26px;
                min-height: 24px;
                max-height: 24px;
            }}
            QPushButton:hover {{
                border: 1px solid {color};
            }}
        """

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
            just, ok = QInputDialog.getText(self, "Justificativa de Sequência", "Esta ordem está fora de sequência. Forneça uma explicação obrigatória:")
            if not ok or not just.strip():
                return
        try:
            scheduler_logic.complete_order(self.order_data['order_id'], m_name, just)
            self.controller.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Execução", str(e))

    def on_partial(self):
        if self.order_data['remaining_qty'] <= 1:
            QMessageBox.information(self, "Use Completar", "Só resta 1 unidade — use o botão Completar em vez de Parcial.")
            return
        m_name = self.order_data['machine_name']
        is_first = scheduler_logic.check_is_first_in_queue(self.order_data['order_id'], m_name)
        just = None
        if not is_first:
            just, ok = QInputDialog.getText(self, "Justificativa de Sequência", "Esta ordem está fora de sequência. Forneça uma explicação obrigatória:")
            if not ok or not just.strip():
                return

        qty_done, ok_qty = QInputDialog.getInt(self, "Conclusão Parcial", "Quantas ferramentas foram afiadas?", min=1, max=self.order_data['remaining_qty']-1)
        if not ok_qty:
            return

        try:
            scheduler_logic.partial_complete_order(self.order_data['order_id'], m_name, qty_done, just)
            self.controller.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Execução", str(e))

    def on_delay(self):
        m_name = self.order_data['machine_name']
        if not scheduler_logic.check_is_first_in_queue(self.order_data['order_id'], m_name):
            QMessageBox.warning(self, "Restrição de Acesso", "Apenas o item ativo, primeiro da fila, pode ser atrasado.")
            return
        just, ok = QInputDialog.getText(self, "Justificativa de Atraso", "Forneça uma explicação obrigatória para o atraso:")
        if ok and just.strip():
            scheduler_logic.delay_order(self.order_data['order_id'], m_name, just)
            self.controller.refresh_ui()

    def on_remove(self):
        just, ok = QInputDialog.getText(self, "Cancelar / Remover Ordem", "Informe o motivo da remoção desta ordem:")
        if ok and just.strip():
            scheduler_logic.cancel_or_remove_order(self.order_data['order_id'], self.order_data.get('machine_name'), just)
            self.controller.refresh_ui()


class MachineContainer(QFrame):
    """Drag-and-Drop recipient container for specific machine lines."""

    def __init__(self, machine_name, controller):
        super().__init__()
        self.setObjectName("MachineContainer")
        self.setAcceptDrops(True)
        self.setMinimumWidth(280)
        self.machine_name = machine_name
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)

        # Header Status
        header_layout = QHBoxLayout()
        title_font = QFont("Segoe UI", 11, QFont.Bold)
        self.lbl_title = QLabel(f"🖥  {self.machine_name}")
        self.lbl_title.setFont(title_font)

        self.lbl_time = make_badge("Total: 0d", COLORS["warning"], COLORS["warning_bg"])

        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_time)
        self.main_layout.addLayout(header_layout)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        self.main_layout.addWidget(divider)

        # List Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
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

        if not orders:
            empty_lbl = QLabel("Nenhuma ordem nesta máquina")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding: 16px;")
            self.cards_layout.addWidget(empty_lbl)

        self.lbl_time.setText(f"Total: {total_lead_time:.1f}d")

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
        self.setWindowTitle("Sharpening Scheduler")
        self.resize(1400, 800)
        self.setStyleSheet(APP_STYLING)

        self.is_production_mode = (db_sqlite.get_app_mode() == 'production')
        self.init_ui()
        self.refresh_ui()

        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.refresh_ui)
        self.sync_timer.start(10000)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        # Header Controls
        top_frame = QFrame()
        top_frame.setStyleSheet(f"""
            background-color: {COLORS['surface']};
            border-radius: 12px;
        """)
        top_frame.setGraphicsEffect(soft_shadow(blur=14, y_offset=2, alpha=14))
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(18, 14, 18, 14)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        app_title = QLabel("⚙️ Sharpening Scheduler")
        app_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        app_subtitle = QLabel("Planejamento e acompanhamento de afiação de ferramentas")
        app_subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        title_box.addWidget(app_title)
        title_box.addWidget(app_subtitle)

        self.btn_refresh = QPushButton("🔄  Atualizar dados (SQL Server)")
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)

        self.lbl_mode_status = QLabel("Planejamento")
        self.lbl_mode_status.setFont(QFont("Segoe UI", 10, QFont.Bold))

        self.toggle_mode_switch = ToggleSwitch()
        self.toggle_mode_switch.setChecked(self.is_production_mode)
        self.toggle_mode_switch.toggled.connect(self.toggle_mode)

        top_layout.addLayout(title_box)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_refresh)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.lbl_mode_status)
        top_layout.addSpacing(6)
        top_layout.addWidget(self.toggle_mode_switch)
        main_layout.addWidget(top_frame)

        # Grid Content Layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Unassigned Pool
        unassigned_frame = QFrame()
        unassigned_frame.setObjectName("UnassignedPanel")
        unassigned_frame.setFixedWidth(300)
        unassigned_frame.setGraphicsEffect(soft_shadow(blur=14, y_offset=2, alpha=12))
        unassigned_layout = QVBoxLayout(unassigned_frame)
        unassigned_layout.setContentsMargins(14, 14, 14, 14)
        unassigned_layout.setSpacing(10)

        lbl_unassigned = QLabel("📋  Ordens Não Alocados")
        lbl_unassigned.setFont(QFont("Segoe UI", 11, QFont.Bold))
        unassigned_layout.addWidget(lbl_unassigned)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        unassigned_layout.addWidget(divider)

        self.unassigned_scroll = QScrollArea()
        self.unassigned_scroll.setWidgetResizable(True)
        self.unassigned_scroll.setStyleSheet("background: transparent; border: none;")
        self.unassigned_container = QWidget()
        self.unassigned_container.setStyleSheet("background: transparent;")
        self.unassigned_cards_layout = QVBoxLayout(self.unassigned_container)
        self.unassigned_cards_layout.setSpacing(8)
        self.unassigned_cards_layout.setAlignment(Qt.AlignTop)
        self.unassigned_scroll.setWidget(self.unassigned_container)
        unassigned_layout.addWidget(self.unassigned_scroll)
        content_layout.addWidget(unassigned_frame)

        # Scrollable Grid of Machines (rola na horizontal quando há muitas máquinas)
        self.machines_area = QWidget()
        self.machines_area.setStyleSheet("background: transparent;")
        self.machines_layout = QHBoxLayout(self.machines_area)
        self.machines_layout.setContentsMargins(0, 0, 4, 0)
        self.machines_layout.setSpacing(14)
        self.machines_layout.setSizeConstraint(QHBoxLayout.SetMinAndMaxSize)

        machines_scroll = HorizontalScrollArea()
        machines_scroll.setWidgetResizable(True)
        machines_scroll.setStyleSheet("background: transparent; border: none;")
        machines_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        machines_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        machines_scroll.setWidget(self.machines_area)

        content_layout.addWidget(machines_scroll)
        main_layout.addLayout(content_layout)

        self.update_mode_ui_elements()

    def update_mode_ui_elements(self):
        if self.is_production_mode:
            self.lbl_mode_status.setText("🔒 Produção")
            self.lbl_mode_status.setStyleSheet(f"color: {COLORS['danger']};")
            self.btn_refresh.setEnabled(False)
        else:
            self.lbl_mode_status.setText("✏️ Planejamento")
            self.lbl_mode_status.setStyleSheet(f"color: {COLORS['primary']};")
            self.btn_refresh.setEnabled(True)
        self.toggle_mode_switch.setChecked(self.is_production_mode)
        self.toggle_mode_switch.update()

    def toggle_mode(self, checked):
        self.is_production_mode = checked
        db_sqlite.set_app_mode('production' if self.is_production_mode else 'planning')
        self.update_mode_ui_elements()
        self.refresh_ui()

    def on_refresh_clicked(self):
        try:
            data = db_sql_server.fetch_sql_server_data()
            scheduler_logic.sync_sql_server_to_sqlite(data['orders'], data['machines'])
            QMessageBox.information(self, "Sucesso", "Sincronizado com sucesso com o SQLite local.")
        except Exception as e:
            QMessageBox.warning(self, "Resiliência de Conexão Ativa", f"Usando cache offline.\nDetalhes: {str(e)}")
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
        unassigned_orders = sorted(unassigned_orders, key=lambda o: o['open_date'])
        for ord_data in unassigned_orders:
            card = DraggableOrderCard(ord_data, self.is_production_mode, self)
            self.unassigned_cards_layout.addWidget(card)

        if not unassigned_orders:
            empty_lbl = QLabel("Nenhuma ordem pendente 🎉")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding: 16px;")
            self.unassigned_cards_layout.addWidget(empty_lbl)

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