import os
import sys
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import importlib.util
from threading import Thread
import queue
import json
import shutil
from datetime import datetime

class DirectoryProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Processor")
        self.root.geometry("800x600")
        
        # Initialize variables before setting up UI
        self.search_keyword = tk.StringVar(value="")  # Default keyword from your Lynx_main.py
        self.selected_directory = tk.StringVar()
        self.output_directory = tk.StringVar()
        self.output_folder_name = tk.StringVar(value="Processed_Files")
        self.create_subfolder = tk.BooleanVar(value=True)  # Default to creating a subfolder
        self.processor_module = None
        self.processor_path = tk.StringVar()
        self.results = []
        
        # Queue for processing logs
        self.log_queue = queue.Queue()
        self.after_id = None
        
        # Set up the UI
        self.setup_ui()
        
        # No need for these variables here since they're now defined in __init__

    def setup_ui(self):
        # Create a main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Directory selection
        ttk.Label(config_frame, text="Input Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.selected_directory, width=50).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(config_frame, text="Browse...", command=self.browse_directory).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Output directory selection
        ttk.Label(config_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.output_directory, width=50).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(config_frame, text="Browse...", command=self.browse_output_directory).grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Subfolder options frame
        subfolder_frame = ttk.Frame(config_frame)
        subfolder_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # Checkbox for creating subfolder
        ttk.Checkbutton(subfolder_frame, text="Create subfolder for output", variable=self.create_subfolder, 
                    command=self.toggle_subfolder_options).grid(row=0, column=0, sticky=tk.W)
        
        # Output folder name
        self.subfolder_label = ttk.Label(subfolder_frame, text="Subfolder Name:")
        self.subfolder_label.grid(row=0, column=1, sticky=tk.W, padx=15, pady=5)
        self.subfolder_entry = ttk.Entry(subfolder_frame, textvariable=self.output_folder_name, width=30)
        self.subfolder_entry.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Keyword entry
        ttk.Label(config_frame, text="Search Keyword:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.search_keyword, width=50).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Processor script selection
        ttk.Label(config_frame, text="Processor Script:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.processor_path, width=50).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(config_frame, text="Browse...", command=self.browse_processor).grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Scan Directory", command=self.scan_directory).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self.deselect_all_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Process Selected Files", command=self.process_selected_files).pack(side=tk.LEFT, padx=5)
        
        # Create paned window to allow resizing between results and log
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results frame with Treeview
        results_frame = ttk.LabelFrame(paned_window, text="Found Files", padding="10")
        paned_window.add(results_frame, weight=2)  # Give more weight to results
        
        # Create Treeview
        self.tree = ttk.Treeview(results_frame, columns=("Path", "Keywords Found"), show="headings")
        self.tree.heading("Path", text="File Path")
        self.tree.heading("Keywords Found", text="Keywords Found")
        self.tree.column("Path", width=500)
        self.tree.column("Keywords Found", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Add scrollbar to Treeview
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Log frame
        log_frame = ttk.LabelFrame(paned_window, text="Processing Log", padding="10")
        paned_window.add(log_frame, weight=1)
        
        # Create text widget for logs with fixed height to ensure visibility
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Add scrollbar to log
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Add a sample log message to verify log display works
        self.log_text.insert(tk.END, "Log initialized. Ready to process files.\n")
        self.log_text.see(tk.END)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=5)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.selected_directory.set(directory)
            
    def browse_output_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_directory.set(directory)
    
    def browse_processor(self):
        processor_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
        if processor_path:
            self.processor_path.set(processor_path)
            self.load_processor_module(processor_path)
    
    def load_processor_module(self, path):
        try:
            # Load the processor module
            module_name = os.path.basename(path).replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.processor_module = module
            self.log(f"Successfully loaded processor module: {module_name}")
        except Exception as e:
            self.log(f"Error loading processor module: {str(e)}")
            messagebox.showerror("Error", f"Failed to load processor module: {str(e)}")
    
    def scan_directory(self):
        directory = self.selected_directory.get()
        if not directory:
            messagebox.showwarning("Warning", "Please select a directory first")
            return
        
        keyword = self.search_keyword.get()
        if not keyword:
            messagebox.showwarning("Warning", "Please enter a search keyword")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        
        self.status_var.set("Scanning directory...")
        self.log(f"Starting scan in: {directory} for keyword: {keyword}")
        
        # Start scan in a separate thread
        Thread(target=self._scan_directory_thread, args=(directory, keyword)).start()

    def _scan_directory_thread(self, directory, keyword):
        """
        Scan a directory for files containing the specified keyword.
        This runs in a separate thread to keep the UI responsive.
        
        Args:
            directory (str): Directory to scan
            keyword (str): Keyword to search for
        """
        try:
            found_files = 0
            
            # Update status via the main thread
            self.root.after(0, lambda: self.status_var.set(f"Scanning directory: {directory}"))
            
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.pdf'):
                        file_path = os.path.join(root, file)
                        
                        # Check if the file contains the keyword in its content or filename
                        if self._check_file_for_keyword(file_path, keyword):
                            self.log_queue.put(f"Found file with keyword: {file_path}")
                            self.results.append((file_path, f"Contains keyword: {keyword}"))
                            found_files += 1
                            
            if found_files == 0:
                self.log_queue.put(f"No files found with keyword: {keyword}")
                
            # Update UI from main thread
            self.root.after(0, self._update_results)
            self.root.after(0, lambda: self.status_var.set(f"Found {found_files} files matching '{keyword}'"))
        except Exception as e:
            self.log_queue.put(f"Error scanning directory: {str(e)}")
            # Update status via the main thread
            self.root.after(0, lambda: self.status_var.set("Error during scan"))  

    def _check_file_for_keyword(self, file_path, keyword):
        """Check if a file contains the keyword in its name or basic metadata"""
        try:
            # First check filename
            if keyword.lower() in os.path.basename(file_path).lower():
                return True
                
            # If we have PyPDF2 or other PDF libraries, we could check content
            # For now, we'll just do a basic check on the file itself using binary mode
            # This will catch text in PDF headers and metadata
            try:
                with open(file_path, 'rb') as f:
                    # Read first 5KB which should contain headers and metadata
                    content = f.read(5120)
                    if keyword.encode('utf-8') in content:
                        return True
            except Exception as e:
                self.log_queue.put(f"Warning: Cannot check content of {file_path}: {str(e)}")
                
            # Default to include the file if keyword is empty
            if not keyword.strip():
                return True
                
            return False
        except Exception as e:
            self.log_queue.put(f"Error checking file {file_path}: {str(e)}")
            # Include the file if there's an error, to be safe
            return True
    
    def _update_results(self):
        for file_path, keywords in self.results:
            self.tree.insert("", tk.END, values=(file_path, keywords))
        
        self.status_var.set(f"Found {len(self.results)} files")
        self.log(f"Scan completed. Found {len(self.results)} files.")
    
    def process_selected_files(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select files to process")
            return
        
        if not self.processor_module:
            processor_path = self.processor_path.get()
            if not processor_path:
                messagebox.showwarning("Warning", "Please select a processor script")
                return
            self.load_processor_module(processor_path)
            if not self.processor_module:
                return
        
        selected_files = [self.tree.item(item, "values")[0] for item in selected_items]
        self.log(f"Processing {len(selected_files)} selected files...")
        
        # Start processing in a separate thread
        Thread(target=self._process_files_thread, args=(selected_files,)).start()

    def _process_files_thread(self, files):
        processed_count = 0
        
        # Get output directory settings
        output_dir = self.output_directory.get()
        create_subfolder = self.create_subfolder.get()
        output_folder_name = self.output_folder_name.get() if create_subfolder else ""
        
        # Start processing log queue checking if not already running
        if self.after_id is None:
            self.root.after(100, self.process_log_queue)
        
        # Determine the final output path
        if output_dir:
            if create_subfolder and output_folder_name:
                full_output_path = os.path.join(output_dir, output_folder_name)
                try:
                    if not os.path.exists(full_output_path):
                        os.makedirs(full_output_path)
                        self.log_queue.put(f"Created output directory: {full_output_path}")
                    else:
                        self.log_queue.put(f"Using existing output directory: {full_output_path}")
                except Exception as e:
                    self.log_queue.put(f"Error creating output directory: {str(e)}")
                    full_output_path = None
            else:
                # Use the output directory directly
                full_output_path = output_dir
                self.log_queue.put(f"Using output directory directly: {full_output_path}")
        else:
            full_output_path = None
            self.log_queue.put("No output directory specified, using source directory.")
                
        for file_path in files:
            try:
                self.log_queue.put(f"Processing file: {file_path}")
                
                # Get the original file directory and name
                original_dir = os.path.dirname(file_path)
                file_name = os.path.basename(file_path)
                file_base_name = os.path.splitext(file_name)[0]
                
                # Check if create_document_json function exists in the module
                if hasattr(self.processor_module, 'create_document_json'):
                    # Get the extraction params from the module if available
                    extraction_params = getattr(self.processor_module, 'extraction_params', [])
                    
                    # Save original directory to restore later
                    original_cwd = os.getcwd()
                    
                    try:
                        # If using the modified version with process_pdf_file function
                        if hasattr(self.processor_module, 'process_pdf_file'):
                            # Set up environment for processing
                            parent_dir = os.path.dirname(original_cwd)
                            os.chdir(parent_dir)
                            
                            # Call the function with the file path
                            json_path = self.processor_module.process_pdf_file(file_path)
                        else:
                            # Call the function directly with the file path
                            json_path = self.processor_module.create_document_json(file_path, extraction_params)
                            
                        # If the processing succeeded
                        if json_path:
                            # Move or copy the generated JSON file to our output directory if specified
                            if full_output_path:
                                # Get the original JSON file location
                                json_basename = os.path.basename(json_path)
                                target_json_path = os.path.join(full_output_path, json_basename)
                                
                                # If the file exists, copy it to the output directory
                                if os.path.exists(json_path):
                                    # If the output directory is different from the source directory,
                                    # copy the file and then remove the original
                                    if os.path.normpath(os.path.dirname(json_path)) != os.path.normpath(full_output_path):
                                        shutil.copy2(json_path, target_json_path)
                                        self.log_queue.put(f"Copied JSON to: {target_json_path}")
                                        
                                        # Remove the original file to avoid duplicate output
                                        os.remove(json_path)
                                        self.log_queue.put(f"Removed duplicate JSON from: {json_path}")
                                
                            self.log_queue.put(f"Successfully processed: {file_path} -> {json_path}")
                            processed_count += 1
                        else:
                            self.log_queue.put(f"Failed to process: {file_path}")
                    finally:
                        # Change back to original directory
                        os.chdir(original_cwd)
                    
                else:
                    # If we're using a module that requires different handling
                    # Here we're simulating the original Lynx_main.py behavior
                    self.log_queue.put("Using custom module processing...")
                    
                    # Save current directory to restore later
                    original_cwd = os.getcwd()
                    
                    try:
                        # Change to parent directory as in the original script
                        parent_dir = os.path.dirname(original_cwd)
                        os.chdir(parent_dir)
                        
                        # Mock the input function for non-interactive use
                        original_input = __builtins__['input']
                        __builtins__['input'] = lambda _: file_path
                        
                        # Execute the main block of the module
                        if hasattr(self.processor_module, '__name__'):
                            self.processor_module.__name__ = "__main__"
                            exec(getattr(self.processor_module, '__main__', ''), self.processor_module.__dict__)
                            
                            # Look for generated JSON file in the same directory as the PDF
                            expected_json_path = os.path.join(original_dir, file_base_name + ".json")
                            
                            # If we found the JSON file and have an output directory specified
                            if os.path.exists(expected_json_path) and full_output_path:
                                # Get the filename of the JSON
                                json_basename = os.path.basename(expected_json_path)
                                target_json_path = os.path.join(full_output_path, json_basename)
                                
                                # Copy the file to the output directory
                                if os.path.normpath(os.path.dirname(expected_json_path)) != os.path.normpath(full_output_path):
                                    shutil.copy2(expected_json_path, target_json_path)
                                    self.log_queue.put(f"Copied JSON to: {target_json_path}")
                                    
                                    # Remove the original file
                                    os.remove(expected_json_path)
                                    self.log_queue.put(f"Removed duplicate JSON from: {expected_json_path}")
                                
                            processed_count += 1
                        
                    except Exception as e:
                        self.log_queue.put(f"Error executing processor module: {str(e)}")
                    finally:
                        # Restore original input function and directory
                        __builtins__['input'] = original_input
                        os.chdir(original_cwd)
            except Exception as e:
                self.log_queue.put(f"Error processing file: {file_path}\nError: {str(e)}")
        
        self.log_queue.put(f"Completed processing. Successfully processed {processed_count} of {len(files)} files.")

    def log(self, message):
        """
        Add a message to the log text widget and ensure it's visible.
        
        Args:
            message (str): Message to log
        """
        # Ensure we can modify the text widget
        self.log_text.configure(state=tk.NORMAL)
        
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Insert the message with timestamp
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        # Auto-scroll to the end
        self.log_text.see(tk.END)
        
        # Update the GUI immediately
        self.root.update_idletasks()

    def process_log_queue(self):
        """
        Process messages from the log queue and update the log text widget.
        """
        try:
            # Get all messages from the queue without blocking
            while True:
                message = self.log_queue.get_nowait()
                self.log(message)
                self.log_queue.task_done()
        except queue.Empty:
            pass
        
        # Schedule to check the queue again
        self.after_id = self.root.after(100, self.process_log_queue)


    def start(self):
        # Start checking the log queue
        self.process_log_queue()
        self.root.mainloop()
    def toggle_subfolder_options(self):
        """Enable or disable subfolder options based on checkbox state"""
        if self.create_subfolder.get():
            self.subfolder_label.configure(state="normal")
            self.subfolder_entry.configure(state="normal")
        else:
            self.subfolder_label.configure(state="disabled")
            self.subfolder_entry.configure(state="disabled")    
    def select_all_files(self):
        """Select all files in the treeview"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
            
    def deselect_all_files(self):
        """Deselect all files in the treeview"""
        for item in self.tree.selection():
            self.tree.selection_remove(item)

if __name__ == "__main__":
    root = tk.Tk()
    app = DirectoryProcessor(root)
    app.start()