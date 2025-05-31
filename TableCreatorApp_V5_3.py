import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QFrame, QFileDialog, QMessageBox, QDialog, QTextBrowser
)
from PyQt6.QtCore import Qt
import sqlite3
import os

class TableCreatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Creation V5.2 - PyQt6")
        self.setGeometry(100, 100, 900, 700)

        # Initialize database connection
        self.db_path = None
        self.conn = None
        self.cursor = None
        self.current_table = None
        self.tables = {}  # {table_name: [fields]}

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Database label
        self.db_label = QLabel("Database in use: (not selected)")
        self.db_label.setToolTip("Shows the currently selected SQLite database file")
        self.main_layout.addWidget(self.db_label)

        # Database buttons
        db_button_layout = QHBoxLayout()
        self.create_db_button = QPushButton("Create New Database")
        self.create_db_button.setToolTip("Create a new SQLite database file")
        self.create_db_button.clicked.connect(self.create_new_database)
        db_button_layout.addWidget(self.create_db_button)
        self.open_db_button = QPushButton("Open Existing Database")
        self.open_db_button.setToolTip("Open an existing SQLite database file")
        self.open_db_button.clicked.connect(self.open_existing_database)
        db_button_layout.addWidget(self.open_db_button)
        self.help_button = QPushButton("Help")
        self.help_button.setToolTip("View help information for using the application")
        self.help_button.clicked.connect(self.show_help_dialog)
        db_button_layout.addWidget(self.help_button)
        self.main_layout.addLayout(db_button_layout)

        # Table selection
        table_select_layout = QHBoxLayout()
        self.table_label = QLabel("Select Table:")
        self.table_label.setToolTip("Choose an existing table or create a new one")
        table_select_layout.addWidget(self.table_label)
        self.table_combo = QComboBox()
        self.table_combo.setToolTip("List of tables in the database")
        self.table_combo.currentTextChanged.connect(self.switch_table)
        table_select_layout.addWidget(self.table_combo)
        self.new_table_button = QPushButton("New Table")
        self.new_table_button.setToolTip("Create a new table")
        self.new_table_button.clicked.connect(self.add_new_table)
        table_select_layout.addWidget(self.new_table_button)
        self.main_layout.addLayout(table_select_layout)

        # Table name entry
        table_name_layout = QHBoxLayout()
        self.table_name_label = QLabel("Table Name:")
        self.table_name_label.setToolTip("Enter or edit the name of the table")
        table_name_layout.addWidget(self.table_name_label)
        self.table_name_entry = QLineEdit()
        self.table_name_entry.setToolTip("Enter the name of the table (e.g., Staff)")
        self.table_name_entry.textChanged.connect(self.update_sql_display)
        table_name_layout.addWidget(self.table_name_entry)
        self.main_layout.addLayout(table_name_layout)

        # Add/Modify Field frame
        add_field_frame = QFrame()
        add_field_frame.setFrameShape(QFrame.Shape.Box)
        add_field_layout = QVBoxLayout(add_field_frame)
        add_field_layout.addWidget(QLabel("Add/Modify Field"))

        # Field Name Entry
        field_name_layout = QHBoxLayout()
        field_name_layout.addWidget(QLabel("Field Name:"))
        self.field_name_entry = QLineEdit()
        self.field_name_entry.setToolTip("Enter the name of the field (e.g., Staff ID)")
        self.field_name_entry.textChanged.connect(self.update_fk_check_state)
        field_name_layout.addWidget(self.field_name_entry)
        add_field_layout.addLayout(field_name_layout)

        # Type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.setToolTip("Select the data type for the field")
        self.type_combo.addItems(["INTEGER", "TEXT", "REAL", "BLOB", "NUMERIC", "DATE", "BOOLEAN"])
        self.type_combo.currentTextChanged.connect(self.update_add_field_widgets)
        type_layout.addWidget(self.type_combo)
        add_field_layout.addLayout(type_layout)

        # Subtype for TEXT
        self.subtype_frame = QFrame()
        subtype_layout = QHBoxLayout(self.subtype_frame)
        subtype_layout.addWidget(QLabel("Subtype:"))
        self.subtype_combo = QComboBox()
        self.subtype_combo.setToolTip("Select subtype for TEXT fields")
        self.subtype_combo.addItems(["TEXT", "CHAR", "VCHAR", "NCHAR", "NVCHAR"])
        self.subtype_combo.currentTextChanged.connect(self.update_range_entry)
        subtype_layout.addWidget(self.subtype_combo)
        add_field_layout.addWidget(self.subtype_frame)
        self.subtype_frame.setVisible(False)

        # Length entry
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Length:"))
        self.range_entry = QLineEdit()
        self.range_entry.setToolTip("Enter length for CHAR, VCHAR, NCHAR, or NVCHAR (e.g., 40)")
        self.range_entry.setEnabled(False)
        range_layout.addWidget(self.range_entry)
        add_field_layout.addLayout(range_layout)

        # Default and Check constraints
        constraints_layout = QGridLayout()
        constraints_layout.addWidget(QLabel("Default:"), 0, 0)
        self.default_entry = QLineEdit()
        self.default_entry.setToolTip("Enter default value for the field")
        constraints_layout.addWidget(self.default_entry, 0, 1)
        constraints_layout.addWidget(QLabel("Check:"), 1, 0)
        self.check_entry = QLineEdit()
        self.check_entry.setToolTip("Enter a CHECK condition (e.g., age > 18)")
        constraints_layout.addWidget(self.check_entry, 1, 1)
        add_field_layout.addLayout(constraints_layout)

        # Foreign Key frame
        self.fk_frame = QFrame()
        fk_layout = QVBoxLayout(self.fk_frame)
        fk_layout.addWidget(QLabel("Foreign Key"))
        self.fk_check = QCheckBox("FK")
        self.fk_check.setToolTip("Check to define this field as a foreign key")
        self.fk_check.setEnabled(False)  # Disabled by default
        self.fk_check.stateChanged.connect(self.update_fk_widgets)
        fk_layout.addWidget(self.fk_check)
        self.fk_ref_table_combo = QComboBox()
        self.fk_ref_table_combo.setToolTip("Select the table to reference")
        self.fk_ref_table_combo.currentTextChanged.connect(self.update_fk_column_combo)
        fk_layout.addWidget(self.fk_ref_table_combo)
        self.fk_ref_column_combo = QComboBox()
        self.fk_ref_column_combo.setToolTip("Select the primary key column")
        fk_layout.addWidget(self.fk_ref_column_combo)
        self.fk_on_delete_combo = QComboBox()
        self.fk_on_delete_combo.setToolTip("Action when referenced row is deleted")
        self.fk_on_delete_combo.addItems(["NO ACTION", "CASCADE", "SET NULL", "RESTRICT"])
        fk_layout.addWidget(self.fk_on_delete_combo)
        self.fk_on_update_combo = QComboBox()
        self.fk_on_update_combo.setToolTip("Action when referenced column is updated")
        self.fk_on_update_combo.addItems(["NO ACTION", "CASCADE", "SET NULL", "RESTRICT"])
        fk_layout.addWidget(self.fk_on_update_combo)
        add_field_layout.addWidget(self.fk_frame)

        # Checkboxes
        checkbox_layout = QHBoxLayout()
        self.nn_check = QCheckBox("NN")
        self.nn_check.setToolTip("Not Null")
        self.pk_check = QCheckBox("PK")
        self.pk_check.setToolTip("Primary Key")
        self.ai_check = QCheckBox("AI")
        self.ai_check.setToolTip("Auto Increment")
        self.u_check = QCheckBox("U")
        self.u_check.setToolTip("Unique")
        self.ai_check.setEnabled(False)
        self.pk_check.stateChanged.connect(self.update_ai_check)
        self.type_combo.currentTextChanged.connect(self.update_ai_check)
        checkbox_layout.addWidget(self.nn_check)
        checkbox_layout.addWidget(self.pk_check)
        checkbox_layout.addWidget(self.ai_check)
        checkbox_layout.addWidget(self.u_check)
        add_field_layout.addLayout(checkbox_layout)

        # Add/Modify Field buttons
        field_button_layout = QHBoxLayout()
        self.add_field_button = QPushButton("Add Field")
        self.add_field_button.setToolTip("Add a new field")
        self.add_field_button.clicked.connect(self.add_field)
        field_button_layout.addWidget(self.add_field_button)
        self.modify_field_button = QPushButton("Modify Field")
        self.modify_field_button.setToolTip("Modify the selected field")
        self.modify_field_button.clicked.connect(self.modify_field)
        self.modify_field_button.setEnabled(False)
        field_button_layout.addWidget(self.modify_field_button)
        add_field_layout.addLayout(field_button_layout)
        self.main_layout.addWidget(add_field_frame)

        # Fields TreeWidget
        fields_frame = QFrame()
        fields_frame.setFrameShape(QFrame.Shape.Box)
        fields_layout = QVBoxLayout(fields_frame)
        fields_layout.addWidget(QLabel("Fields"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Range", "NN", "PK", "AI", "U", "Default", "Check", "FK"])
        self.tree.itemSelectionChanged.connect(self.update_modify_button_state)
        for i in range(10):
            self.tree.setColumnWidth(i, 80)
        self.tree.setMinimumHeight(167)  # Reduced from 250 to 167 (2/3)
        fields_layout.addWidget(self.tree)
        self.main_layout.addWidget(fields_frame)

        # Manipulation buttons
        manip_layout = QHBoxLayout()
        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Remove the selected field")
        self.remove_button.clicked.connect(self.remove_field)
        self.remove_button.setEnabled(False)
        manip_layout.addWidget(self.remove_button)
        self.move_top_button = QPushButton("Move Top")
        self.move_top_button.setToolTip("Move the selected field to the top")
        self.move_top_button.clicked.connect(self.move_top)
        self.move_top_button.setEnabled(False)
        manip_layout.addWidget(self.move_top_button)
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.setToolTip("Move the selected field up")
        self.move_up_button.clicked.connect(self.move_up)
        self.move_up_button.setEnabled(False)
        manip_layout.addWidget(self.move_up_button)
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.setToolTip("Move the selected field down")
        self.move_down_button.clicked.connect(self.move_down)
        self.move_down_button.setEnabled(False)
        manip_layout.addWidget(self.move_down_button)
        self.move_bottom_button = QPushButton("Move Bottom")
        self.move_bottom_button.setToolTip("Move the selected field to the bottom")
        self.move_bottom_button.clicked.connect(self.move_bottom)
        self.move_bottom_button.setEnabled(False)
        manip_layout.addWidget(self.move_bottom_button)
        fields_layout.addLayout(manip_layout)

        # SQL display
        self.sql_display = QTextEdit()
        self.sql_display.setToolTip("Shows the SQL statement for the current table")
        self.sql_display.setReadOnly(True)
        self.sql_display.setFixedHeight(150)
        self.main_layout.addWidget(self.sql_display)

        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Apply Changes")
        self.ok_button.setToolTip("Apply changes to the database")
        self.ok_button.clicked.connect(self.apply_table_changes)
        button_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setToolTip("Close without saving")
        self.cancel_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(button_layout)

        # Initial update
        self.update_sql_display()
        self.select_database_file()

    def show_help_dialog(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help - Table Creation V5.2")
        help_dialog.setGeometry(300, 300, 400, 300)
        layout = QVBoxLayout(help_dialog)
        help_text = QTextBrowser()
        help_text.setHtml("""
        <h2>Table Creation V5.2 Help</h2>
        <p><b>Creating a Database:</b> Use 'Create New Database' or 'Open Existing Database'.</p>
        <p><b>Creating a Table:</b> Enter a table name, click 'New Table', add fields, and apply changes.</p>
        <p><b>Fields:</b>
        <ul>
            <li><b>Name:</b> Unique field name.</li>
            <li><b>Type:</b> INTEGER, TEXT, etc.</li>
            <li><b>Length:</b> For CHAR, VCHAR, etc.</li>
            <li><b>Constraints:</b> NN (Not Null), PK (Primary Key), AI (Auto Increment), U (Unique), Default, Check, FK (Foreign Key).</li>
        </ul>
        </p>
        <p><b>Foreign Keys:</b> FK checkbox enables when a field matches another table’s primary key field in name and type. Select reference table and column.</p>
        <p><b>Applying Changes:</b> Click 'Apply Changes' to save to the database.</p>
        """)
        layout.addWidget(help_text)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(help_dialog.accept)
        layout.addWidget(ok_button)
        help_dialog.exec()

    def select_database_file(self):
        print("select_database_file: Initialized")
        self.create_db_button.setEnabled(True)
        self.open_db_button.setEnabled(True)

    def create_new_database(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Create New SQLite Database", "", "SQLite Database (*.db);;All Files (*.*)")
        if file_path:
            print(f"create_new_database: Creating {file_path}")
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                if self.conn:
                    self.conn.close()
                self.db_path = file_path
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
                self.cursor.execute("PRAGMA foreign_keys = ON;")
                self.db_label.setText(f"Database in use: {self.db_path}")
                self.tables = {}
                self.current_table = None
                self.table_combo.blockSignals(True)
                self.table_combo.clear()
                self.table_combo.blockSignals(False)
                self.table_name_entry.blockSignals(True)
                self.table_name_entry.clear()
                self.table_name_entry.blockSignals(False)
                self.clear_table_ui()
                self.create_db_button.setEnabled(False)
                self.open_db_button.setEnabled(False)
                print("create_new_database: Success")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")
                self.db_label.setText("Database in use: (not selected)")
                self.conn = None
                self.cursor = None
                print(f"create_new_database: Error - {str(e)}")

    def open_existing_database(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open SQLite Database", "", "SQLite Database (*.db);;All Files (*.*)")
        if file_path:
            print(f"open_existing_database: Opening {file_path}")
            try:
                if self.conn:
                    self.conn.close()
                self.db_path = file_path
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
                self.cursor.execute("PRAGMA foreign_keys = ON;")
                self.db_label.setText(f"Database in use: {self.db_path}")
                self.tables = {}
                self.current_table = None
                self.table_combo.blockSignals(True)
                self.table_combo.clear()
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in self.cursor.fetchall()]
                self.table_combo.addItems(tables)
                self.table_combo.blockSignals(False)
                self.table_name_entry.blockSignals(True)
                self.table_name_entry.clear()
                self.table_name_entry.blockSignals(False)

                for table_name in tables:
                    self.tables[table_name] = []
                    self.cursor.execute(f"PRAGMA table_info('{table_name}');")
                    columns = self.cursor.fetchall()
                    self.cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
                    fk_list = self.cursor.fetchall()
                    self.cursor.execute(f"PRAGMA index_list('{table_name}');")
                    indexes = self.cursor.fetchall()
                    pk_fields = []
                    for col in columns:
                        cid, name, col_type, notnull, default, pk = col
                        range_val = ""
                        display_type = col_type
                        if col_type.startswith(("CHAR", "VCHAR", "NCHAR", "NVCHAR")):
                            if "(" in col_type and ")" in col_type:
                                display_type = col_type[:col_type.index("(")]
                                range_val = col_type[col_type.index("(")+1:col_type.index(")")]
                        elif col_type.upper() in ("DATE", "BOOLEAN"):
                            display_type = col_type.upper()
                            col_type = "TEXT" if col_type.upper() == "DATE" else "INTEGER"
                        field = {
                            "name": name,
                            "type": col_type,
                            "range": range_val,
                            "display_type": display_type,
                            "not_null": bool(notnull),
                            "primary_key": bool(pk),
                            "autoincrement": False,
                            "unique": False,
                            "default": default or "",
                            "check": "",
                            "foreign_key": {"table": "", "column": "", "on_delete": "NO ACTION", "on_update": "NO ACTION"}
                        }
                        if pk:
                            pk_fields.append(field)
                        self.tables[table_name].append(field)
                    self.cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                    create_sql = self.cursor.fetchone()
                    if create_sql:
                        create_sql = create_sql[0].upper()
                        if "AUTOINCREMENT" in create_sql:
                            for field in pk_fields:
                                if field["type"].startswith("INTEGER"):
                                    field["autoincrement"] = True
                        if "CHECK" in create_sql:
                            check_start = create_sql.find("CHECK")
                            check_end = create_sql.find(")", check_start)
                            check_expr = create_sql[check_start+6:check_end]
                            for field in self.tables[table_name]:
                                if field["name"] in check_expr:
                                    field["check"] = check_expr
                    for idx in indexes:
                        idx_name = idx[1]
                        is_unique = idx[2]
                        if is_unique:
                            self.cursor.execute(f"PRAGMA index_info('{idx_name}');")
                            idx_cols = self.cursor.fetchall()
                            for idx_col in idx_cols:
                                cid = idx_col[2]
                                for col in columns:
                                    if col[0] == cid:
                                        col_name = col[1]
                                        for field in self.tables[table_name]:
                                            if field["name"] == col_name:
                                                field["unique"] = True
                                                break
                                        break
                    for fk in fk_list:
                        col_name = fk[3]
                        ref_table = fk[2]
                        ref_column = fk[4]
                        on_delete = fk[5] or "NO ACTION"
                        on_update = fk[6] or "NO ACTION"
                        for field in self.tables[table_name]:
                            if field["name"] == col_name:
                                field["foreign_key"] = {
                                    "table": ref_table,
                                    "column": ref_column,
                                    "on_delete": on_delete,
                                    "on_update": on_update
                                }
                                break
                self.clear_table_ui()
                if tables:
                    self.table_combo.setCurrentText(tables[0])
                    self.switch_table(tables[0])
                self.create_db_button.setEnabled(False)
                self.open_db_button.setEnabled(False)
                print("open_existing_database: Success")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open database: {str(e)}")
                self.db_label.setText("Database in use: (not selected)")
                self.conn = None
                self.cursor = None
                print(f"open_existing_database: Error - {str(e)}")

    def add_new_table(self):
        table_name = self.table_name_entry.text().strip()
        if not table_name:
            QMessageBox.critical(self, "Error", "Table name cannot be empty")
            print("add_new_table: Error - Empty name")
            return
        if table_name in self.tables or table_name in [self.table_combo.itemText(i) for i in range(self.table_combo.count())]:
            QMessageBox.critical(self, "Error", "Table name already exists")
            print("add_new_table: Error - Name exists")
            return
        print(f"add_new_table: Adding {table_name}")
        try:
            self.tables[table_name] = []
            self.current_table = table_name
            self.table_combo.blockSignals(True)
            self.table_combo.addItem(table_name)
            self.table_combo.setCurrentText(table_name)
            self.table_combo.blockSignals(False)
            self.clear_table_ui()
            self.update_sql_display()
            self.update_fk_check_state()
            print("add_new_table: Success")
        except Exception as e:
            print(f"add_new_table: Error - {str(e)}")
            raise

    def switch_table(self, table_name):
        if not table_name:
            return
        print(f"switch_table: Switching to {table_name}")
        try:
            self.current_table = table_name
            self.table_name_entry.blockSignals(True)
            self.table_name_entry.setText(table_name)
            self.table_name_entry.blockSignals(False)
            self.tree.blockSignals(True)
            self.tree.clear()
            for field in self.tables.get(table_name, []):
                fk_info = ""
                if field["foreign_key"]["table"]:
                    fk_info = f"{field['foreign_key']['table']}({field['foreign_key']['column']}) ON DELETE {field['foreign_key']['on_delete']}"
                item = QTreeWidgetItem([
                    field["name"],
                    field["display_type"],
                    field["range"],
                    "✓" if field["not_null"] else "",
                    "✓" if field["primary_key"] else "",
                    "✓" if field["autoincrement"] else "",
                    "✓" if field["unique"] else "",
                    field["default"],
                    field["check"],
                    fk_info
                ])
                self.tree.addTopLevelItem(item)
            self.tree.blockSignals(False)
            self.update_sql_display()
            self.update_button_states()
            self.update_fk_check_state()
            print("switch_table: Completed")
        except Exception as e:
            print(f"switch_table: Error - {str(e)}")
            raise

    def clear_table_ui(self):
        print("clear_table_ui: Clearing")
        try:
            self.tree.blockSignals(True)
            self.tree.clear()
            self.tree.blockSignals(False)
            self.field_name_entry.clear()
            self.type_combo.blockSignals(True)
            self.type_combo.setCurrentText("INTEGER")
            self.type_combo.blockSignals(False)
            self.subtype_combo.blockSignals(True)
            self.subtype_combo.setCurrentText("TEXT")
            self.subtype_combo.blockSignals(False)
            self.range_entry.clear()
            self.range_entry.setEnabled(False)
            self.default_entry.clear()
            self.check_entry.clear()
            self.nn_check.blockSignals(True)
            self.nn_check.setChecked(False)
            self.nn_check.blockSignals(False)
            self.pk_check.blockSignals(True)
            self.pk_check.setChecked(False)
            self.pk_check.blockSignals(False)
            self.ai_check.blockSignals(True)
            self.ai_check.setChecked(False)
            self.ai_check.setEnabled(False)
            self.ai_check.blockSignals(False)
            self.u_check.blockSignals(True)
            self.u_check.setChecked(False)
            self.u_check.blockSignals(False)
            self.fk_check.blockSignals(True)
            self.fk_check.setChecked(False)
            self.fk_check.setEnabled(False)
            self.fk_check.blockSignals(False)
            self.fk_frame.setVisible(True)  # Always visible
            self.update_button_states()
            print("clear_table_ui: Completed")
        except Exception as e:
            print(f"clear_table_ui: Error - {str(e)}")
            raise

    def update_add_field_widgets(self):
        print("update_add_field_widgets: Starting")
        try:
            if self.type_combo.currentText() == "TEXT":
                self.subtype_frame.show()
                self.update_range_entry()
            else:
                self.subtype_frame.hide()
                self.range_entry.setEnabled(False)
                self.range_entry.clear()
            self.update_fk_check_state()
            print("update_add_field_widgets: Completed")
        except Exception as e:
            print(f"update_add_field_widgets: Error - {str(e)}")
            raise

    def update_range_entry(self):
        print("update_range_entry: Starting")
        try:
            if (self.type_combo.currentText() == "TEXT" and
                    self.subtype_combo.currentText() in ["CHAR", "VCHAR", "NCHAR", "NVCHAR"]):
                self.range_entry.setEnabled(True)
            else:
                self.range_entry.setEnabled(False)
                self.range_entry.clear()
            print("update_range_entry: Completed")
        except Exception as e:
            print(f"update_range_entry: Error - {str(e)}")
            raise

    def update_ai_check(self):
        print("update_ai_check: Starting")
        try:
            if self.type_combo.currentText() == "INTEGER" and self.pk_check.isChecked():
                self.ai_check.setEnabled(True)
            else:
                self.ai_check.setEnabled(False)
                self.ai_check.setChecked(False)
            print("update_ai_check: Completed")
        except Exception as e:
            print(f"update_ai_check: Error - {str(e)}")
            raise

    def update_fk_widgets(self):
        print("update_fk_widgets: Starting")
        try:
            if self.fk_check.isChecked():
                self.fk_ref_table_combo.setEnabled(True)
                self.fk_ref_column_combo.setEnabled(True)
                self.fk_on_delete_combo.setEnabled(True)
                self.fk_on_update_combo.setEnabled(True)
                self.update_fk_ref_table_combo()
            else:
                self.fk_ref_table_combo.setEnabled(False)
                self.fk_ref_column_combo.setEnabled(False)
                self.fk_on_delete_combo.setEnabled(False)
                self.fk_on_update_combo.setEnabled(False)
                self.fk_ref_table_combo.clear()
                self.fk_ref_column_combo.clear()
            print("update_fk_widgets: Completed")
        except Exception as e:
            print(f"update_fk_widgets: Error - {str(e)}")
            raise

    def update_fk_check_state(self):
        print("update_fk_check_state: Starting")
        try:
            field_name = self.field_name_entry.text().strip()
            field_type = self.get_current_field_type()
            can_be_fk = False
            if field_name and field_type:
                for table in self.tables:
                    if table != self.current_table:
                        pk_fields = [f for f in self.tables[table] if f["primary_key"]]
                        if len(pk_fields) == 1:  # Single-column PK
                            pk_field = pk_fields[0]
                            if pk_field["name"] == field_name and pk_field["type"] == field_type:
                                can_be_fk = True
                                break
            self.fk_check.setEnabled(can_be_fk)
            if not can_be_fk:
                self.fk_check.setChecked(False)
                self.fk_ref_table_combo.clear()
                self.fk_ref_column_combo.clear()
            print(f"update_fk_check_state: FK enabled={can_be_fk}")
        except Exception as e:
            print(f"update_fk_check_state: Error - {str(e)}")
            raise

    def get_current_field_type(self):
        main_type = self.type_combo.currentText()
        if main_type == "TEXT":
            subtype = self.subtype_combo.currentText()
            range_val = self.range_entry.text().strip() if self.range_entry.isEnabled() else ""
            if subtype in ["CHAR", "VCHAR", "NCHAR", "NVCHAR"] and range_val:
                return f"{subtype}({range_val})"
            return subtype
        elif main_type == "DATE":
            return "TEXT"
        elif main_type == "BOOLEAN":
            return "INTEGER"
        return main_type

    def update_fk_ref_table_combo(self):
        print("update_fk_ref_table_combo: Starting")
        try:
            self.fk_ref_table_combo.blockSignals(True)
            self.fk_ref_table_combo.clear()
            field_name = self.field_name_entry.text().strip()
            field_type = self.get_current_field_type()
            for table in self.tables:
                if table != self.current_table:
                    pk_fields = [f for f in self.tables[table] if f["primary_key"]]
                    if len(pk_fields) == 1:
                        pk_field = pk_fields[0]
                        if pk_field["name"] == field_name and pk_field["type"] == field_type:
                            self.fk_ref_table_combo.addItem(table)
            self.fk_ref_table_combo.blockSignals(False)
            self.update_fk_column_combo()
            print("update_fk_ref_table_combo: Completed")
        except Exception as e:
            print(f"update_fk_ref_table_combo: Error - {str(e)}")
            raise

    def update_fk_column_combo(self):
        print("update_fk_column_combo: Starting")
        try:
            self.fk_ref_column_combo.blockSignals(True)
            self.fk_ref_column_combo.clear()
            ref_table = self.fk_ref_table_combo.currentText()
            if ref_table and ref_table in self.tables:
                pk_fields = [f for f in self.tables[ref_table] if f["primary_key"]]
                columns = [f["name"] for f in pk_fields]
                self.fk_ref_column_combo.addItems(columns)
            self.fk_ref_column_combo.blockSignals(False)
            print("update_fk_column_combo: Completed")
        except Exception as e:
            print(f"update_fk_column_combo: Error - {str(e)}")
            raise

    def add_field(self):
        print("add_field: Starting")
        try:
            if not self.current_table:
                QMessageBox.critical(self, "Error", "No table selected")
                print("add_field: Error - No table")
                return
            name = self.field_name_entry.text().strip()
            if not name:
                QMessageBox.critical(self, "Error", "Field name cannot be empty")
                print("add_field: Error - Empty name")
                return
            main_type = self.type_combo.currentText()
            range_val = self.range_entry.text().strip() if self.range_entry.isEnabled() else ""
            default_val = self.default_entry.text().strip()
            check_val = self.check_entry.text().strip()

            if main_type == "TEXT":
                subtype = self.subtype_combo.currentText()
                if subtype in ["CHAR", "VCHAR", "NCHAR", "NVCHAR"] and range_val:
                    field_type = f"{subtype}({range_val})"
                    display_type = subtype
                else:
                    field_type = subtype
                    display_type = subtype
            elif main_type == "DATE":
                field_type = "TEXT"
                display_type = "DATE"
            elif main_type == "BOOLEAN":
                field_type = "INTEGER"
                display_type = "BOOLEAN"
            else:
                field_type = main_type
                display_type = main_type

            fk_info = ""
            fk_data = {"table": "", "column": "", "on_delete": "NO ACTION", "on_update": "NO ACTION"}
            if self.fk_check.isChecked():
                ref_table = self.fk_ref_table_combo.currentText().strip()
                ref_column = self.fk_ref_column_combo.currentText().strip()
                if not ref_table or not ref_column:
                    QMessageBox.critical(self, "Error", "Select reference table and column")
                    print("add_field: Error - Invalid FK")
                    return
                fk_data = {
                    "table": ref_table,
                    "column": ref_column,
                    "on_delete": self.fk_on_delete_combo.currentText(),
                    "on_update": self.fk_on_update_combo.currentText()
                }
                fk_info = f"{ref_table}({ref_column}) ON DELETE {fk_data['on_delete']}"

            item = QTreeWidgetItem([
                name, display_type, range_val,
                "✓" if self.nn_check.isChecked() else "",
                "✓" if self.pk_check.isChecked() else "",
                "✓" if self.ai_check.isChecked() else "",
                "✓" if self.u_check.isChecked() else "",
                default_val, check_val, fk_info
            ])
            self.tree.blockSignals(True)
            self.tree.addTopLevelItem(item)
            self.tree.blockSignals(False)

            if self.current_table not in self.tables:
                self.tables[self.current_table] = []
            self.tables[self.current_table].append({
                "name": name, "type": field_type, "range": range_val, "display_type": display_type,
                "not_null": self.nn_check.isChecked(), "primary_key": self.pk_check.isChecked(),
                "autoincrement": self.ai_check.isChecked(), "unique": self.u_check.isChecked(),
                "default": default_val, "check": check_val, "foreign_key": fk_data
            })

            self.clear_field_input()
            self.update_sql_display()
            self.update_button_states()
            print("add_field: Success")
        except Exception as e:
            print(f"add_field: Error - {str(e)}")
            raise

    def modify_field(self):
        print("modify_field: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if not selected_items or not self.current_table:
                QMessageBox.critical(self, "Error", "No field selected")
                print("modify_field: Error - No field")
                return
            index = self.tree.indexOfTopLevelItem(selected_items[0])
            name = self.field_name_entry.text().strip()
            if not name:
                QMessageBox.critical(self, "Error", "Field name cannot be empty")
                print("modify_field: Error - Empty name")
                return
            main_type = self.type_combo.currentText()
            range_val = self.range_entry.text().strip() if self.range_entry.isEnabled() else ""
            default_val = self.default_entry.text().strip()
            check_val = self.check_entry.text().strip()

            if main_type == "TEXT":
                subtype = self.subtype_combo.currentText()
                if subtype in ["CHAR", "VCHAR", "NCHAR", "NVCHAR"] and range_val:
                    field_type = f"{subtype}({range_val})"
                    display_type = subtype
                else:
                    field_type = subtype
                    display_type = subtype
            elif main_type == "DATE":
                field_type = "TEXT"
                display_type = "DATE"
            elif main_type == "BOOLEAN":
                field_type = "INTEGER"
                display_type = "BOOLEAN"
            else:
                field_type = main_type
                display_type = main_type

            fk_info = ""
            fk_data = {"table": "", "column": "", "on_delete": "NO ACTION", "on_update": "NO ACTION"}
            if self.fk_check.isChecked():
                ref_table = self.fk_ref_table_combo.currentText().strip()
                ref_column = self.fk_ref_column_combo.currentText().strip()
                if not ref_table or not ref_column:
                    QMessageBox.critical(self, "Error", "Select reference table and column")
                    print("modify_field: Error - Invalid FK")
                    return
                fk_data = {
                    "table": ref_table,
                    "column": ref_column,
                    "on_delete": self.fk_on_delete_combo.currentText(),
                    "on_update": self.fk_on_update_combo.currentText()
                }
                fk_info = f"{ref_table}({ref_column}) ON DELETE {fk_data['on_delete']}"

            self.tables[self.current_table][index] = {
                "name": name,
                "type": field_type,
                "range": range_val,
                "display_type": display_type,
                "not_null": self.nn_check.isChecked(),
                "primary_key": self.pk_check.isChecked(),
                "autoincrement": self.ai_check.isChecked(),
                "unique": self.u_check.isChecked(),
                "default": default_val,
                "check": check_val,
                "foreign_key": fk_data
            }

            item = QTreeWidgetItem([
                name,
                display_type,
                range_val,
                "✓" if self.nn_check.isChecked() else "",
                "✓" if self.pk_check.isChecked() else "",
                "✓" if self.ai_check.isChecked() else "",
                "✓" if self.u_check.isChecked() else "",
                default_val,
                check_val,
                fk_info
            ])
            self.tree.blockSignals(True)
            self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(index, item)
            self.tree.setCurrentItem(item)
            self.tree.blockSignals(False)

            self.clear_field_input()
            self.update_sql_display()
            self.update_button_states()
            print("modify_field: Success")
        except Exception as e:
            print(f"modify_field: Error - {str(e)}")
            raise

    def clear_field_input(self):
        print("clear_field_input: Starting")
        try:
            self.field_name_entry.clear()
            self.type_combo.blockSignals(True)
            self.type_combo.setCurrentText("INTEGER")
            self.type_combo.blockSignals(False)
            self.subtype_combo.blockSignals(True)
            self.subtype_combo.setCurrentText("TEXT")
            self.subtype_combo.blockSignals(False)
            self.range_entry.clear()
            self.range_entry.setEnabled(False)
            self.default_entry.clear()
            self.check_entry.clear()
            self.nn_check.blockSignals(True)
            self.nn_check.setChecked(False)
            self.nn_check.blockSignals(False)
            self.pk_check.blockSignals(True)
            self.pk_check.setChecked(False)
            self.pk_check.blockSignals(False)
            self.ai_check.blockSignals(True)
            self.ai_check.setChecked(False)
            self.ai_check.setEnabled(False)
            self.ai_check.blockSignals(False)
            self.u_check.blockSignals(True)
            self.u_check.setChecked(False)
            self.u_check.blockSignals(False)
            self.fk_check.blockSignals(True)
            self.fk_check.setChecked(False)
            self.fk_check.setEnabled(False)
            self.fk_check.blockSignals(False)
            self.fk_ref_table_combo.clear()
            self.fk_ref_column_combo.clear()
            print("clear_field_input: Completed")
        except Exception as e:
            print(f"clear_field_input: Error - {str(e)}")
            raise

    def remove_field(self):
        print("remove_field: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if not selected_items or not self.current_table:
                QMessageBox.critical(self, "Error", "No field selected")
                print("remove_field: Error - No field")
                return
            index = self.tree.indexOfTopLevelItem(selected_items[0])
            self.tree.blockSignals(True)
            self.tree.takeTopLevelItem(index)
            self.tree.blockSignals(False)
            self.tables[self.current_table].pop(index)
            self.update_sql_display()
            self.update_button_states()
            print("remove_field: Success")
        except Exception as e:
            print(f"remove_field: Error - {str(e)}")
            raise

    def move_top(self):
        print("move_top: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if selected_items and self.current_table:
                index = self.tree.indexOfTopLevelItem(selected_items[0])
                if index != 0:
                    self.tree.blockSignals(True)
                    item = self.tree.takeTopLevelItem(index)
                    self.tree.insertTopLevelItem(0, item)
                    self.tree.setCurrentItem(item)
                    self.tree.blockSignals(False)
                    self.tables[self.current_table].insert(0, self.tables[self.current_table].pop(index))
                    self.update_sql_display()
            print("move_top: Success")
        except Exception as e:
            print(f"move_top: Error - {str(e)}")
            raise

    def move_up(self):
        print("move_up: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if selected_items and self.current_table:
                index = self.tree.indexOfTopLevelItem(selected_items[0])
                if index > 0:
                    self.tree.blockSignals(True)
                    item = self.tree.takeTopLevelItem(index)
                    self.tree.insertTopLevelItem(index - 1, item)
                    self.tree.setCurrentItem(item)
                    self.tree.blockSignals(False)
                    self.tables[self.current_table].insert(index - 1, self.tables[self.current_table].pop(index))
                    self.update_sql_display()
            print("move_up: Success")
        except Exception as e:
            print(f"move_up: Error - {str(e)}")
            raise

    def move_down(self):
        print("move_down: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if selected_items and self.current_table:
                index = self.tree.indexOfTopLevelItem(selected_items[0])
                if index < self.tree.topLevelItemCount() - 1:
                    self.tree.blockSignals(True)
                    item = self.tree.takeTopLevelItem(index)
                    self.tree.insertTopLevelItem(index + 1, item)
                    self.tree.setCurrentItem(item)
                    self.tree.blockSignals(False)
                    self.tables[self.current_table].insert(index + 1, self.tables[self.current_table].pop(index))
                    self.update_sql_display()
            print("move_down: Success")
        except Exception as e:
            print(f"move_down: Error - {str(e)}")
            raise

    def move_bottom(self):
        print("move_bottom: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if selected_items and self.current_table:
                index = self.tree.indexOfTopLevelItem(selected_items[0])
                if index < self.tree.topLevelItemCount() - 1:
                    self.tree.blockSignals(True)
                    item = self.tree.takeTopLevelItem(index)
                    self.tree.addTopLevelItem(item)
                    self.tree.setCurrentItem(item)
                    self.tree.blockSignals(False)
                    self.tables[self.current_table].append(self.tables[self.current_table].pop(index))
                    self.update_sql_display()
            print("move_bottom: Success")
        except Exception as e:
            print(f"move_bottom: Error - {str(e)}")
            raise

    def update_button_states(self):
        print("update_button_states: Starting")
        try:
            state = bool(self.current_table and self.tree.topLevelItemCount() > 0)
            self.remove_button.setEnabled(state)
            self.move_top_button.setEnabled(state)
            self.move_up_button.setEnabled(state)
            self.move_down_button.setEnabled(state)
            self.move_bottom_button.setEnabled(state)
            self.update_modify_button_state()
            print("update_button_states: Completed")
        except Exception as e:
            print(f"update_button_states: Error - {str(e)}")
            raise

    def update_modify_button_state(self):
        print("update_modify_button_state: Starting")
        try:
            state = bool(self.current_table and self.tree.selectedItems())
            self.modify_field_button.setEnabled(state)
            print("update_modify_button_state: Completed")
        except Exception as e:
            print(f"update_modify_button_state: Error - {str(e)}")
            raise

    def update_sql_display(self):
        print("update_sql_display: Starting")
        try:
            table_name = self.table_name_entry.text().strip() or ""
            sql = f'CREATE TABLE "{table_name}" (\n'
            fields = self.tables.get(self.current_table, [])
            pk_fields = [field for field in fields if field["primary_key"]]
            fk_fields = [field for field in fields if field["foreign_key"]["table"]]

            column_defs = []
            for field in fields:
                col_def = f'    "{field["name"]}" {field["type"]}'
                if field["not_null"] and not field["primary_key"]:
                    col_def += " NOT NULL"
                if field["unique"] and not field["primary_key"]:
                    col_def += " UNIQUE"
                if field["default"]:
                    col_def += f" DEFAULT '{field['default']}'"
                if field["check"]:
                    col_def += f" CHECK({field['check']})"
                column_defs.append(col_def)

            if pk_fields:
                if len(pk_fields) == 1:
                    pk_field = pk_fields[0]
                    pk_name = pk_field["name"]
                    if pk_field["autoincrement"] and field["type"].startswith("INTEGER"):
                        pk_clause = f'    PRIMARY KEY("{pk_name}" AUTOINCREMENT)'
                    else:
                        pk_clause = f'    PRIMARY KEY("{pk_name}")'
                else:
                    pk_names = ", ".join(f'"{field["name"]}"' for field in pk_fields)
                    pk_clause = f"    PRIMARY KEY({pk_names})"
                column_defs.append(pk_clause)

            for fk_field in fk_fields:
                fk = fk_field["foreign_key"]
                fk_clause = f'    FOREIGN KEY("{fk_field["name"]}") REFERENCES "{fk["table"]}"("{fk["column"]}")'
                if fk["on_delete"] != "NO ACTION":
                    fk_clause += f" ON DELETE {fk['on_delete']}"
                if fk["on_update"] != "NO ACTION":
                    fk_clause += f" ON UPDATE {fk['on_update']}"
                column_defs.append(fk_clause)

            sql += ",\n".join(column_defs)
            sql += "\n);"
            self.sql_display.setText(sql)
            print("update_sql_display: Completed")
        except Exception as e:
            print(f"update_sql_display: Error - {str(e)}")
            raise

    def apply_table_changes(self):
        print("apply_table_changes: Starting")
        try:
            if not self.current_table or not self.tables.get(self.current_table):
                QMessageBox.critical(self, "Error", "Cannot save empty table")
                print("apply_table_changes: Error - Empty table")
                return
            if not self.conn:
                QMessageBox.critical(self, "Error", "No database selected")
                print("apply_table_changes: Error - No database")
                return

            table_name = self.current_table
            fields = self.tables[table_name]
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            table_exists = self.cursor.fetchone() is not None

            if not table_exists:
                sql = self.generate_sql()
                self.cursor.execute(sql)
                self.conn.commit()
                QMessageBox.information(self, "Success", f"Table '{table_name}' created!")
            else:
                new_sql = self.generate_sql()
                temp_table = f"temp_{table_name}"
                temp_sql = new_sql.replace(f'CREATE TABLE "{table_name}"', f'CREATE TABLE "{temp_table}"')
                self.cursor.execute(temp_sql)
                old_cols = []
                self.cursor.execute(f"PRAGMA table_info('{table_name}');")
                for col in self.cursor.fetchall():
                    old_cols.append(col[1])
                new_cols = [f["name"] for f in fields]
                common_cols = [col for col in old_cols if col in new_cols]
                if common_cols:
                    cols_str = ", ".join(f'"{col}"' for col in common_cols)
                    self.cursor.execute(f'INSERT INTO "{temp_table}" ({cols_str}) SELECT {cols_str} FROM "{table_name}";')
                self.cursor.execute(f'DROP TABLE "{table_name}";')
                self.cursor.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table_name}";')
                self.conn.commit()
                QMessageBox.information(self, "Success", f"Table '{table_name}' modified!")

            if table_name not in [self.table_combo.itemText(i) for i in range(self.table_combo.count())]:
                self.table_combo.blockSignals(True)
                self.table_combo.addItem(table_name)
                self.table_combo.setCurrentText(table_name)
                self.table_combo.blockSignals(False)
            self.update_fk_check_state()
            print("apply_table_changes: Success")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply changes: {str(e)}")
            print(f"apply_table_changes: Error - {str(e)}")
            raise

    def generate_sql(self):
        table_name = self.table_name_entry.text().strip() or self.current_table
        sql = f'CREATE TABLE "{table_name}" (\n'
        fields = self.tables.get(self.current_table, [])
        pk_fields = [field for field in fields if field["primary_key"]]
        fk_fields = [field for field in fields if field["foreign_key"]["table"]]

        column_defs = []
        for field in fields:
            col_def = f'    "{field["name"]}" {field["type"]}'
            if field["not_null"] and not field["primary_key"]:
                col_def += " NOT NULL"
            if field["unique"] and not field["primary_key"]:
                col_def += " UNIQUE"
            if field["default"]:
                col_def += f" DEFAULT '{field['default']}'"
            if field["check"]:
                col_def += f" CHECK({field['check']})"
            column_defs.append(col_def)

        if pk_fields:
            if len(pk_fields) == 1:
                pk_field = pk_fields[0]
                pk_name = pk_field["name"]
                if pk_field["autoincrement"] and pk_field["type"].startswith("INTEGER"):
                    pk_clause = f'    PRIMARY KEY("{pk_name}" AUTOINCREMENT)'
                else:
                    pk_clause = f'    PRIMARY KEY("{pk_name}")'
            else:
                pk_names = ", ".join(f'"{field["name"]}"' for field in pk_fields)
                pk_clause = f"    PRIMARY KEY({pk_names})"
            column_defs.append(pk_clause)

        for fk_field in fk_fields:
            fk = fk_field["foreign_key"]
            fk_clause = f'    FOREIGN KEY("{fk_field["name"]}") REFERENCES "{fk["table"]}"("{fk["column"]}")'
            if fk["on_delete"] != "NO ACTION":
                fk_clause += f" ON DELETE {fk['on_delete']}"
            if fk["on_update"] != "NO ACTION":
                fk_clause += f" ON UPDATE {fk['on_update']}"
            column_defs.append(fk_clause)

        sql += ",\n".join(column_defs)
        sql += "\n);"
        return sql

    def close_app(self):
        print("close_app: Starting")
        try:
            if self.conn:
                self.conn.close()
            self.close()
            print("close_app: Completed")
        except Exception as e:
            print(f"close_app: Error - {str(e)}")
            raise

if __name__ == "__main__":
    print("main: Starting")
    try:
        app = QApplication(sys.argv)
        window = TableCreatorApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"main: Error - {str(e)}")
        raise