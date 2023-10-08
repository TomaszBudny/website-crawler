# Required libraries
import sys
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QTableWidgetItem, QTableWidget, QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QTextEdit, QFileDialog,
                             QHBoxLayout, QListWidget, QListWidgetItem, QCheckBox, QTreeWidget, QTreeWidgetItem, QErrorMessage, QMessageBox, QSpacerItem, QSizePolicy, QDialog)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import threading
import concurrent.futures
import csv
from tests import *
from pprint import pprint
import sys
import logging

default_url = "http://example.org/"
version_info = "Version: 1.0.0\nDate: 2023-10-10"

class ConsoleAndFileLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout  # console output
        self.log = open(filename, "a")  # file output

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass

    def close(self):
        self.log.close()

console_logger = ConsoleAndFileLogger("console.log")

sys.stdout = console_logger
sys.stderr = console_logger

# Set up logging at the start of your script
logging.basicConfig(filename='error.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions, log them, and display a pop-up."""
    # Log the exception
    with open('error.log', 'a') as f:
        f.write(f"Exception type: {exc_type}\n")
        f.write(f"Exception value: {exc_value}\n")
        f.write(f"Exception traceback: {exc_traceback}\n\n")

    # Show a pop-up message
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Error")
    msg.setText("An unexpected error occurred. Please check the error.log file for more details.")
    msg.setDetailedText(str(exc_value))
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()  # This will block until the user clicks "Ok"

    sys.exit(1)  # Exit the program

# Set the function as the default exception handler
sys.excepthook = handle_uncaught_exception

# Number of concurrent threads for crawling
MAX_THREADS = 3  

def save_to_csv(data_list, filename="output.csv"):
    """
    Save a list of lists of dictionaries to a CSV file, preserving the order of columns.

    Args:
        data_list (list): List of lists, where each inner list contains a dictionary with the page data.
        filename (str): Name of the CSV file to save the data to. Defaults to "output.csv".
    """

    # Flatten the list of lists
    flat_data = [item for sublist in data_list for item in sublist]

    # Use a predefined order for the headers
    headers = [
        "H1", "URL", "Alias", "PSI", "Title", "Meta Description", 
        "Robots", "WP version", "Page Weight", "Heading structure", "Accessibility", "W3C", "GTM"
    ]

    # If there's no data, exit early
    if not flat_data:
        print("No data to save.")
        return

    # Write data to the CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()  # Write the headers (column names)
        for data in flat_data:
            if data and isinstance(data, dict):  # Check if data is not None and is a dictionary
                writer.writerow(data)

class CrawlerThread(QThread):
    signal = pyqtSignal(list)  # Signal to emit the crawl results
    # Signal to emit the current page being visited, number of pages visited, and total pages found
    page_signal = pyqtSignal(str, int, int, list)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.is_paused = threading.Event()
        self.is_paused.set()
        self.is_stopped = False
        self.visited = set()
        self.to_visit = [url]
        self.results = []
        self.pages_visited = 0
        self.total_pages_found = 1
        self.lock = threading.Lock()  # Lock to ensure thread-safety when updating shared data

    def run(self):
        all_page_data = []  # List to store page_data for all pages

        # Use ThreadPoolExecutor to concurrently fetch and parse URLs
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            while self.to_visit and not self.is_stopped:
                self.is_paused.wait()  # Wait if the crawling is paused
                futures = {executor.submit(self.fetch_and_parse, url): url for url in self.to_visit[:MAX_THREADS]}
                self.to_visit = self.to_visit[MAX_THREADS:]
                for future in concurrent.futures.as_completed(futures):
                    new_links, title_data, *page_data = future.result() # Updated to capture page_data
                    self.to_visit.extend(new_links)
                    if title_data:
                        self.results.append(title_data)

                    # Append the page_data to all_page_data
                    all_page_data.append(page_data)

                    self.page_signal.emit(title_data if title_data else "", self.pages_visited+1, self.total_pages_found, page_data if page_data else [])
        
        # Print out all the page_data after crawling is done
        save_to_csv(all_page_data)

        self.signal.emit(self.results)  # Emit the crawl results when done


    def fetch_and_parse(self, url):
        # Return if the URL has already been visited or if the crawl has been stopped
        if url in self.visited or self.is_stopped:
            return [], None
        self.visited.add(url)
        self.pages_visited += 1
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers)

        # Check if the content type is not HTML
        if 'text/html' not in response.headers.get('Content-Type', ''):
            # Log or print a message if you want
            print(f"URL {url} returned non-HTML content. Skipping parsing.")
            return [], None, None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title and meta description
        title_tag = soup.find('title')
        meta_desc_tag = soup.find('meta', attrs={"name": "description"})

        h1_tag = check_h1_tag(soup)
        page_weight = get_page_weight(response.content)

        title_data = f"URL: {url}"
        if title_tag:
            title_data += f" - Title: {title_tag.text}"
        if meta_desc_tag:
            title_data += f" - Meta Description: {meta_desc_tag['content']}"

        # Append test results to title_data
        title_data += f" - H1 Tag Present: {h1_tag}"
        title_data += f" - Page Weight: {page_weight} bytes"

        page_data = {
            "H1": check_h1_tag(soup),
            "URL": url,
            "Alias": "/" + url.replace(self.url, ""),
            "Title": check_title_tag(soup),
            "Meta Description": check_meta_description(soup),
            "Robots": check_meta_robots(soup),
            "WP version": check_wordpress_version(soup),
            "Page Weight": get_page_weight(response.content),
            "Heading structure" : structured_headings(soup),
            "PSI": get_pagespeed_score(url),
            "Accessibility": run_accessibility_check(url),
            "W3C": w3c_validation(url),
            "GTM": check_gtm_installed(url),
        }

        new_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
    
            # Skip links that are just '#' or that contain '#'
            if href == '#' or '#' in href:
                continue
            
            if href.startswith('/') or self.url in href:
                if self.url not in href:
                    href = self.url + href
                with self.lock:  # Use the lock to ensure thread-safety
                    if href not in self.visited and href not in self.to_visit:
                        new_links.append(href)
                        self.to_visit.append(href)  # Add to to_visit inside the lock
                        self.total_pages_found += 1
        return new_links, title_data, page_data
    
    def pause(self):
        self.is_paused.clear()

    def resume(self):
        self.is_paused.set()
        
    def stop(self):
        self.is_stopped = True

class WebCrawlerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.url_to_item = {}  # Dictionary to map URLs to their QTreeWidgetItem
        self.init_ui()

    def init_ui(self):
        # Setup the UI components
        self.setWindowTitle('Web Crawler')
        self.setGeometry(100, 100, 600, 600)  # Adjusted window size for list

        self.label = QLabel('Enter URL:')
        self.url_entry = QLineEdit(self)
        self.submit_button = QPushButton('Submit', self)
        self.pause_button = QPushButton("❚❚", self)
        self.pause_button.setToolTip("Pause crawling")
        self.stop_button = QPushButton("■", self)
        self.stop_button.setToolTip("Stop crawling")
        self.result_text = QTextEdit(self)
        self.result_text.setReadOnly(True)
        self.status_label = QLabel("Pages crawled: 0 / Total pages: 0")
        self.about_button = QPushButton("About Us", self)
        self.about_button.clicked.connect(self.show_about)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['URL', 'Title', 'Meta Description'])
        self.table.setRowCount(0)

        # QTreeWidget for crawled pages
        self.crawled_pages_tree = QTreeWidget(self)
        self.crawled_pages_tree.setHeaderLabels(["URL"])
        self.crawled_pages_tree.itemChanged.connect(self.handleItemChanged)

        # Set the default URL
        self.url_entry.setText(default_url)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.submit_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.about_button)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.url_entry)
        layout.addLayout(control_layout)
        layout.addWidget(self.result_text)
        layout.addWidget(self.status_label)
        layout.addWidget(self.crawled_pages_tree)  # Add the tree to the layout
        layout.addWidget(self.table)

        self.setLayout(layout)

        # Connect buttons to respective functions
        self.submit_button.clicked.connect(self.submit)
        self.pause_button.clicked.connect(self.pause_or_resume)
        self.stop_button.clicked.connect(self.stop_crawl)

    # In your main class, you can display the custom AboutDialog like this:
    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About Us")
        
        # Set up text to be displayed
        about_text = ("<center><h2>About Web Crawler</h2></center>"
                    "<center><p>This software is designed to crawl websites and extract useful information.</p></center>"
                    f"<center><p>{version_info}</p></center>")
        
        label = QLabel(about_text)
        
        # Ok button to close the dialog
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(ok_button)
        dialog.setLayout(layout)
        
        # Show the dialog modally
        dialog.exec_()


    def reset_ui(self):
        # Clear result_text
        self.result_text.clear()

        # Clear the QTreeWidget
        self.crawled_pages_tree.clear()

        # Reset the status label
        self.status_label.setText("Pages crawled: 0 / Total pages: 0")

        # Reset the pause button to its initial state
        self.pause_button.setText("❚❚")
        self.pause_button.setToolTip("Pause crawling")

        # Clear the url_to_item dictionary
        self.url_to_item.clear()

    # Handle item changes in the QTreeWidget
    def handleItemChanged(self, item, column):
        # Prevents the signal from being emitted while the state is being set programmatically
        if item.checkState(column) == Qt.Checked:
            item.setExpanded(True)  # Expand the item if checked

    # Submit button function
    def submit(self):
        self.reset_ui()
        url = self.url_entry.text()
        self.start_crawling()

    # Start the crawling process
    def start_crawling(self):
        url = self.url_entry.text()
        self.result_text.append("Crawling website... Please wait.")
        self.thread = CrawlerThread(url)
        self.thread.signal.connect(self.on_crawl_complete)
        self.thread.page_signal.connect(self.update_current_page)
        self.thread.start()
        self.pause_button.setText("❚❚")
        self.pause_button.setToolTip("Pause crawling")

    def addRow(self, url, title, meta_description):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        
        self.table.setItem(row_position, 0, QTableWidgetItem(url))
        self.table.setItem(row_position, 1, QTableWidgetItem(title))
        self.table.setItem(row_position, 2, QTableWidgetItem(meta_description))

    # Update the UI with the currently crawled page's data
    def update_current_page(self, page, pages_crawled, total_pages, page_data):
        if page_data:
            print(page_data)
        if page:
            
            # Split page info to extract URL and title
            page_info = page.split(" - ")
            url = page_data[0]['URL']
            title = page_data[0]['Title'] if page_data[0]['Title'] else "N/A"
            meta_desc = page_data[0]['Meta Description'] if page_data[0]['Meta Description'] else "N/A"
            accessibility_desc = page_data[0]['Accessibility'] if page_data[0]['Accessibility'] else "N/A"

            self.result_text.append(url)
            
            # Check if the URL already exists in the tree widget
            if url not in self.url_to_item:
                
                # Add the crawled URL as a top-level item in the tree
                url_item = QTreeWidgetItem(self.crawled_pages_tree)
                url_item.setText(0, url)
                url_item.setFlags(url_item.flags() | Qt.ItemIsUserCheckable)
                url_item.setCheckState(0, Qt.Unchecked)
                
                # Add the title as a child item
                title_item = QTreeWidgetItem(url_item)
                title_item.setText(0, "Title: " + title)

                # Add the meta description as another child item
                meta_desc_item = QTreeWidgetItem(url_item)
                meta_desc_item.setText(0, "Meta Description: " + meta_desc)

                # Add the meta description as another child item
                accessibility_item = QTreeWidgetItem(url_item)
                accessibility_item.setText(0, "Accessibility: " + page_data[0]['Accessibility'])

                window.addRow(url, title_item, meta_desc_item)

                # Add the URL item to the tree and update the dictionary
                self.crawled_pages_tree.addTopLevelItem(url_item)
                self.url_to_item[url] = url_item
            else:
                # Update the title for the existing URL in the tree widget
                url_item = self.url_to_item[url]
                if url_item.childCount() == 0:
                    # If the title item does not exist, create one
                    title_item = QTreeWidgetItem(url_item)
                    meta_desc_item = QTreeWidgetItem(url_item)  # Create meta description item
                    accessibility_item = QTreeWidgetItem(url_item)  # Create meta description item
                else:
                    title_item = url_item.child(0)  # Assuming the title is always the first child
                    meta_desc_item = url_item.child(1)  # Assuming the meta description is the second child
                    accessibility_item = url_item.child(2)  # Assuming the meta description is the second child
                title_item.setText(0, "Title: " + title)
                meta_desc_item.setText(0, "Meta Description: " + meta_desc)
                accessibility_item.setText(0, "Accessibility: " + accessibility_desc)

            self.status_label.setText(f"Pages crawled: {pages_crawled} / Total pages: {total_pages}")

    # Pause or resume the crawling based on its current state
    def pause_or_resume(self):
        if self.thread.is_paused.is_set():
            self.thread.pause()
            self.pause_button.setText("▶")
            self.pause_button.setToolTip("Resume crawling")
        else:
            self.thread.resume()
            self.pause_button.setText("❚❚")
            self.pause_button.setToolTip("Pause crawling")

    # Stop the crawling process
    def stop_crawl(self):
        self.thread.stop()
        self.result_text.append("Crawling stopped by user.")

    # Handle the completion of the crawling process
    def on_crawl_complete(self, results):
        # if not results:
        #     self.result_text.setPlainText("No titles or meta descriptions found!")
        #     return

        # save_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "CSV Files (*.csv);;All Files (*)")
        # if not save_path:
        #     return

        # with open(save_path, 'w', newline='') as file:
        #     writer = csv.writer(file)
        #     # Write the header row with additional columns for H1 Tag and Page Weight
        #     writer.writerow(["URL", "Title", "Meta Description", "H1 Tag Present", "Page Weight (bytes)"])
        #     for line in results:
        #         # Split the line into its components and write them as a row in the CSV
        #         components = line.split(" - ")
        #         url = components[0].replace("URL: ", "").strip()
        #         title = components[1].replace("Title: ", "").strip() if len(components) > 1 else "N/A"
        #         meta_desc = components[2].replace("Meta Description: ", "").strip() if len(components) > 2 else "N/A"
        #         h1_present = components[3].replace("H1 Tag Present: ", "").strip() if len(components) > 3 else "N/A"
        #         page_weight = components[4].replace("Page Weight: ", "").replace(" bytes", "").strip() if len(components) > 4 else "N/A"
        #         # page_weight = components[4].replace("Accessibility Violations: ", "").strip() if len(components) > 5 else "N/A"
        #         writer.writerow([url, title, meta_desc, h1_present, page_weight])
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Scanning Complete")
        msg_box.setText("Scanning complete! Check your output.csv file for results.")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()  # This will block until the user clicks "Ok"
        self.pause_button.setText("▶")
        self.pause_button.setToolTip("Resume crawling")

# Entry point for the application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WebCrawlerApp()
    window.show()
    sys.exit(app.exec_())
