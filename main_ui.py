from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QSpinBox, QCheckBox
)
from PyQt5.QtCore import QThread, pyqtSignal
import sys
import io
import logging
from contextlib import redirect_stdout
from controllers.cli_controller import CLIScrapeController
from state_manager import StateManager

class QTextEditLogger(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)

class ScraperWorker(QThread):
    output_ready = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url, max_pages, delay, headless, state_manager=None):
        super().__init__()
        self.url = url
        self.scraper_args = {
            'max_pages': max_pages,
            'delay': delay,
            'headless': headless
        }
        # Use provided state manager or create new one
        self.state_manager = state_manager or StateManager()
        self.controller = CLIScrapeController(self.state_manager)
        self.should_stop = False

        # Setup logging
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        self.log_handler = QTextEditLogger(self.output_ready)
        root_logger.addHandler(self.log_handler)

    def run(self):
        try:
            # Only initialize state if no existing state
            if not self.state_manager.state:
                self.state_manager.initialize_state(self.url, **self.scraper_args)
            self.controller.start_scraping(self.url, self.scraper_args)
        except Exception as e:
            self.output_ready.emit(f"Error: {str(e)}")
        finally:
            # Remove log handler when done
            logging.getLogger().removeHandler(self.log_handler)
            self.finished.emit()

    def stop(self):
        """Non-blocking stop"""
        if self.controller:
            self.controller.stop()
            # Don't wait here anymore

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sahibinden Scraper")
        self.setMinimumSize(800, 600)
        self.worker = None
        self.state_manager = StateManager()
        self.current_session_file = None  # Add this to track current session file
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Session management group
        session_group = QHBoxLayout()
        
        # Load session button
        self.load_session_btn = QPushButton("Load Session")
        self.load_session_btn.clicked.connect(self.load_session)
        
        # Save session button
        self.save_session_btn = QPushButton("Save Session")
        self.save_session_btn.clicked.connect(self.save_session)
        self.save_session_btn.setEnabled(False)
        
        # Auto-save checkbox
        self.autosave_checkbox = QCheckBox("Auto-save Session")
        self.autosave_checkbox.setChecked(True)
        
        session_group.addWidget(self.load_session_btn)
        session_group.addWidget(self.save_session_btn)
        session_group.addWidget(self.autosave_checkbox)
        session_group.addStretch()
        
        layout.addLayout(session_group)

        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("Search URL:")
        self.url_input = QLineEdit()
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Settings
        settings_layout = QHBoxLayout()
        
        self.max_pages_spinbox = QSpinBox()
        self.max_pages_spinbox.setRange(1, 100)
        self.max_pages_spinbox.setValue(1)
        settings_layout.addWidget(QLabel("Max Pages:"))
        settings_layout.addWidget(self.max_pages_spinbox)
        
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(1, 10)
        self.delay_spinbox.setValue(2)
        settings_layout.addWidget(QLabel("Delay (seconds):"))
        settings_layout.addWidget(self.delay_spinbox)
        
        self.headless_checkbox = QCheckBox("Headless Mode")
        settings_layout.addWidget(self.headless_checkbox)
        
        layout.addLayout(settings_layout)

        # Add session status label
        self.session_label = QLabel("No active session")
        layout.addWidget(self.session_label)

        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_scraping)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_scraping)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def load_session(self):
        """Load previous session state"""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session State",
            "",
            "JSON Files (*.json)"
        )
        if filename:
            try:
                self.state_manager = StateManager(filename)
                if self.state_manager.state:
                    # Store current session file
                    self.current_session_file = filename
                    
                    # Update UI with saved state
                    self.url_input.setText(self.state_manager.state.url)
                    saved_args = self.state_manager.get_scraper_args()
                    self.max_pages_spinbox.setValue(int(saved_args.get('max_pages', 1)))
                    self.delay_spinbox.setValue(int(saved_args.get('delay', 2)))
                    self.headless_checkbox.setChecked(saved_args.get('headless', False))
                    
                    # Update session info
                    self.session_label.setText(f"Loaded session: {filename}")
                    self.save_session_btn.setEnabled(True)
                    self.log_area.append(f"Loaded session from {filename}")
                    
                    # Update log with resume info
                    current_page, last_id, processed = self.state_manager.get_resume_info()
                    self.log_area.append(f"Will resume from page {current_page}")
                    self.log_area.append(f"Already processed {len(processed)} listings")
            except Exception as e:
                self.log_area.append(f"Error loading session: {str(e)}")

    def save_session(self):
        """Save current session state"""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session State",
            self.current_session_file or "",  # Use current session file as default
            "JSON Files (*.json)"
        )
        if filename:
            try:
                # If we have an active session, just update the file path
                if self.state_manager.state:
                    self.state_manager.state_file = filename
                else:
                    # Initialize new state if none exists
                    self.state_manager.initialize_state(
                        self.url_input.text(),
                        max_pages=self.max_pages_spinbox.value(),
                        delay=self.delay_spinbox.value(),
                        headless=self.headless_checkbox.isChecked()
                    )
                    self.state_manager.state_file = filename
                
                self.state_manager.save_state()
                self.current_session_file = filename
                self.session_label.setText(f"Saved session: {filename}")
                self.log_area.append(f"Saved session to {filename}")
            except Exception as e:
                self.log_area.append(f"Error saving session: {str(e)}")

    def start_scraping(self):
        if not self.url_input.text():
            self.log_area.append("Error: Please enter a URL")
            return

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log_area.clear()

        # Pass the current state_manager to worker
        self.worker = ScraperWorker(
            self.url_input.text(),
            self.max_pages_spinbox.value(),
            self.delay_spinbox.value(),
            self.headless_checkbox.isChecked(),
            state_manager=self.state_manager  # Pass current state manager
        )
        self.worker.output_ready.connect(self.update_log)
        self.worker.finished.connect(self.on_scraping_finished)
        self.worker.start()

        self.save_session_btn.setEnabled(True)

    def stop_scraping(self):
        """Non-blocking stop handling"""
        if self.worker:
            self.stop_button.setEnabled(False)
            self.log_area.append("Stopping scraper...")
            self.worker.stop()
            # Instead of wait(), use finished signal to cleanup
            self.worker.finished.connect(self._cleanup_worker)
    
    def _cleanup_worker(self):
        """Cleanup worker after it's done"""
        if self.worker:
            if self.autosave_checkbox.isChecked():
                try:
                    self.state_manager.save_state()
                    self.log_area.append("Session state auto-saved")
                except Exception as e:
                    self.log_area.append(f"Error auto-saving state: {str(e)}")
            
            self.worker.deleteLater()
            self.worker = None
        self.on_scraping_finished()

    def update_log(self, text):
        self.log_area.append(text)

    def on_scraping_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_area.append("Scraping finished")

    def closeEvent(self, event):
        """Handle application closing"""
        if self.worker:
            self.worker.stop()
            # Give a short timeout for cleanup
            if not self.worker.wait(1000):  # Wait max 1 second
                self.worker.terminate()  # Force quit if still running
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
