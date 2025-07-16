import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import subprocess
import threading
import queue
import os
import sys
import re
import shlex # For robust command splitting

class AircrackNGGUI:
    def __init__(self, master):
        self.master = master
        master.title("Aircrack-ng GUI")
        master.geometry("1200x900") # Increased window size
        master.resizable(True, True)
        master.grid_rowconfigure(0, weight=1) # Allow notebook to expand vertically
        master.grid_rowconfigure(1, weight=0) # Generated command frame
        master.grid_rowconfigure(2, weight=0) # Buttons frame
        master.grid_rowconfigure(3, weight=0) # Status bar
        master.grid_rowconfigure(4, weight=1) # Output frame to expand vertically
        master.grid_columnconfigure(0, weight=1) # Allow main column to expand horizontally

        self.aircrack_process = None
        self.output_queue = queue.Queue()
        self.search_start_index = "1.0" # For incremental search

        # Configure style for ttk widgets
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'

        # --- Notebook (Tabs) ---
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # --- Input File/Target Tab ---
        self.input_target_frame = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.input_target_frame, text="Input/Target")
        self._create_input_target_tab(self.input_target_frame)

        # --- Attack Options Tab ---
        self.attack_options_frame = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.attack_options_frame, text="Attack Options")
        self._create_attack_options_tab(self.attack_options_frame)

        # --- Filtering Tab ---
        self.filtering_frame = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.filtering_frame, text="Filtering")
        self._create_filtering_tab(self.filtering_frame)

        # --- Performance Tab ---
        self.performance_frame = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.performance_frame, text="Performance")
        self._create_performance_tab(self.performance_frame)

        # --- Output Tab ---
        self.output_options_frame = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.output_options_frame, text="Output")
        self._create_output_options_tab(self.output_options_frame)

        # --- Advanced Tab ---
        self.advanced_frame = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.advanced_frame, text="Advanced")
        self._create_advanced_tab(self.advanced_frame)

        # --- Generated Command ---
        self.command_frame = ttk.LabelFrame(master, text="Generated Aircrack-ng Command", padding="10 10 10 10")
        self.command_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.command_frame.grid_columnconfigure(0, weight=1)
        self.command_text = scrolledtext.ScrolledText(self.command_frame, height=3, width=80, font=("Consolas", 10), state=tk.DISABLED)
        self.command_text.grid(row=0, column=0, sticky="nsew")
        
        self.command_buttons_frame = ttk.Frame(self.command_frame)
        self.command_buttons_frame.grid(row=0, column=1, sticky="ne", padx=(10,0))
        self.copy_command_button = ttk.Button(self.command_buttons_frame, text="Copy Command", command=self.copy_command)
        self.copy_command_button.pack(pady=2)
        self.generate_command_button = ttk.Button(self.command_buttons_frame, text="Generate Command", command=self.generate_command)
        self.generate_command_button.pack(pady=2)

        # --- Buttons Frame ---
        self.button_frame = ttk.Frame(master, padding="10 0 10 5")
        self.button_frame.grid(row=2, column=0, sticky="ew")

        self.run_button = ttk.Button(self.button_frame, text="Run Aircrack-ng", command=self.run_aircrack)
        self.run_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(self.button_frame, text="Clear Output", command=self.clear_output)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.save_output_button = ttk.Button(self.button_frame, text="Save Output", command=self.save_output)
        self.save_output_button.pack(side=tk.LEFT, padx=5)

        # --- Status Bar ---
        self.status_bar = ttk.Label(master, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, sticky="ew")

        # --- Output Frame ---
        self.output_frame = ttk.LabelFrame(master, text="Aircrack-ng Output", padding="10 10 10 10")
        self.output_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.output_frame.grid_rowconfigure(1, weight=1) # Make the output_text expand vertically
        self.output_frame.grid_columnconfigure(0, weight=1) # Make the search_frame and output_text expand horizontally

        # Search functionality for output
        self.search_frame = ttk.Frame(self.output_frame)
        self.search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.search_frame.grid_columnconfigure(1, weight=1) # Make search entry expand
        ttk.Label(self.search_frame, text="Search:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.search_entry = ttk.Entry(self.search_frame, width=50)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<Return>", self.search_output) # Bind Enter key
        ttk.Button(self.search_frame, text="Search", command=self.search_output).grid(row=0, column=2, sticky="e", padx=(0, 5))
        ttk.Button(self.search_frame, text="Clear Search", command=self.clear_search_highlight).grid(row=0, column=3, sticky="e")

        self.output_text = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, bg="black", fg="white", font=("Consolas", 10), height=30)
        self.output_text.grid(row=1, column=0, sticky="nsew")
        self.output_text.config(state=tk.DISABLED) # Make it read-only

        # Configure tag for highlighting search results
        self.output_text.tag_configure("highlight", background="yellow", foreground="black")

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.master.after(100, self.process_queue) # Start checking the queue
        self.generate_command() # Generate initial command on startup

    def _create_input_field(self, parent_frame, label_text, row, entry_name, col=0, width=40, is_checkbox=False, var_name=None, help_text=None, options=None, is_dropdown=False):
        if is_checkbox:
            var = tk.BooleanVar()
            setattr(self, var_name, var)
            chk = ttk.Checkbutton(parent_frame, text=label_text, variable=var, command=self.generate_command)
            chk.grid(row=row, column=col, sticky="w", pady=2)
            if help_text:
                help_button = ttk.Button(parent_frame, text="?", width=2, command=lambda t=help_text: self._show_help_popup(t))
                help_button.grid(row=row, column=col + 1, sticky="w", padx=(5, 0))
            return chk
        elif is_dropdown and options:
            label = ttk.Label(parent_frame, text=label_text)
            label.grid(row=row, column=col, sticky="w", pady=2, padx=(0, 5))
            var = tk.StringVar()
            setattr(self, var_name, var)
            dropdown = ttk.Combobox(parent_frame, textvariable=var, values=options, state="readonly", width=width)
            dropdown.grid(row=row, column=col+1, sticky="ew", pady=2)
            dropdown.set(options[0]) # Set default value
            dropdown.bind("<<ComboboxSelected>>", lambda event: self.generate_command())
            if help_text:
                help_button = ttk.Button(parent_frame, text="?", width=2, command=lambda t=help_text: self._show_help_popup(t))
                help_button.grid(row=row, column=col + 2, sticky="w", padx=(5, 0))
            return dropdown
        else:
            label = ttk.Label(parent_frame, text=label_text)
            label.grid(row=row, column=col, sticky="w", pady=2, padx=(0, 5))
            if entry_name and ("additional_args_entry" in entry_name): # Use ScrolledText for larger inputs
                entry = scrolledtext.ScrolledText(parent_frame, height=4, width=width, font=("Consolas", 10))
            else:
                entry = ttk.Entry(parent_frame, width=width)
            
            entry.grid(row=row, column=col+1, sticky="ew", pady=2)
            setattr(self, entry_name, entry)
            entry.bind("<KeyRelease>", lambda event: self.generate_command()) # Update command on key release
            if help_text:
                help_button = ttk.Button(parent_frame, text="?", width=2, command=lambda t=help_text: self._show_help_popup(t))
                help_button.grid(row=row, column=col + 2, sticky="w", padx=(5, 0))
            return entry

    def _show_help_popup(self, help_text):
        popup = tk.Toplevel(self.master)
        popup.title("Help")
        popup.transient(self.master) # Make it appear on top of the main window
        popup.grab_set() # Disable interaction with the main window

        # Calculate position to center it relative to the main window
        main_x = self.master.winfo_x()
        main_y = self.master.winfo_y()
        main_width = self.master.winfo_width()
        main_height = self.master.winfo_height()

        popup_width = 500
        popup_height = 300
        popup_x = main_x + (main_width // 2) - (popup_width // 2)
        popup_y = main_y + (main_height // 2) - (popup_height // 2)
        popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
        popup.resizable(False, False)

        text_widget = scrolledtext.ScrolledText(popup, wrap=tk.WORD, font=("Consolas", 10), width=60, height=15)
        text_widget.pack(expand=True, fill="both", padx=10, pady=10)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        close_button = ttk.Button(popup, text="Close", command=popup.destroy)
        close_button.pack(pady=5)

    def _create_input_target_tab(self, parent_frame):
        parent_frame.grid_columnconfigure(1, weight=1)
        row = 0
        self._create_input_field(parent_frame, "Input Capture File(s) (required):", row, "capture_file_entry", width=60,
                                 help_text="Path to one or more .cap files. Example: 'capture.cap' or 'capture1.cap capture2.cap'")
        row += 1
        self._create_input_field(parent_frame, "Target BSSID (-b):", row, "bssid_entry", width=40,
                                 help_text="MAC address of the Access Point (AP) to target. Example: 00:11:22:33:44:55")
        row += 1
        self._create_input_field(parent_frame, "Target ESSID (-e):", row, "essid_entry", width=40,
                                 help_text="ESSID (network name) of the AP to target. Example: 'MyHomeWiFi'")

    def _create_attack_options_tab(self, parent_frame):
        parent_frame.grid_columnconfigure(1, weight=1)
        row = 0
        self._create_input_field(parent_frame, "Attack Mode (-a):", row, "attack_mode_entry", width=20, is_dropdown=True, var_name="attack_mode_var",
                                 options=["", "1 (WEP Brute-force)", "2 (WPA/WPA2 Dictionary)"],
                                 help_text="Select attack mode. 1 for WEP brute-force, 2 for WPA/WPA2 dictionary attack.")
        self.attack_mode_var.set("2 (WPA/WPA2 Dictionary)") # Default to dictionary attack
        row += 1
        self._create_input_field(parent_frame, "Wordlist (-w):", row, "wordlist_entry", width=60,
                                 help_text="Path to the wordlist file for dictionary attacks.")
        row += 1
        self._create_input_field(parent_frame, "Single Password (-p):", row, "single_password_entry", width=40,
                                 help_text="Test a single password.")
        row += 1
        self._create_input_field(parent_frame, "Passphrase (-E):", row, "passphrase_entry", width=40,
                                 help_text="Test a single passphrase (for WPA/WPA2).")
        row += 1
        self._create_input_field(parent_frame, "PTW Acks (-x):", row, "ptw_acks_entry", width=10,
                                 help_text="Number of PTW Acks to use (for WEP PTW attack).")
        row += 1
        self.no_dictionary_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "No Dictionary Attack (-N):", row, None, is_checkbox=True, var_name="no_dictionary_var",
                                 help_text="Disable dictionary attack (only for WEP).")
        row += 1
        self.no_ptw_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "No PTW Attack (-P):", row, None, is_checkbox=True, var_name="no_ptw_var",
                                 help_text="Disable PTW attack (only for WEP).")
        row += 1
        self.pmkid_attack_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "PMKID Attack (-J):", row, None, is_checkbox=True, var_name="pmkid_attack_var",
                                 help_text="Perform PMKID attack (for WPA/WPA2).")
        row += 1
        self.no_pmkid_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "No PMKID Attack (-M):", row, None, is_checkbox=True, var_name="no_pmkid_var",
                                 help_text="Disable PMKID attack.")

    def _create_filtering_tab(self, parent_frame):
        parent_frame.grid_columnconfigure(1, weight=1)
        row = 0
        self._create_input_field(parent_frame, "Filter by BSSID (-b):", row, "filter_bssid_entry", width=40,
                                 help_text="Filter packets by BSSID. Example: 00:11:22:33:44:55")
        row += 1
        self._create_input_field(parent_frame, "Filter by Client MAC (-c):", row, "filter_client_mac_entry", width=40,
                                 help_text="Filter packets by client MAC address. Example: AA:BB:CC:DD:EE:FF")
        row += 1
        self._create_input_field(parent_frame, "Filter by ESSID (-e):", row, "filter_essid_entry", width=40,
                                 help_text="Filter packets by ESSID. Example: 'MyHomeWiFi'")
        row += 1
        self._create_input_field(parent_frame, "Filter by Channel (-C):", row, "filter_channel_entry", width=10,
                                 help_text="Filter packets by channel. Example: 6")

    def _create_performance_tab(self, parent_frame):
        parent_frame.grid_columnconfigure(1, weight=1)
        row = 0
        self._create_input_field(parent_frame, "Number of Threads (-t):", row, "threads_entry", width=10,
                                 help_text="Number of threads to use for cracking.")
        row += 1
        self._create_input_field(parent_frame, "CPU Core Affinity (-C):", row, "cpu_affinity_entry", width=10,
                                 help_text="Set CPU core affinity (e.g., 0,1,2).")
        row += 1
        self._create_input_field(parent_frame, "Batch Size (-B):", row, "batch_size_entry", width=10,
                                 help_text="Set batch size for processing packets.")
        row += 1
        self.show_progress_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "Show Progress (--show-progress):", row, None, is_checkbox=True, var_name="show_progress_var",
                                 help_text="Show progress of the cracking process.")

    def _create_output_options_tab(self, parent_frame):
        parent_frame.grid_columnconfigure(1, weight=1)
        row = 0
        self._create_input_field(parent_frame, "Output File (-o):", row, "output_file_entry", width=60,
                                 help_text="Write cracked passwords to a file.")
        row += 1
        self.verbose_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "Verbose (-v):", row, None, is_checkbox=True, var_name="verbose_var",
                                 help_text="Show verbose output.")
        row += 1
        self.quiet_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "Quiet (-q):", row, None, is_checkbox=True, var_name="quiet_var",
                                 help_text="Suppress non-essential output.")
        row += 1
        self.no_color_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "No Color (--no-color):", row, None, is_checkbox=True, var_name="no_color_var",
                                 help_text="Disable colored output.")

    def _create_advanced_tab(self, parent_frame):
        parent_frame.grid_columnconfigure(1, weight=1)
        row = 0
        self.debug_var = tk.BooleanVar()
        self._create_input_field(parent_frame, "Debug (-D):", row, None, is_checkbox=True, var_name="debug_var",
                                 help_text="Enable debug mode.")
        row += 1
        self._create_input_field(parent_frame, "Additional Arguments:", row, "additional_args_entry", width=60,
                                 help_text="Any other Aircrack-ng arguments not covered by the GUI.")

    def generate_command(self):
        command_parts = ["aircrack-ng"]

        # Helper to add arguments if value is not empty
        def add_arg(arg_name, entry_widget, is_text_area=False):
            if is_text_area:
                value = entry_widget.get("1.0", tk.END).strip()
            else:
                value = entry_widget.get().strip()
            if value:
                command_parts.append(arg_name)
                command_parts.append(shlex.quote(value)) # Quote values to handle spaces

        # Helper to add checkbox arguments
        def add_checkbox_arg(arg_name, var_widget):
            if var_widget.get():
                command_parts.append(arg_name)

        # Helper to add dropdown arguments
        def add_dropdown_arg(arg_name, var_widget):
            value = var_widget.get().strip()
            if value:
                command_parts.append(arg_name)
                # Extract only the number for attack mode if it's in "X (Description)" format
                if arg_name == "-a":
                    mode_num = value.split(' ')[0]
                    command_parts.append(mode_num)
                else:
                    command_parts.append(shlex.quote(value))

        # Attack Options Tab
        add_dropdown_arg("-a", self.attack_mode_var)
        add_arg("-w", self.wordlist_entry)
        add_arg("-p", self.single_password_entry)
        add_arg("-E", self.passphrase_entry)
        add_arg("-x", self.ptw_acks_entry)
        add_checkbox_arg("-N", self.no_dictionary_var)
        add_checkbox_arg("-P", self.no_ptw_var)
        add_checkbox_arg("-J", self.pmkid_attack_var)
        add_checkbox_arg("-M", self.no_pmkid_var)

        # Filtering Tab
        add_arg("-b", self.filter_bssid_entry) # Overloaded, but context usually makes it clear
        add_arg("-c", self.filter_client_mac_entry) # Overloaded
        add_arg("-e", self.filter_essid_entry) # Overloaded
        add_arg("-C", self.filter_channel_entry) # Overloaded

        # Performance Tab
        add_arg("-t", self.threads_entry)
        add_arg("-C", self.cpu_affinity_entry) # Overloaded
        add_arg("-B", self.batch_size_entry)
        add_checkbox_arg("--show-progress", self.show_progress_var)

        # Output Tab
        add_arg("-o", self.output_file_entry)
        add_checkbox_arg("-v", self.verbose_var)
        add_checkbox_arg("-q", self.quiet_var)
        add_checkbox_arg("--no-color", self.no_color_var)

        # Advanced Tab
        add_checkbox_arg("-D", self.debug_var)
        
        # Additional Arguments
        additional_args = self.additional_args_entry.get("1.0", tk.END).strip()
        if additional_args:
            try:
                split_args = shlex.split(additional_args)
                command_parts.extend(split_args)
            except ValueError:
                messagebox.showwarning("Command Generation Error", "Could not parse additional arguments. Please check quotes.")
                command_parts.append(additional_args) # Fallback

        # Input Capture File(s) are always the last arguments
        capture_files_str = self.capture_file_entry.get().strip()
        if capture_files_str:
            # Allow multiple files separated by space, so use shlex.split
            files = shlex.split(capture_files_str)
            for f in files:
                command_parts.append(shlex.quote(f))
        else:
            messagebox.showwarning("Missing Input File", "Please specify at least one input capture file in the 'Input/Target' tab.")
            # Prevent command generation if essential argument is missing
            self.command_text.config(state=tk.NORMAL)
            self.command_text.delete(1.0, tk.END)
            self.command_text.insert(tk.END, "Error: Input Capture File(s) are required.")
            self.command_text.config(state=tk.DISABLED)
            return

        generated_cmd = " ".join(command_parts)
        self.command_text.config(state=tk.NORMAL)
        self.command_text.delete(1.0, tk.END)
        self.command_text.insert(tk.END, generated_cmd)
        self.command_text.config(state=tk.DISABLED)

    def copy_command(self):
        command_to_copy = self.command_text.get("1.0", tk.END).strip()
        self.master.clipboard_clear()
        self.master.clipboard_append(command_to_copy)
        messagebox.showinfo("Copy Command", "Command copied to clipboard!")

    def run_aircrack(self):
        if self.aircrack_process and self.aircrack_process.poll() is None:
            messagebox.showwarning("Aircrack-ng Running", "Aircrack-ng is already running. Please wait for it to finish or close the application.")
            return

        self.clear_output()
        self.status_bar.config(text="Aircrack-ng is running...")
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, "Starting Aircrack-ng...\n")
        self.output_text.config(state=tk.DISABLED)

        # Generate the command just before running to ensure it's up-to-date
        self.generate_command()
        command_str = self.command_text.get("1.0", tk.END).strip()
        
        # Check for error message from generate_command
        if command_str.startswith("Error:"):
            self.status_bar.config(text="Error")
            return

        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"Executing command: {command_str}\n\n")
        self.output_text.config(state=tk.DISABLED)

        # Use shlex.split to correctly handle quoted arguments for subprocess
        try:
            command = shlex.split(command_str)
        except ValueError as e:
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, f"Error parsing command: {e}\n")
            self.output_text.config(state=tk.DISABLED)
            self.status_bar.config(text="Error")
            return

        # Run aircrack-ng in a separate thread
        self.aircrack_thread = threading.Thread(target=self._run_aircrack_thread, args=(command,))
        self.aircrack_thread.daemon = True
        self.aircrack_thread.start()

    def _run_aircrack_thread(self, command):
        try:
            # Check if aircrack-ng is available in PATH
            import shutil
            if shutil.which(command[0]) is None:
                self.output_queue.put(f"Error: '{command[0]}' not found in system PATH. Please ensure aircrack-ng is installed and accessible.\n")
                self.output_queue.put("STATUS: Error\n")
                return

            self.aircrack_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1, # Line-buffered
                universal_newlines=True
            )

            # Use a separate thread for reading stdout/stderr to avoid blocking
            def read_output(pipe, output_queue):
                for line in iter(pipe.readline, ''):
                    output_queue.put(line)
                pipe.close()

            stdout_thread = threading.Thread(target=read_output, args=(self.aircrack_process.stdout, self.output_queue))
            stderr_thread = threading.Thread(target=read_output, args=(self.aircrack_process.stderr, self.output_queue))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()

            # Wait for aircrack-ng process to finish
            self.aircrack_process.wait()
            return_code = self.aircrack_process.returncode
            self.output_queue.put(f"\nAircrack-ng finished with exit code: {return_code}\n")
            self.output_queue.put(f"STATUS: {'Completed' if return_code == 0 else 'Failed'}\n")

        except FileNotFoundError:
            self.output_queue.put("Error: aircrack-ng command not found. Make sure aircrack-ng is installed and in your system's PATH.\n")
            self.output_queue.put("STATUS: Error\n")
        except Exception as e:
            self.output_queue.put(f"An error occurred: {e}\n")
            self.output_queue.put("STATUS: Error\n")
        finally:
            self.master.after(0, lambda: setattr(self, 'aircrack_process', None)) # Clear process on main thread
            self.master.after(0, lambda: self.status_bar.config(text="Ready")) # Update status bar on main thread

    def process_queue(self):
        while not self.output_queue.empty():
            try:
                line = self.output_queue.get_nowait()
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, line)
                self.output_text.see(tk.END) # Scroll to the end
                self.output_text.config(state=tk.DISABLED)
            except queue.Empty:
                pass
        
        if self.aircrack_process and self.aircrack_process.poll() is None:
            self.status_bar.config(text="Aircrack-ng is running...")
        else:
            self.status_bar.config(text="Ready")

        self.master.after(100, self.process_queue)

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.status_bar.config(text="Ready")
        self.clear_search_highlight() # Clear highlights when output is cleared

    def save_output(self):
        output_content = self.output_text.get("1.0", tk.END)
        if not output_content.strip():
            messagebox.showinfo("Save Output", "No output to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write(output_content)
                messagebox.showinfo("Save Output", f"Output saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {e}")

    def search_output(self, event=None):
        search_term = self.search_entry.get().strip()
        self.clear_search_highlight() # Clear previous highlights

        if not search_term:
            self.search_start_index = "1.0" # Reset search start
            return

        self.output_text.config(state=tk.NORMAL)
        
        # Start search from the beginning if it's a new search or no more matches from current position
        if self.search_start_index == "1.0" or not self.output_text.search(search_term, self.search_start_index, tk.END, nocase=1):
            self.search_start_index = "1.0"

        idx = self.output_text.search(search_term, self.search_start_index, tk.END, nocase=1)
        if idx:
            end_idx = f"{idx}+{len(search_term)}c"
            self.output_text.tag_add("highlight", idx, end_idx)
            self.output_text.see(idx) # Scroll to the found text
            self.search_start_index = end_idx # Set start for next search
        else:
            messagebox.showinfo("Search", f"No more occurrences of '{search_term}' found.")
            self.search_start_index = "1.0" # Reset for next search attempt

        self.output_text.config(state=tk.DISABLED)

    def clear_search_highlight(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.tag_remove("highlight", "1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.search_start_index = "1.0" # Reset search start index

    def on_closing(self):
        if self.aircrack_process and self.aircrack_process.poll() is None:
            if messagebox.askokcancel("Quit", "Aircrack-ng is still running. Do you want to terminate it and quit?"):
                self.aircrack_process.terminate()
                self.master.destroy()
        else:
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AircrackNGGUI(root)
    root.mainloop()
