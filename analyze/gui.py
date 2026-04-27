from qtpy.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit, 
    QCheckBox, QSpinBox, QFileDialog, QVBoxLayout, 
    QGridLayout, QHBoxLayout, QScrollArea,
    QMessageBox, QGroupBox
)
from qtpy.QtCore import Qt
from analyzer import CellsSignalAnalyzer
import os
import re

comma_sep_floats_regex = re.compile(r'^\s*-?\d+(\.\d+)?\s*(,\s*-?\d+(\.\d+)?\s*)*$')

class MetricsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.analyzer = None
        self.output_folder = None

        self.setWindowTitle("Measures analyzer")

        self._metric_rows = []

        main_layout = QVBoxLayout(self)

        # -------------------------------------------------
        # File selection
        # -------------------------------------------------
        self.file_button = QPushButton("Choose CSV/TSV file")
        self.file_button.clicked.connect(self._choose_file)
        main_layout.addWidget(self.file_button)

        self.label_info = QLabel("No file selected.")
        self.label_info.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.label_info, alignment=Qt.AlignCenter)

        main_layout.addSpacing(15)

        # -------------------------------------------------
        # Selector for excluded classes
        # -------------------------------------------------

        self.excluded_classes_scroll_area = QScrollArea()
        self.excluded_classes_scroll_area.setWidgetResizable(True)
        self.excluded_classes_container = QGroupBox("Excluded classes")
        self.excluded_classes_layout = QVBoxLayout(self.excluded_classes_container)
        self.excluded_classes_scroll_area.setWidget(self.excluded_classes_container)
        main_layout.addWidget(self.excluded_classes_scroll_area, stretch=1)

        # -------------------------------------------------
        # Metrics grid (with headers)
        # -------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.metrics_container = QGroupBox("Available metrics")
        self.metrics_grid = QGridLayout(self.metrics_container)
        self.metrics_grid.setColumnStretch(0, 0)  # checkbox
        self.metrics_grid.setColumnStretch(1, 2)  # metric name
        self.metrics_grid.setColumnStretch(2, 2)  # alias
        self.metrics_grid.setColumnStretch(3, 2)  # milestones
        self.metrics_grid.setColumnStretch(4, 1)  # level

        headers = ["", "Metric name", "Alias", "Milestones", "Level"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold;")
            self.metrics_grid.addWidget(label, 0, col)

        self.scroll_area.setWidget(self.metrics_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        main_layout.addSpacing(15)

        # -------------------------------------------------
        # Selector for reference images
        # -------------------------------------------------
        self.references_scroll_area = QScrollArea()
        self.references_scroll_area.setWidgetResizable(True)

        self.references_container = QGroupBox("Reference images")
        self.references_layout = QVBoxLayout(self.references_container)

        self.references_scroll_area.setWidget(self.references_container)
        main_layout.addWidget(self.references_scroll_area, stretch=1)

        main_layout.addSpacing(15)

        # -------------------------------------------------
        # Bottom buttons
        # -------------------------------------------------
        bottom_layout = QHBoxLayout()

        self.folder_button = QPushButton("Choose output folder")
        self.folder_button.clicked.connect(self._choose_folder)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._run_analysis)

        bottom_layout.addWidget(self.folder_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.run_button)

        main_layout.addLayout(bottom_layout)

    # =================================================
    # Public API
    # =================================================

    def update_reference_images(self):
        if not self.analyzer:
            return
        # Clear existing widgets
        for i in reversed(range(self.references_layout.count())):
            item = self.references_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for image in self.analyzer.get_images():
            checkbox = QCheckBox(image)
            self.references_layout.addWidget(checkbox)

    def get_reference_images(self):
        images = []
        for i in range(self.references_layout.count()):
            item = self.references_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                images.append(widget.text())
        return images
    
    def refresh_excluded_classes(self):
        if not self.analyzer:
            return
        classes = self.analyzer.get_classifications()
        # Clear existing widgets
        for i in reversed(range(self.excluded_classes_layout.count())):
            item = self.excluded_classes_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not classes:
            return
        for cls in classes:
            checkbox = QCheckBox(cls)
            self.excluded_classes_layout.addWidget(checkbox)

    def refresh_metrics_list(self, metrics=None):
        """
        Reset and rebuild the metrics list.

        Parameters
        ----------
        metrics : iterable of str or None
            Metric names to populate the table.
        """
        self._clear_metrics_rows()
        self._metric_rows.clear()

        if not metrics:
            return

        for row, name in enumerate(metrics, start=1):
            checkbox = QCheckBox()
            label = QLabel(name)
            alias_edit = QLineEdit()
            milestones_edit = QLineEdit()
            level = QSpinBox()
            level.setRange(0, 10)

            label.setEnabled(False)
            alias_edit.setEnabled(False)
            milestones_edit.setEnabled(False)
            level.setEnabled(False)
            
            checkbox.stateChanged.connect(
                            lambda state, lbl=label, al=alias_edit, ms=milestones_edit, lv=level: 
                            self._on_checkbox_changed(state, lbl, al, ms, lv)
                        )
            
            milestones_edit.setPlaceholderText("e.g., 0.25, 0.5, 0.75")
            milestones_edit.textChanged.connect(lambda text, widget=milestones_edit: self._on_milestones_changed(text, widget))

            self.metrics_grid.addWidget(checkbox, row, 0, Qt.AlignCenter)
            self.metrics_grid.addWidget(label, row, 1)
            self.metrics_grid.addWidget(alias_edit, row, 2)
            self.metrics_grid.addWidget(milestones_edit, row, 3)
            self.metrics_grid.addWidget(level, row, 4, Qt.AlignCenter)

            self._metric_rows.append(
                (checkbox, label, alias_edit, milestones_edit, level)
            )
    
    def _on_checkbox_changed(self, state, label, alias_edit, milestones_edit, level):
        """
        Enable/disable alias and milestones edits based on checkbox state.
        """
        enabled = state == Qt.Checked
        label.setEnabled(enabled)
        alias_edit.setEnabled(enabled)
        milestones_edit.setEnabled(enabled)
        level.setEnabled(enabled)
    
    def _on_milestones_changed(self, text, widget):
        """
        Validate milestones input format.
        """
        if text == "" or comma_sep_floats_regex.match(text):
            widget.setStyleSheet("border: 1px solid #43eb34;")  # valid
        else:
            widget.setStyleSheet("border: 1px solid #eb3434;")  # invalid

    def get_metrics_state(self):
        """
        Retrieve user selections and inputs.
        """
        data = []
        for checkbox, label, alias, milestones, level in self._metric_rows:
            if not checkbox.isChecked():
                continue
            data.append({
                "metric": label.text(),
                "alias": alias.text(),
                "milestones": milestones.text(),
                "level": level.value(),
            })
        return data

    # =================================================
    # Internal helpers
    # =================================================

    def _clear_metrics_rows(self):
        """
        Remove all rows except the header (row 0).
        """
        for i in reversed(range(self.metrics_grid.count())):
            item = self.metrics_grid.itemAt(i)
            widget = item.widget()
            if widget is not None:
                row, _, _, _ = self.metrics_grid.getItemPosition(i)
                if row > 0:
                    widget.deleteLater()

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select data file",
            "",
            "Data files (*.csv *.tsv)"
        )
        if not path:
            return
        self.analyzer = CellsSignalAnalyzer(path)
        self.analyzer.detect_classifications()
        self.analyzer.format_classification()
        self.refresh_metrics_list(
            self.analyzer.get_columns()
        )
        self.update_reference_images()
        self.refresh_excluded_classes()
        self.label_info.setText(f"File: {os.path.basename(path)} | Found classes: {', '.join(self.analyzer.get_classifications())}")

    def _choose_folder(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select output folder"
        )
        if path:
            print("Selected folder:", path)
            self.output_folder = path

    def _run_analysis(self):
        if not self.analyzer:
            print("--- No data file loaded. ---")
            return
        
        if self.output_folder is None:
            print("--- No output folder selected. ---")
            return
        
        excluded_classes = []
        for i in range(self.excluded_classes_layout.count()):
            item = self.excluded_classes_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                excluded_classes.append(widget.text())
        self.analyzer.set_exclusions(excluded_classes)
        self.analyzer.exclude()
        
        metrics_state = self.get_metrics_state()
        for metric in metrics_state:
            name = metric['alias'] if metric['alias'] else metric['metric']
            milestones_text = metric['milestones']
            if milestones_text:
                milestones = [float(m.strip()) for m in milestones_text.split(',') if m.strip()]
            else:
                milestones = []
            self.analyzer.add_measurable(name, metric['metric'], milestones, metric['level'])
        
        reference_images = self.get_reference_images()
        self.analyzer.set_references(reference_images)
        self.analyzer.process_thresholds()

        self.analyzer.make_summary()
        self.analyzer.summary_stats.to_csv(
            os.path.join(self.output_folder, "summary.tsv"), 
            sep="\t", 
            index=False
        )
        self.analyzer.raw_values_to_tsv(self.output_folder)
        QMessageBox.information(
            self,
            "Success",
            "Analysis completed!"
        )


# -----------------------------------------------------
# Standalone test
# -----------------------------------------------------
if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)

    w = MetricsWindow()
    w.show()

    sys.exit(app.exec_())
