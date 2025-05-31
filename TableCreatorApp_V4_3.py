import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QPushButton, QCheckBox, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QFrame, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
import sqlite3
import os


class TableCreatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Creation V4.3 - PyQt6")
        self.setGeometry(100, 100, 800, 600)

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
        self.main_layout.addWidget(self.db_label)

        # Database buttons
        db_button_layout = QHBoxLayout()
        self.create_db_button = QPushButton("Create New Database")
        self.create_db_button.clicked.connect(self.create_new_database)
        db_button_layout.addWidget(self.create_db_button)
        self.open_db_button = QPushButton("Open Existing Database")
        self.open_db_button.clicked.connect(self.open_existing_database)
        db_button_layout.addWidget(self.open_db_button)
        self.main_layout.addLayout(db_button_layout)

        # Table selection
        table_select_layout = QHBoxLayout()
        self.table_label = QLabel("Select Table:")
        table_select_layout.addWidget(self.table_label)
        self.table_combo = QComboBox()
        self.table_combo.currentTextChanged.connect(self.switch_table)
        table_select_layout.addWidget(self.table_combo)
        self.new_table_button = QPushButton("New Table")
        self.new_table_button.clicked.connect(self.add_new_table)
        table_select_layout.addWidget(self.new_table_button)
        self.main_layout.addLayout(table_select_layout)

        # Table name entry
        table_name_layout = QHBoxLayout()
        self.table_name_label = QLabel("Table Name:")
        table_name_layout.addWidget(self.table_name_label)
        self.table_name_entry = QLineEdit()
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
        field_name_layout.addWidget(self.field_name_entry)
        add_field_layout.addLayout(field_name_layout)

        # Type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["INTEGER", "TEXT", "REAL", "BLOB", "NUMERIC"])
        self.type_combo.currentTextChanged.connect(self.update_add_field_widgets)
        type_layout.addWidget(self.type_combo)
        add_field_layout.addLayout(type_layout)

        # Subtype for TEXT
        self.subtype_frame = QFrame()
        subtype_layout = QHBoxLayout(self.subtype_frame)
        subtype_layout.addWidget(QLabel("Subtype:"))
        self.subtype_combo = QComboBox()
        self.subtype_combo.addItems(["TEXT", "CHAR", "VCHAR", "NCHAR", "NVCHAR"])
        self.subtype_combo.currentTextChanged.connect(self.update_range_entry)
        subtype_layout.addWidget(self.subtype_combo)
        add_field_layout.addWidget(self.subtype_frame)
        self.subtype_frame.setVisible(False)

        # Length entry
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Length:"))
        self.range_entry = QLineEdit()
        self.range_entry.setEnabled(False)
        range_layout.addWidget(self.range_entry)
        add_field_layout.addLayout(range_layout)

        # Checkboxes
        checkbox_layout = QHBoxLayout()
        self.nn_check = QCheckBox("NN")  # Corrected label from "Database" to "NN"
        self.pk_check = QCheckBox("PK")
        self.ai_check = QCheckBox("AI")
        self.u_check = QCheckBox("U")
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
        self.add_field_button.clicked.connect(self.add_field)
        field_button_layout.addWidget(self.add_field_button)
        self.modify_field_button = QPushButton("Modify Field")
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
        self.tree.setHeaderLabels(["Name", "Type", "Range", "NN", "PK", "AI", "U"])
        self.tree.itemSelectionChanged.connect(self.update_modify_button_state)
        for i in range(7):
            self.tree.setColumnWidth(i, 80)
        self.tree.setMinimumHeight(250)  # Set height for ~10 rows
        fields_layout.addWidget(self.tree)
        self.main_layout.addWidget(fields_frame)

        # Manipulation buttons
        manip_layout = QHBoxLayout()
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_field)
        self.remove_button.setEnabled(False)
        manip_layout.addWidget(self.remove_button)
        self.move_top_button = QPushButton("Move Top")
        self.move_top_button.clicked.connect(self.move_top)
        self.move_top_button.setEnabled(False)
        manip_layout.addWidget(self.move_top_button)
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(self.move_up)
        self.move_up_button.setEnabled(False)
        manip_layout.addWidget(self.move_up_button)
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(self.move_down)
        self.move_down_button.setEnabled(False)
        manip_layout.addWidget(self.move_down_button)
        self.move_bottom_button = QPushButton("Move Bottom")
        self.move_bottom_button.clicked.connect(self.move_bottom)
        self.move_bottom_button.setEnabled(False)
        manip_layout.addWidget(self.move_bottom_button)
        fields_layout.addLayout(manip_layout)

        # SQL display
        self.sql_display = QTextEdit()
        self.sql_display.setReadOnly(True)
        self.sql_display.setFixedHeight(150)
        self.main_layout.addWidget(self.sql_display)

        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Apply Changes")
        self.ok_button.clicked.connect(self.apply_table_changes)
        button_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(button_layout)

        # Initial update
        self.update_sql_display()
        self.select_database_file()

    def select_database_file(self):
        """Prompt user to select or create a database file at startup."""
        print("select_database_file: Initialized database selection")
        self.create_db_button.setEnabled(True)
        self.open_db_button.setEnabled(True)

    def create_new_database(self):
        """Create a new SQLite database file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Create New SQLite Database", "", "SQLite Database (*.db);;All Files (*.*)"
        )
        if file_path:
            print(f"create_new_database: Creating database at {file_path}")
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                if self.conn:
                    self.conn.close()
                self.db_path = file_path
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
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
                print("create_new_database: Database created successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}")
                self.db_label.setText("Database in use: (not selected)")
                self.conn = None
                self.cursor = None
                print(f"create_new_database: Error - {str(e)}")

    def open_existing_database(self):
        """Open an existing SQLite database file and load table schemas."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open SQLite Database", "", "SQLite Database (*.db);;All Files (*.*)"
        )
        if file_path:
            print(f"open_existing_database: Opening database at {file_path}")
            try:
                if self.conn:
                    self.conn.close()
                self.db_path = file_path
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
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

                # Load schema for each table
                for table_name in tables:
                    self.tables[table_name] = []
                    self.cursor.execute(f"PRAGMA table_info('{table_name}');")
                    columns = self.cursor.fetchall()
                    self.cursor.execute(f"PRAGMA index_list('{table_name}');")
                    indexes = self.cursor.fetchall()
                    pk_fields = []
                    for col in columns:
                        cid, name, col_type, notnull, default, pk = col
                        # Parse type and length
                        range_val = ""
                        display_type = col_type
                        if col_type.startswith(("CHAR", "VCHAR", "NCHAR", "NVCHAR")):
                            if "(" in col_type and ")" in col_type:
                                display_type = col_type[:col_type.index("(")]
                                range_val = col_type[col_type.index("(")+1:col_type.index(")")]
                        field = {
                            "name": name,
                            "type": col_type,
                            "range": range_val,
                            "display_type": display_type,
                            "not_null": bool(notnull),
                            "primary_key": bool(pk),
                            "autoincrement": False,  # Detect below
                            "unique": False  # Detect below
                        }
                        if pk:
                            pk_fields.append(field)
                        self.tables[table_name].append(field)
                    # Check for AUTOINCREMENT
                    self.cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                    create_sql = self.cursor.fetchone()
                    if create_sql and "AUTOINCREMENT" in create_sql[0].upper():
                        for field in pk_fields:
                            if field["type"].startswith("INTEGER"):
                                field["autoincrement"] = True
                    # Check for UNIQUE constraints
                    for idx in indexes:
                        idx_name = idx[1]  # Index name
                        is_unique = idx[2]  # Unique flag
                        if is_unique:
                            self.cursor.execute(f"PRAGMA index_info('{idx_name}');")
                            idx_cols = self.cursor.fetchall()
                            for idx_col in idx_cols:
                                cid = idx_col[2]  # Column ID
                                # Find column name by cid
                                for col in columns:
                                    if col[0] == cid:  # Match cid
                                        col_name = col[1]
                                        for field in self.tables[table_name]:
                                            if field["name"] == col_name:
                                                field["unique"] = True
                                                break
                                        break
                self.clear_table_ui()
                # Select first table if available
                if tables:
                    self.table_combo.setCurrentText(tables[0])
                    self.switch_table(tables[0])
                self.create_db_button.setEnabled(False)
                self.open_db_button.setEnabled(False)
                print("open_existing_database: Database opened successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open database: {str(e)}")
                self.db_label.setText("Database in use: (not selected)")
                self.conn = None
                self.cursor = None
                print(f"open_existing_database: Error - {str(e)}")

    def add_new_table(self):
        """Add a new table to the combo box and initialize its fields."""
        table_name = self.table_name_entry.text().strip()
        if not table_name:
            QMessageBox.critical(self, "Error", "Table name cannot be empty")
            return
        if table_name in self.tables or table_name in [self.table_combo.itemText(i) for i in range(self.table_combo.count())]:
            QMessageBox.critical(self, "Error", "Table name already exists")
            return
        print(f"add_new_table: Adding table {table_name}")
        try:
            self.tables[table_name] = []
            self.current_table = table_name
            self.table_combo.blockSignals(True)
            self.table_combo.addItem(table_name)
            self.table_combo.setCurrentText(table_name)
            self.table_combo.blockSignals(False)
            self.clear_table_ui()
            self.update_sql_display()
            print(f"add_new_table: Table {table_name} added")
        except Exception as e:
            print(f"add_new_table: Error - {str(e)}")
            raise

    def switch_table(self, table_name):
        """Switch to a different table and update the UI."""
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
                item = QTreeWidgetItem([
                    field['name'],
                    field['display_type'],
                    field['range'],
                    "✔" if field['not_null'] else "",
                    "✔" if field['primary_key'] else "",
                    "✔" if field['autoincrement'] else "",
                    "✔" if field['unique'] else ""
                ])
                self.tree.addTopLevelItem(item)
            self.tree.blockSignals(False)
            self.update_sql_display()
            self.update_button_states()
            print(f"switch_table: Completed")
        except Exception as e:
            print(f"switch_table: Error - {str(e)}")
            raise

    def clear_table_ui(self):
        """Clear the table UI elements."""
        print("clear_table_ui: Starting")
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
            self.update_button_states()
            print("clear_table_ui: Completed")
        except Exception as e:
            print(f"clear_table_ui: Error - {str(e)}")
            raise

    def update_add_field_widgets(self):
        """Show or hide subtype frame based on type."""
        print("update_add_field_widgets: Starting")
        try:
            if self.type_combo.currentText() == "TEXT":
                self.subtype_frame.show()
                self.update_range_entry()
            else:
                self.subtype_frame.hide()
                self.range_entry.setEnabled(False)
                self.range_entry.clear()
            print("update_add_field_widgets: Completed")
        except Exception as e:
            print(f"update_add_field_widgets: Error - {str(e)}")
            raise

    def update_range_entry(self):
        """Enable or disable length entry based on subtype."""
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
        """Enable AI checkbox only when type is INTEGER and PK is checked."""
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

    def add_field(self):
        """Add a field to the current table."""
        print("add_field: Starting")
        try:
            if not self.current_table:
                QMessageBox.critical(self, "Error", "No table selected. Create a new table first.")
                print("add_field: Error - No table selected")
                return
            name = self.field_name_entry.text().strip()
            if not name:
                QMessageBox.critical(self, "Error", "Field name cannot be empty")
                print("add_field: Error - Field name empty")
                return
            main_type = self.type_combo.currentText()
            range_val = self.range_entry.text().strip() if self.range_entry.isEnabled() else ""

            if main_type == "TEXT":
                subtype = self.subtype_combo.currentText()
                if subtype in ["CHAR", "VCHAR", "NCHAR", "NVCHAR"] and range_val:
                    field_type = f"{subtype}({range_val})"
                    display_type = subtype
                else:
                    field_type = subtype
                    display_type = subtype
            else:
                field_type = main_type
                display_type = main_type

            item = QTreeWidgetItem([
                name, display_type, range_val,
                "✔" if self.nn_check.isChecked() else "",
                "✔" if self.pk_check.isChecked() else "",
                "✔" if self.ai_check.isChecked() else "",
                "✔" if self.u_check.isChecked() else ""
            ])
            self.tree.blockSignals(True)
            self.tree.addTopLevelItem(item)
            self.tree.blockSignals(False)
            if self.current_table not in self.tables:
                self.tables[self.current_table] = []
            self.tables[self.current_table].append({
                "name": name, "type": field_type, "range": range_val, "display_type": display_type,
                "not_null": self.nn_check.isChecked(), "primary_key": self.pk_check.isChecked(),
                "autoincrement": self.ai_check.isChecked(), "unique": self.u_check.isChecked()
            })

            # Reset controls
            self.clear_field_input()
            self.update_sql_display()
            self.update_button_states()
            print("add_field: Completed")
        except Exception as e:
            print(f"add_field: Error - {str(e)}")
            raise

    def modify_field(self):
        """Modify the selected field in the current table."""
        print("modify_field: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if not selected_items or not self.current_table:
                QMessageBox.critical(self, "Error", "No field selected")
                print("modify_field: Error - No field selected")
                return
            index = self.tree.indexOfTopLevelItem(selected_items[0])
            name = self.field_name_entry.text().strip()
            if not name:
                QMessageBox.critical(self, "Error", "Field name cannot be empty")
                print("modify_field: Error - Field name empty")
                return
            main_type = self.type_combo.currentText()
            range_val = self.range_entry.text().strip() if self.range_entry.isEnabled() else ""

            if main_type == "TEXT":
                subtype = self.subtype_combo.currentText()
                if subtype in ["CHAR", "VCHAR", "NCHAR", "NVCHAR"] and range_val:
                    field_type = f"{subtype}({range_val})"
                    display_type = subtype
                else:
                    field_type = subtype
                    display_type = subtype
            else:
                field_type = main_type
                display_type = main_type

            # Update field in self.tables
            self.tables[self.current_table][index] = {
                "name": name, "type": field_type, "range": range_val, "display_type": display_type,
                "not_null": self.nn_check.isChecked(), "primary_key": self.pk_check.isChecked(),
                "autoincrement": self.ai_check.isChecked(), "unique": self.u_check.isChecked()
            }

            # Update UI
            item = QTreeWidgetItem([
                name, display_type, range_val,
                "✔" if self.nn_check.isChecked() else "",
                "✔" if self.pk_check.isChecked() else "",
                "✔" if self.ai_check.isChecked() else "",
                "✔" if self.u_check.isChecked() else ""
            ])
            self.tree.blockSignals(True)
            self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(index, item)
            self.tree.setCurrentItem(item)
            self.tree.blockSignals(False)

            self.clear_field_input()
            self.update_sql_display()
            self.update_button_states()
            print("modify_field: Completed")
        except Exception as e:
            print(f"modify_field: Error - {str(e)}")
            raise

    def clear_field_input(self):
        """Clear field input controls."""
        self.field_name_entry.clear()
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentText("INTEGER")
        self.type_combo.blockSignals(False)
        self.subtype_combo.blockSignals(True)
        self.subtype_combo.setCurrentText("TEXT")
        self.subtype_combo.blockSignals(False)
        self.range_entry.clear()
        self.range_entry.setEnabled(False)
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

    def remove_field(self):
        """Remove the selected field from the current table."""
        print("remove_field: Starting")
        try:
            selected_items = self.tree.selectedItems()
            if not selected_items or not self.current_table:
                QMessageBox.critical(self, "Error", "No field selected or no table selected")
                print("remove_field: Error - No field or table selected")
                return
            index = self.tree.indexOfTopLevelItem(selected_items[0])
            self.tree.blockSignals(True)
            self.tree.takeTopLevelItem(index)
            self.tree.blockSignals(False)
            self.tables[self.current_table].pop(index)
            self.update_sql_display()
            self.update_button_states()
            print("remove_field: Completed")
        except Exception as e:
            print(f"remove_field: Error - {str(e)}")
            raise

    def move_top(self):
        """Move the selected field to the top."""
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
            print("move_top: Completed")
        except Exception as e:
            print(f"move_top: Error - {str(e)}")
            raise

    def move_up(self):
        """Move the selected field up one position."""
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
            print("move_up: Completed")
        except Exception as e:
            print(f"move_up: Error - {str(e)}")
            raise

    def move_down(self):
        """Move the selected field down one position."""
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
            print("move_down: Completed")
        except Exception as e:
            print(f"move_down: Error - {str(e)}")
            raise

    def move_bottom(self):
        """Move the selected field to the bottom."""
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
            print("move_bottom: Completed")
        except Exception as e:
            print(f"move_bottom: Error - {str(e)}")
            raise

    def update_button_states(self):
        """Update the state of manipulation buttons."""
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
        """Enable Modify button if a field is selected."""
        print("update_modify_button_state: Starting")
        try:
            state = bool(self.current_table and self.tree.selectedItems())
            self.modify_field_button.setEnabled(state)
            print("update_modify_button_state: Completed")
        except Exception as e:
            print(f"update_modify_button_state: Error - {str(e)}")
            raise

    def update_sql_display(self):
        """Update the SQL text display with the current table definition."""
        print("update_sql_display: Starting")
        try:
            table_name = self.table_name_entry.text().strip() or ""
            sql = f"CREATE TABLE \"{table_name}\" (\n"
            fields = self.tables.get(self.current_table, [])
            # Collect primary key fields
            pk_fields = [field for field in fields if field['primary_key']]

            # Define columns
            column_defs = []
            for field in fields:
                col_def = f'    "{field["name"]}" {field["type"]}'
                if field['not_null'] and not field['primary_key']:
                    col_def += " NOT NULL"
                if field['unique'] and not field['primary_key']:
                    col_def += " UNIQUE"
                column_defs.append(col_def)

            # Add PRIMARY KEY clause
            if pk_fields:
                if len(pk_fields) == 1:
                    pk_field = pk_fields[0]
                    pk_name = pk_field['name']
                    if pk_field['autoincrement'] and pk_field['type'].startswith("INTEGER"):
                        pk_clause = f'    PRIMARY KEY("{pk_name}" AUTOINCREMENT)'
                    else:
                        pk_clause = f'    PRIMARY KEY("{pk_name}")'
                else:
                    pk_names = ", ".join(f'"{field["name"]}"' for field in pk_fields)
                    pk_clause = f"    PRIMARY KEY({pk_names})"
                column_defs.append(pk_clause)

            sql += ",\n".join(column_defs)
            sql += "\n);"
            self.sql_display.setText(sql)
            print("update_sql_display: Completed")
        except Exception as e:
            print(f"update_sql_display: Error - {str(e)}")
            raise

    def apply_table_changes(self):
        """Apply changes to the current table in the database (create or modify)."""
        print("apply_table_changes: Starting")
        try:
            if not self.current_table or not self.tables.get(self.current_table):
                QMessageBox.critical(self, "Error", "Cannot save an empty table. Add at least one field to the table.")
                print("apply_table_changes: Error - No fields")
                return
            if not self.conn:
                QMessageBox.critical(self, "Error", "No database selected")
                print("apply_table_changes: Error - No database")
                return

            table_name = self.current_table
            fields = self.tables[table_name]
            # Check if table exists
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            table_exists = self.cursor.fetchone() is not None

            if not table_exists:
                # Create new table
                sql = self.generate_sql()
                self.cursor.execute(sql)
                self.conn.commit()
                QMessageBox.information(self, "Success", f"Table '{table_name}' created!")
            else:
                # Modify existing table by recreating
                # Generate new schema
                new_sql = self.generate_sql()
                temp_table = f"temp_{table_name}"
                # Create temporary table
                temp_sql = new_sql.replace(f"CREATE TABLE \"{table_name}\"", f"CREATE TABLE \"{temp_table}\"")
                self.cursor.execute(temp_sql)

                # Get old and new columns
                old_cols = []
                self.cursor.execute(f"PRAGMA table_info('{table_name}');")
                for col in self.cursor.fetchall():
                    old_cols.append(col[1])  # cid, name
                new_cols = [f["name"] for f in fields]
                # Find common columns for data transfer
                common_cols = [col for col in old_cols if col in new_cols]
                if common_cols:
                    cols_str = ", ".join(f"\"{col}\"" for col in common_cols)
                    self.cursor.execute(f"INSERT INTO \"{temp_table}\" ({cols_str}) SELECT {cols_str} FROM \"{table_name}\";")
                # Drop old table
                self.cursor.execute(f"DROP TABLE \"{table_name}\";")
                # Rename temporary table
                self.cursor.execute(f"ALTER TABLE \"{temp_table}\" RENAME TO \"{table_name}\";")
                self.conn.commit()
                QMessageBox.information(self, "Success", f"Table '{table_name}' modified successfully!")

            if table_name not in [self.table_combo.itemText(i) for i in range(self.table_combo.count())]:
                self.table_combo.blockSignals(True)
                self.table_combo.addItem(table_name)
                self.table_combo.setCurrentText(table_name)
                self.table_combo.blockSignals(False)
            print("apply_table_changes: Completed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply changes: {str(e)}")
            print(f"apply_table_changes: Error - {str(e)}")
            raise

    def generate_sql(self):
        """Generate SQL for the current table."""
        table_name = self.table_name_entry.text().strip() or self.current_table
        sql = f"CREATE TABLE \"{table_name}\" (\n"
        fields = self.tables.get(self.current_table, [])

        # Collect primary key fields
        pk_fields = [field for field in fields if field['primary_key']]

        # Define columns
        column_defs = []
        for field in fields:
            col_def = f'    "{field["name"]}" {field["type"]}'
            if field['not_null'] and not field['primary_key']:
                col_def += " NOT NULL"
            if field['unique'] and not field['primary_key']:
                col_def += " UNIQUE"
            column_defs.append(col_def)

        # Add PRIMARY KEY clause
        if pk_fields:
            if len(pk_fields) == 1:
                pk_field = pk_fields[0]
                pk_name = pk_field['name']
                if pk_field['autoincrement'] and pk_field['type'].startswith("INTEGER"):
                    pk_clause = f'    PRIMARY KEY("{pk_name}" AUTOINCREMENT)'
                else:
                    pk_clause = f'    PRIMARY KEY("{pk_name}")'
            else:
                pk_names = ", ".join(f'"{field["name"]}"' for field in pk_fields)
                pk_clause = f"    PRIMARY KEY({pk_names})"
            column_defs.append(pk_clause)

        sql += ",\n".join(column_defs)
        sql += "\n);"
        return sql

    def close_app(self):
        """Close the database connection and exit."""
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
    print("main: Starting application")
    try:
        app = QApplication(sys.argv)
        window = TableCreatorApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"main: Error - {str(e)}")
        raise