import sqlite3
import sys
import csv
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem, QTableWidget,
    QTableWidgetItem, QComboBox, QFileDialog, QMessageBox, QHeaderView,
    QLineEdit, QScrollArea, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox as QMessageBoxWidget


class SQLiteEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple SQLite Editor V1.51")
        self.setGeometry(100, 100, 800, 600)

        self.db_path = None
        self.conn = None
        self.cursor = None
        self.active_editor = None
        self.full_data = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.db_label = QLabel("No database selected")
        self.main_layout.addWidget(self.db_label)

        button_layout = QHBoxLayout()
        self.open_btn = QPushButton("Open Database")
        self.open_btn.clicked.connect(self.open_database)
        button_layout.addWidget(self.open_btn)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("Close Database")
        self.close_btn.clicked.connect(self.close_database)
        button_layout.addWidget(self.close_btn)

        self.main_layout.addLayout(button_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Tab 1: Database Structure
        self.tab1 = QWidget()
        self.tabs.addTab(self.tab1, "Database Structure")
        tab1_layout = QVBoxLayout(self.tab1)

        self.tree1 = QTreeWidget()
        self.tree1.setHeaderLabels(["Name", "Type", "Schema"])
        self.tree1.header().resizeSection(0, 150)
        self.tree1.header().resizeSection(1, 100)
        self.tree1.header().resizeSection(2, 400)

        scroll_area1 = QScrollArea()
        scroll_area1.setWidget(self.tree1)
        scroll_area1.setWidgetResizable(True)
        scroll_area1.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area1.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tab1_layout.addWidget(scroll_area1)

        # Tab 2: Browse Data
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab2, "Browse Data")
        tab2_layout = QVBoxLayout(self.tab2)

        self.table_dropdown = QComboBox()
        self.table_dropdown.currentIndexChanged.connect(self.load_table_data)
        tab2_layout.addWidget(self.table_dropdown)

        self.table2 = QTableWidget()
        self.table2.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table2.cellDoubleClicked.connect(self.edit_cell)

        scroll_area2 = QScrollArea()
        scroll_area2.setWidget(self.table2)
        scroll_area2.setWidgetResizable(True)
        scroll_area2.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area2.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tab2_layout.addWidget(scroll_area2)

        button_layout2 = QHBoxLayout()
        self.insert_btn = QPushButton("Insert")
        self.insert_btn.clicked.connect(self.insert_record)
        self.insert_btn.setEnabled(False)
        button_layout2.addWidget(self.insert_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_record)
        self.remove_btn.setEnabled(False)
        button_layout2.addWidget(self.remove_btn)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_records)
        self.search_btn.setEnabled(False)
        button_layout2.addWidget(self.search_btn)

        button_layout2.addStretch()

        self.truncate_btn = QPushButton("Truncate All")
        self.truncate_btn.clicked.connect(self.truncate_records)
        self.truncate_btn.setEnabled(False)
        button_layout2.addWidget(self.truncate_btn)

        tab2_layout.addLayout(button_layout2)

        # Tab 3: Import/Export
        self.tab3 = QWidget()
        self.tabs.addTab(self.tab3, "Import and Export")
        tab3_layout = QVBoxLayout(self.tab3)

        self.import_btn = QPushButton("Import CSV")
        self.import_btn.clicked.connect(self.import_csv)
        tab3_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export to CSV")
        self.export_btn.clicked.connect(self.export_csv)
        tab3_layout.addWidget(self.export_btn)

        self.changes_made = False
        self.current_table = None
        self.column_types = {}
        self.column_constraints = {}

    def open_database(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Database", "", "SQLite files (*.db *.sqlite *.sqlite3)"
        )
        if file_path:
            try:
                self.db_path = file_path
                self.db_label.setText(f"Database: {os.path.basename(file_path)}")
                self.conn = sqlite3.connect(file_path)

                self.load_db_structure()

                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                cursor.close()
                self.table_dropdown.clear()
                self.table_dropdown.addItems(tables)
                if tables:
                    self.table_dropdown.setCurrentIndex(0)
                    self.load_table_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open database: {str(e)}")
                self._reset()

    def format_schema(self, schema):
        if schema is None:
            return ""
        return " ".join(schema.replace("\n", " ").split())

    def load_db_structure(self):
        self.tree1.clear()

        cursor = self.conn.cursor() if self.conn else None
        if not cursor:
            QMessageBox.critical(self, "Error", "No database connection available.")
            return

        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
        except Exception as e:
            cursor.close()
            QMessageBox.critical(self, "Error", f"Failed to load database structure: {str(e)}")
            return

        for table in tables:
            table_name = table[0]
            parent = QTreeWidgetItem(self.tree1, [table_name, "", ""])
            self.tree1.expandItem(parent)

            try:
                sub_cursor = self.conn.cursor()
                escaped_table_name = table_name.replace('"', '""')
                sub_cursor.execute(f'PRAGMA table_info("{escaped_table_name}")')
                columns = sub_cursor.fetchall()

                for col in columns:
                    col_name, col_type = col[1], col[2]
                    QTreeWidgetItem(parent, [col_name, col_type, ""])

                sub_cursor.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                schema_result = sub_cursor.fetchone()
                schema = schema_result[0] if schema_result else ""
                formatted_schema = self.format_schema(schema)
                parent.setText(2, formatted_schema)
                sub_cursor.close()
            except Exception as e:
                sub_cursor.close()
                QMessageBox.warning(
                    self, "Warning",
                    f"Failed to load structure for table '{table_name}': {str(e)}"
                )
                continue
        cursor.close()

    def load_table_data(self):
        new_table = self.table_dropdown.currentText()
        if not new_table:
            return

        if self.current_table and self.changes_made:
            response = QMessageBox.question(
                self, "Unsaved Changes",
                f"You have unsaved changes in table '{self.current_table}'. Do you want to save them before switching to '{new_table}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if response == QMessageBox.StandardButton.Yes:
                self.save_changes()
            elif response == QMessageBox.StandardButton.Cancel:
                self.table_dropdown.setCurrentText(self.current_table)
                return

        self.current_table = new_table
        self.table2.blockSignals(True)
        self.table2.clear()
        self.table2.setHorizontalHeaderLabels([])
        self.table2.setColumnCount(0)
        self.table2.setRowCount(0)
        self.table2.blockSignals(False)

        self.column_types = {}
        self.column_constraints = {}
        self.full_data = []

        cursor = self.conn.cursor() if self.conn else None
        if not cursor:
            QMessageBox.critical(self, "Error", "No database connection available.")
            return

        try:
            escaped_table_name = self.current_table.replace('"', '""')
            cursor.execute(f'PRAGMA table_info("{escaped_table_name}")')
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]
            self.column_types = {col[1]: col[2] for col in columns_info}
            self.column_constraints = {col[1]: self.parse_column_constraints(col) for col in columns_info}

            self.table2.setColumnCount(len(columns))
            self.table2.setHorizontalHeaderLabels(columns)
            for i in range(len(columns)):
                self.table2.horizontalHeader().resizeSection(i, 100)

            cursor.execute(f'SELECT * FROM "{escaped_table_name}"')
            rows = cursor.fetchall()
            self.table2.setRowCount(len(rows))
            self.full_data = [list(row) for row in rows]

            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    display_text = "Null" if value is None else str(value)
                    actual_value = "" if value is None else str(value)
                    item = QTableWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, actual_value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table2.setItem(row_idx, col_idx, item)

            self.insert_btn.setEnabled(True)
            self.remove_btn.setEnabled(len(rows) > 0)
            self.search_btn.setEnabled(len(rows) > 0)
            self.truncate_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load table data: {str(e)}")
            self._reset()
        finally:
            cursor.close()

    def parse_column_constraints(self, column_info):
        constraints = {}
        col_type = column_info[2].upper() if column_info[2] else ""

        if 'CHAR' in col_type or 'TEXT' in col_type:
            match = re.search(r'\((\d+)\)', column_info[2] or "")
            if match:
                constraints['max_length'] = int(match.group(1))

        constraints['not_null'] = bool(column_info[3])
        return constraints

    def insert_record(self):
        if self.table2.columnCount() == 0:
            QMessageBox.warning(self, "Warning", "No columns available to insert a record.")
            return

        row_count = self.table2.rowCount()
        self.table2.blockSignals(True)
        self.table2.setRowCount(row_count + 1)
        new_row = [""] * self.table2.columnCount()
        for col_idx in range(self.table2.columnCount()):
            item = QTableWidgetItem("Null")
            item.setData(Qt.ItemDataRole.UserRole, "")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table2.setItem(row_count, col_idx, item)
        self.table2.blockSignals(False)

        self.full_data.append(new_row)
        self.changes_made = True
        self.remove_btn.setEnabled(True)
        self.search_btn.setEnabled(True)

    def remove_record(self):
        selected_rows = self.table2.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a row to remove.")
            return

        row = selected_rows[0].row()
        displayed_row = [self.table2.item(row, i).data(Qt.ItemDataRole.UserRole) if self.table2.item(row, i) else "" for
                         i in range(self.table2.columnCount())]
        for i, full_row in enumerate(self.full_data):
            if all(str(full_row[j]) == str(displayed_row[j]) for j in range(len(displayed_row))):
                del self.full_data[i]
                break

        self.table2.removeRow(row)
        self.changes_made = True
        if self.table2.rowCount() == 0:
            self.remove_btn.setEnabled(False)
            self.search_btn.setEnabled(False)

    def search_records(self):
        if not self.current_table:
            return

        search_dialog = QDialog(self)
        search_dialog.setWindowTitle("Search Records")
        search_dialog.setGeometry(300, 300, 400, 150)
        dialog_layout = QVBoxLayout(search_dialog)

        search_input_layout = QHBoxLayout()
        search_label = QLabel("Search Term:")
        self.search_input = QLineEdit()
        search_input_layout.addWidget(search_label)
        search_input_layout.addWidget(self.search_input)
        dialog_layout.addLayout(search_input_layout)

        field_layout = QHBoxLayout()
        field_label = QLabel("Field:")
        self.field_combo = QComboBox()
        columns = [self.table2.horizontalHeaderItem(i).text() for i in range(self.table2.columnCount())]
        self.field_combo.addItems(columns)
        field_layout.addWidget(field_label)
        field_layout.addWidget(self.field_combo)
        dialog_layout.addLayout(field_layout)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(lambda: self.perform_search(search_dialog))
        dialog_layout.addWidget(search_btn)

        search_dialog.exec()

    def perform_search(self, dialog):
        search_term = self.search_input.text().strip()
        field_name = self.field_combo.currentText()

        if not search_term:
            QMessageBox.warning(self, "Warning", "Please enter a search term.")
            return

        # Get current displayed rows in table2
        displayed_rows = []
        for row in range(self.table2.rowCount()):
            displayed_row = [
                self.table2.item(row, col).data(Qt.ItemDataRole.UserRole) if self.table2.item(row, col) else "" for col
                in range(self.table2.columnCount())]
            displayed_rows.append(displayed_row)

        # Find the column index for the field to search
        columns = [self.table2.horizontalHeaderItem(i).text() for i in range(self.table2.columnCount())]
        field_idx = columns.index(field_name) if field_name in columns else -1
        if field_idx == -1:
            QMessageBox.warning(self, "Error", f"Field '{field_name}' not found.")
            return

        # Filter displayed rows based on the search term
        filtered_rows = [
            row for row in displayed_rows
            if search_term.lower() in str(row[field_idx]).lower()
        ]

        if not filtered_rows:
            QMessageBox.warning(self, "No Matches", f"No records found where {field_name} contains '{search_term}'.")
            dialog.accept()
            return

        # Update table2 with filtered rows
        self.table2.blockSignals(True)
        self.table2.clearContents()
        self.table2.setRowCount(len(filtered_rows))

        for row_idx, row in enumerate(filtered_rows):
            for col_idx, value in enumerate(row):
                display_text = "Null" if value in (None, "", "NULL") else str(value)
                actual_value = "" if value in (None, "", "NULL") else str(value)
                item = QTableWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, actual_value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table2.setItem(row_idx, col_idx, item)

        self.table2.blockSignals(False)
        self.remove_btn.setEnabled(len(filtered_rows) > 0)
        self.search_btn.setEnabled(len(filtered_rows) > 0)
        self.changes_made = False
        dialog.accept()

    def edit_cell(self, row, column):
        if self.active_editor:
            try:
                self.active_editor.returnPressed.disconnect()
                self.active_editor.editingFinished.disconnect()
            except TypeError:
                pass
            self.active_editor.deleteLater()
            self.active_editor = None

        column_name = self.table2.horizontalHeaderItem(column).text()
        constraints = self.column_constraints.get(column_name, {}) or {}
        current_item = self.table2.item(row, column)
        current_value = current_item.data(Qt.ItemDataRole.UserRole) if current_item else ""
        if current_value is None:
            current_value = ""

        self.active_editor = QLineEdit(self.table2)
        self.active_editor.setText(current_value)

        rect = self.table2.visualItemRect(current_item)
        self.active_editor.setGeometry(rect)
        self.active_editor.show()
        self.active_editor.setFocus()

        def handle_edit():
            if not self.active_editor:
                return

            new_value = self.active_editor.text()
            error = None

            max_length = constraints.get('max_length')
            not_null = constraints.get('not_null', False)

            if not_null and not new_value.strip():
                error = f"Column '{column_name}' cannot be empty (NOT NULL constraint)."
            elif max_length is not None and len(new_value) > max_length:
                error = f"Value in column '{column_name}' exceeds maximum length of {max_length} characters."

            if error:
                QMessageBox.warning(self, "Validation Error", error)
            else:
                display_text = "Null" if not new_value else new_value
                item = QTableWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, new_value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table2.setItem(row, column, item)

                displayed_row = [
                    self.table2.item(row, i).data(Qt.ItemDataRole.UserRole) if self.table2.item(row, i) else "" for i in
                    range(self.table2.columnCount())]
                for i, full_row in enumerate(self.full_data):
                    if all(str(full_row[j]) == str(displayed_row[j]) for j in range(len(displayed_row)) if j != column):
                        self.full_data[i][column] = new_value
                        break
                self.changes_made = True

            try:
                self.active_editor.returnPressed.disconnect()
                self.active_editor.editingFinished.disconnect()
            except TypeError:
                pass
            self.active_editor.deleteLater()
            self.active_editor = None

        self.active_editor.returnPressed.connect(handle_edit)
        self.active_editor.editingFinished.connect(handle_edit)

    def convert_value(self, value, col_type):
        if value in (None, "", "NULL"):
            return None
        try:
            if "INTEGER" in col_type.upper():
                return int(value)
            elif "FLOAT" in col_type.upper() or "REAL" in col_type.upper():
                return float(value)
            elif "CHAR" in col_type.upper() or "TEXT" in col_type.upper():
                return str(value)
            else:
                return value
        except (ValueError, TypeError):
            return None

    def save_changes(self):
        if not self.current_table or not self.changes_made:
            return

        cursor = self.conn.cursor() if self.conn else None
        if not cursor:
            QMessageBox.critical(self, "Error", "No database connection available.")
            return

        try:
            displayed_rows = []
            for row in range(self.table2.rowCount()):
                displayed_row = [
                    self.table2.item(row, col).data(Qt.ItemDataRole.UserRole) if self.table2.item(row, col) else "" for
                    col in range(self.table2.columnCount())]
                displayed_rows.append(displayed_row)

            for displayed_row in displayed_rows:
                found = False
                for i, full_row in enumerate(self.full_data):
                    if all(str(full_row[j]) == str(displayed_row[j]) for j in range(len(displayed_row))):
                        self.full_data[i] = displayed_row
                        found = True
                        break
                if not found:
                    pass

            columns = [self.table2.horizontalHeaderItem(i).text() for i in range(self.table2.columnCount())]
            student_id_idx = columns.index("Student_ID") if "Student_ID" in columns else -1
            if student_id_idx != -1:
                student_ids = [row[student_id_idx] for row in self.full_data]
                if any(not sid.strip() for sid in student_ids):
                    raise ValueError("Student_ID cannot be empty (NOT NULL constraint).")
                if len(student_ids) != len(set(student_ids)):
                    raise ValueError("Duplicate Student_ID found. Student_ID must be unique.")

            escaped_table_name = self.current_table.replace('"', '""')
            cursor.execute(f'DELETE FROM "{escaped_table_name}"')
            placeholders = ",".join(["?"] * len(columns))

            for row in self.full_data:
                values = row
                for col_idx, col_name in enumerate(columns):
                    constraints = self.column_constraints.get(col_name, {})
                    max_length = constraints.get('max_length')
                    not_null = constraints.get('not_null', False)
                    value = values[col_idx]

                    if not_null and not value.strip():
                        raise ValueError(f"Column '{col_name}' cannot be empty (NOT NULL constraint).")
                    if max_length is not None and len(value) > max_length:
                        raise ValueError(
                            f"Value in column '{col_name}' exceeds maximum length of {max_length} characters.")

                converted_values = [self.convert_value(val, self.column_types[columns[i]]) for i, val in
                                    enumerate(values)]
                cursor.execute(f'INSERT INTO "{escaped_table_name}" VALUES ({placeholders})', converted_values)

            self.conn.commit()
            self.changes_made = False
            QMessageBox.information(self, "Success", "Changes saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
        finally:
            cursor.close()

    def truncate_records(self):
        if not self.current_table:
            return

        if self.changes_made:
            response = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Truncating will discard them. Proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if response != QMessageBox.StandardButton.Yes:
                return

        confirm_box = QMessageBoxWidget()
        confirm_box.setIcon(QMessageBoxWidget.Icon.Warning)
        confirm_box.setWindowTitle("Confirm Truncate")
        confirm_box.setText(f"Delete ALL records from '{self.current_table}'? This cannot be undone!")
        yes_button = confirm_box.addButton(QMessageBoxWidget.StandardButton.Yes)
        no_button = confirm_box.addButton(QMessageBoxWidget.StandardButton.No)
        confirm_box.setDefaultButton(no_button)
        confirm_box.exec()

        if confirm_box.clickedButton() == yes_button:
            cursor = self.conn.cursor() if self.conn else None
            if not cursor:
                QMessageBox.critical(self, "Error", "No database connection available.")
                return

            try:
                escaped_table_name = self.current_table.replace('"', '""')
                cursor.execute(f'DELETE FROM "{escaped_table_name}"')
                self.conn.commit()
                self.load_table_data()
                QMessageBox.information(self, "Success", "All records deleted")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Truncate failed: {str(e)}")
            finally:
                cursor.close()

    def normalize_date(self, date_str):
        # Remove extra spaces and handle various date formats
        date_str = date_str.strip().replace(" ", "")
        # Try parsing common formats
        for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"]:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%d-%m-%Y")
            except ValueError:
                continue
        # If parsing fails, return the original (will fail validation if too long)
        return date_str

    def import_csv(self):
        if not self.current_table:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV files (*.csv)"
        )
        if file_path:
            cursor = self.conn.cursor() if self.conn else None
            if not cursor:
                QMessageBox.critical(self, "Error", "No database connection available.")
                return

            try:
                with open(file_path, "r") as f:
                    reader = csv.reader(f)
                    header = next(reader)

                    escaped_table_name = self.current_table.replace('"', '""')
                    cursor.execute(f'PRAGMA table_info("{escaped_table_name}")')
                    db_columns = [col[1] for col in cursor.fetchall()]

                    if header != db_columns:
                        QMessageBox.critical(self, "Error", "CSV header doesn't match table columns")
                        return

                    placeholders = ",".join(["?"] * len(db_columns))
                    current_data = [list(row) for row in self.full_data]
                    birthdate_idx = db_columns.index("Birthdate") if "Birthdate" in db_columns else -1

                    for row in reader:
                        for col_idx, col_name in enumerate(db_columns):
                            constraints = self.column_constraints.get(col_name, {})
                            max_length = constraints.get('max_length')
                            not_null = constraints.get('not_null', False)
                            value = row[col_idx]

                            if col_name == "Birthdate":
                                value = self.normalize_date(value)
                                row[col_idx] = value

                            if not_null and not value.strip():
                                raise ValueError(f"Column '{col_name}' cannot be empty (NOT NULL constraint).")
                            if max_length is not None and len(value) > max_length:
                                raise ValueError(
                                    f"Value in column '{col_name}' exceeds maximum length of {max_length} characters.")

                        converted_row = [
                            self.convert_value(row[i], self.column_types[db_columns[i]])
                            for i in range(len(row))
                        ]
                        cursor.execute(
                            f'INSERT INTO "{escaped_table_name}" VALUES ({placeholders})',
                            converted_row
                        )
                        row_count = self.table2.rowCount()
                        self.table2.setRowCount(row_count + 1)
                        for col_idx, value in enumerate(row):
                            display_text = "Null" if value in (None, "", "NULL") else str(value)
                            actual_value = "" if value in (None, "", "NULL") else str(value)
                            item = QTableWidgetItem(display_text)
                            item.setData(Qt.ItemDataRole.UserRole, actual_value)
                            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.table2.setItem(row_count, col_idx, item)
                        current_data.append(row)

                    self.full_data = current_data
                    self.conn.commit()
                    self.changes_made = False
                    QMessageBox.information(self, "Success", f"Imported {reader.line_num - 1} records")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"CSV import failed: {str(e)}")
            finally:
                cursor.close()

    def export_csv(self):
        if not self.current_table:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "", "CSV files (*.csv)"
        )
        if file_path:
            try:
                with open(file_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    columns = [self.table2.horizontalHeaderItem(i).text() for i in range(self.table2.columnCount())]
                    writer.writerow(columns)

                    for row in range(self.table2.rowCount()):
                        row_data = []
                        for col in range(self.table2.columnCount()):
                            item = self.table2.item(row, col)
                            value = item.data(Qt.ItemDataRole.UserRole) if item else ""
                            row_data.append(value)
                        writer.writerow(row_data)

                    QMessageBox.information(self, "Success", "Data exported successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def close_database(self):
        if self.changes_made:
            if QMessageBox.question(
                    self, "Warning", "Save changes before closing?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.save_changes()
        self._reset()

    def _reset(self):
        self.db_path = None
        if self.conn:
            self.conn.close()
        self.conn = None
        self.cursor = None
        self.db_label.setText("No database selected")
        self.full_data = []

        self.table2.blockSignals(True)
        self.table2.clear()
        self.table2.setHorizontalHeaderLabels([])
        self.table2.setColumnCount(0)
        self.table2.setRowCount(0)
        self.table2.blockSignals(False)
        self.tree1.clear()
        self.table_dropdown.clear()
        self.insert_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.truncate_btn.setEnabled(False)
        self.changes_made = False
        self.current_table = None
        self.column_types = {}
        self.column_constraints = {}


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = SQLiteEditor()
    editor.show()
    sys.exit(app.exec())