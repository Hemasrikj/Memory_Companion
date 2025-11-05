import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter import font as tkfont
import threading
import time

class MemoryCompanionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" Memory Companion - Alzheimer's Care")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f4f8")

        self.connection = None
        self.current_user = None
        self.current_role = None
        self.reminder_thread = None
        self.running = True

        # Custom fonts
        self.title_font = tkfont.Font(family="Arial", size=24, weight="bold")
        self.header_font = tkfont.Font(family="Arial", size=16, weight="bold")
        self.normal_font = tkfont.Font(family="Arial", size=11)

        # Connect to database
        self.connect_db()
        self.create_tables()

        # Start with login screen
        self.show_login()

        # Start reminder checker
        self.start_reminder_thread()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def connect_db(self):
        """Connect to MySQL database (kept credentials as you confirmed)"""
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='070522',
                database='memory_companion'
            )
            print("✓ Connected to database")
        except Error as e:
            messagebox.showerror("Database Error", f"Failed to connect: {e}")

    def create_tables(self):
        """Create all necessary tables (password stored as plain `password`)"""
        try:
            cursor = self.connection.cursor()

            # Patients table (store plain password)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    age INT,
                    diagnosis VARCHAR(100),
                    stage VARCHAR(50),
                    emergency_contact VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Caregivers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caregivers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    phone VARCHAR(50),
                    relationship VARCHAR(100),
                    patient_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            """)

            # Doctors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    specialization VARCHAR(100),
                    license_number VARCHAR(100),
                    hospital VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_type ENUM('patient', 'caregiver', 'doctor') NOT NULL,
                    user_id INT NOT NULL,
                    patient_id INT,
                    entry_type ENUM('meal', 'medication', 'appointment', 'social', 'note', 'activity', 'observation') NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    entry_date DATE NOT NULL,
                    entry_time TIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            """)

            # Reminders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_type ENUM('patient', 'caregiver', 'doctor') NOT NULL,
                    user_id INT NOT NULL,
                    patient_id INT,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    reminder_date DATE NOT NULL,
                    reminder_time TIME NOT NULL,
                    reminder_type ENUM('medication', 'appointment', 'event', 'other') NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            """)

            # Consent logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consent_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    patient_id INT NOT NULL,
                    consent_type VARCHAR(100) NOT NULL,
                    consent_given BOOLEAN NOT NULL,
                    consent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            """)

            # Audit logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_type ENUM('patient', 'caregiver', 'doctor') NOT NULL,
                    user_id INT NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    details TEXT,
                    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.connection.commit()

            # Create sample data only if tables are empty
            cursor.execute("SELECT COUNT(*) FROM patients")
            if cursor.fetchone()[0] == 0:
                self.create_sample_data()

            cursor.close()
        except Error as e:
            messagebox.showerror("Database Error", f"Failed to create tables: {e}")

    def create_sample_data(self):
        """Create sample patients, caregivers, doctors — only 2 entries each — and shared appointment/reminder"""
        cursor = self.connection.cursor()

        # --- Patients (2 entries) ---
        patients = [
            ('ram_kumar', 'patient123', 'Ram Kumar', 72, "Alzheimer's Disease", 'Early Stage', '+91-9876543210'),
            ('meena_rao', 'patient456', 'Meena Rao', 68, "Vascular Dementia", 'Moderate Stage', '+91-9123456789')
        ]
        for username, password, full_name, age, diagnosis, stage, emergency in patients:
            cursor.execute(
                """INSERT INTO patients (username, password, full_name, age, diagnosis, stage, emergency_contact)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (username, password, full_name, age, diagnosis, stage, emergency)
            )

        # fetch patient ids
        cursor.execute("SELECT id FROM patients WHERE username = %s", ('ram_kumar',))
        ram_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM patients WHERE username = %s", ('meena_rao',))
        meena_id = cursor.fetchone()[0]

        # --- Caregivers (2 entries) ---
        caregivers = [
            ('sita_k', 'care123', 'Sita Kumar', '+91-9876501234', 'Wife', ram_id),
            ('raj_r', 'care456', 'Raj Rao', '+91-9123409876', 'Son', meena_id)
        ]
        for username, password, full_name, phone, relationship, patient_id in caregivers:
            cursor.execute(
                """INSERT INTO caregivers (username, password, full_name, phone, relationship, patient_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (username, password, full_name, phone, relationship, patient_id)
            )

        # fetch caregiver id for ram's caregiver
        cursor.execute("SELECT id FROM caregivers WHERE username = %s", ('sita_k',))
        sita_row = cursor.fetchone()
        sita_id = sita_row[0] if sita_row else None

        # --- Doctors (2 entries) ---
        doctors = [
            ('dr_sharma', 'doc123', 'Dr. A.K. Sharma', 'Neurology', 'MD-IN-12345', 'AIIMS Delhi'),
            ('dr_reddy', 'doc456', 'Dr. Priya Reddy', 'Psychiatry', 'MD-IN-67890', 'Apollo Chennai')
        ]
        for username, password, full_name, spec, license_no, hospital in doctors:
            cursor.execute(
                """INSERT INTO doctors (username, password, full_name, specialization, license_number, hospital)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (username, password, full_name, spec, license_no, hospital)
            )

        # fetch doctor id for dr_sharma to link appointment/reminder
        cursor.execute("SELECT id FROM doctors WHERE username = %s", ('dr_sharma',))
        dr_sharma_id = cursor.fetchone()[0]

        # --- Create a shared appointment entry and a shared reminder so it appears for patient, caregiver, doctor ---
        today = (datetime.now()).strftime('%Y-%m-%d')

        # Insert appointment entry (as doctor) only if not existing
        cursor.execute("""
            SELECT COUNT(*) FROM entries
            WHERE user_type='doctor' AND user_id=%s AND patient_id=%s AND entry_type='appointment' AND title=%s AND entry_date=%s
        """, (dr_sharma_id, ram_id, 'Follow-up with Dr. Sharma', today))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """INSERT INTO entries (user_type, user_id, patient_id, entry_type, title, description, entry_date, entry_time)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                ('doctor', dr_sharma_id, ram_id, 'appointment', 'Follow-up with Dr. Sharma',
                 'Routine Alzheimer review and medication check', today, '10:00:00')
            )

        # Add corresponding reminders for patient, caregiver, and doctor — only if not present
        shared_title = 'Doctor Appointment'
        shared_desc = 'Follow-up with Dr. Sharma at 10:00 AM'
        shared_time = '10:00:00'

        roles_and_uids = [
            ('patient', ram_id),
            ('caregiver', sita_id if sita_id else 1),
            ('doctor', dr_sharma_id)
        ]

        for role, uid in roles_and_uids:
            # uid might be None — skip if no uid
            if uid is None:
                continue
            cursor.execute("""
                SELECT COUNT(*) FROM reminders
                WHERE user_type=%s AND user_id=%s AND patient_id=%s AND title=%s AND reminder_date=%s AND reminder_time=%s
            """, (role, uid, ram_id, shared_title, today, shared_time))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""INSERT INTO reminders (user_type, user_id, patient_id, title, description, reminder_date, reminder_time, reminder_type)
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                               (role, uid, ram_id, shared_title, shared_desc, today, shared_time, 'appointment'))

        self.connection.commit()
        cursor.close()
        print("✓ Sample data (2 each) created with shared appointment & reminders")

    def log_action(self, action, details=""):
        """Log user actions to audit log"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (user_type, user_id, action, details) VALUES (%s, %s, %s, %s)",
                (self.current_role, self.current_user, action, details)
            )
            self.connection.commit()
            cursor.close()
        except Error as e:
            print(f"Error logging action: {e}")

    def clear_window(self):
        """Clear all widgets from window"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        """Display login screen without demo credentials"""
        self.clear_window()

        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f4f8")
        main_frame.pack(expand=True)

        # Login container
        login_frame = tk.Frame(main_frame, bg="white", padx=40, pady=40)
        login_frame.pack(padx=20, pady=20)

        # Title
        title = tk.Label(login_frame, text=" Memory Companion", font=self.title_font,
                         bg="white", fg="#2563eb")
        title.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        subtitle = tk.Label(login_frame, text="Alzheimer's & Dementia Care System",
                            font=self.normal_font, bg="white", fg="#64748b")
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 30))

        # Username
        tk.Label(login_frame, text="Username:", font=self.normal_font,
                 bg="white").grid(row=2, column=0, sticky="w", pady=10)
        username_entry = tk.Entry(login_frame, font=self.normal_font, width=30)
        username_entry.grid(row=2, column=1, pady=10, padx=10)

        # Password
        tk.Label(login_frame, text="Password:", font=self.normal_font,
                 bg="white").grid(row=3, column=0, sticky="w", pady=10)
        password_entry = tk.Entry(login_frame, font=self.normal_font, width=30, show="*")
        password_entry.grid(row=3, column=1, pady=10, padx=10)

        # Login button
        login_btn = tk.Button(login_frame, text="Login", font=self.header_font,
                              bg="#2563eb", fg="white", padx=30, pady=10,
                              command=lambda: self.login(username_entry.get(), password_entry.get()))
        login_btn.grid(row=4, column=0, columnspan=2, pady=20)

        # Info box (without credentials)
        info_frame = tk.Frame(login_frame, bg="#eff6ff", padx=15, pady=15)
        info_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

        tk.Label(info_frame, text="Welcome!", font=("Arial", 10, "bold"),
                 bg="#eff6ff", fg="#1e40af").pack()
        tk.Label(info_frame, text="Please enter your credentials to access the system",
                 font=("Arial", 9), bg="#eff6ff").pack()
        tk.Label(info_frame, text="Passwords start with: patient/care/doc",
                 font=("Arial", 9), bg="#eff6ff", fg="#64748b").pack(pady=5)

        # Bind Enter key
        password_entry.bind('<Return>', lambda e: self.login(username_entry.get(), password_entry.get()))
        username_entry.focus()

    def login(self, username, password):
        """Authenticate user from appropriate table — compare plain password values"""
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return

        try:
            cursor = self.connection.cursor()

            # Try patients table
            cursor.execute(
                "SELECT id, full_name FROM patients WHERE username = %s AND password = %s",
                (username, password)
            )
            result = cursor.fetchone()
            if result:
                self.current_user = result[0]
                self.current_role = 'patient'
                self.log_action("LOGIN", f"Patient {username} logged in")
                messagebox.showinfo("Success", f"Welcome, {result[1]}!")
                cursor.close()
                self.show_dashboard()
                return

            # Try caregivers table
            cursor.execute(
                "SELECT id, full_name FROM caregivers WHERE username = %s AND password = %s",
                (username, password)
            )
            result = cursor.fetchone()
            if result:
                self.current_user = result[0]
                self.current_role = 'caregiver'
                self.log_action("LOGIN", f"Caregiver {username} logged in")
                messagebox.showinfo("Success", f"Welcome, {result[1]}!")
                cursor.close()
                self.show_dashboard()
                return

            # Try doctors table
            cursor.execute(
                "SELECT id, full_name FROM doctors WHERE username = %s AND password = %s",
                (username, password)
            )
            result = cursor.fetchone()
            if result:
                self.current_user = result[0]
                self.current_role = 'doctor'
                self.log_action("LOGIN", f"Doctor {username} logged in")
                messagebox.showinfo("Success", f"Welcome, {result[1]}!")
                cursor.close()
                self.show_dashboard()
                return

            cursor.close()
            messagebox.showerror("Error", "Invalid username or password")
        except Error as e:
            messagebox.showerror("Error", f"Login failed: {e}")

    def show_dashboard(self):
        """Display main dashboard"""
        self.clear_window()

        # Header
        header = tk.Frame(self.root, bg="#2563eb", height=80)
        header.pack(fill=tk.X)

        tk.Label(header, text=" Memory Companion", font=self.title_font,
                 bg="#2563eb", fg="white").pack(side=tk.LEFT, padx=20, pady=20)

        role_label = tk.Label(header, text=f"Role: {self.current_role.upper()}",
                              font=self.normal_font, bg="#2563eb", fg="#bfdbfe")
        role_label.pack(side=tk.LEFT, padx=10)

        logout_btn = tk.Button(header, text="Logout", font=self.normal_font,
                              bg="#dc2626", fg="white", padx=20, pady=5,
                              command=self.logout)
        logout_btn.pack(side=tk.RIGHT, padx=20, pady=20)

        # Main container
        container = tk.Frame(self.root, bg="#f0f4f8")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Left sidebar
        sidebar = tk.Frame(container, bg="white", width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="MENU", font=self.header_font,
                 bg="white", fg="#1e293b").pack(pady=20)

        menu_items = [
            ("📝 Add Entry", self.show_entries),
            ("⏰ Reminders", self.show_reminders),
            ("📊 Summaries", self.show_summaries),
            ("🔍 View All Entries", self.view_all_entries),
        ]

        if self.current_role in ['caregiver', 'doctor']:
            menu_items.append(("👤 Patient Info", self.show_patient_info))

        # Add "Add New User" for doctors (simple form in same window)
        if self.current_role == 'doctor':
            menu_items.append(("➕ Add New User", self.add_user_form))
            menu_items.append(("📋 Audit Logs", self.show_audit_logs))

        for text, command in menu_items:
            btn = tk.Button(sidebar, text=text, font=self.normal_font,
                            bg="#f1f5f9", fg="#1e293b", width=25, pady=10,
                            anchor="w", padx=20, command=command)
            btn.pack(pady=5, padx=10, fill=tk.X)

        # Right content area
        self.content_frame = tk.Frame(container, bg="white")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Show welcome message
        self.show_welcome()

    def show_welcome(self):
        """Show welcome screen in content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        welcome_frame = tk.Frame(self.content_frame, bg="white")
        welcome_frame.pack(expand=True)

        tk.Label(welcome_frame, text="👋 Welcome!", font=self.title_font,
                 bg="white", fg="#2563eb").pack(pady=20)

        tk.Label(welcome_frame, text="Select an option from the menu to get started",
                 font=self.normal_font, bg="white", fg="#64748b").pack()

        # Quick stats
        stats_frame = tk.Frame(welcome_frame, bg="white")
        stats_frame.pack(pady=30)

        try:
            cursor = self.connection.cursor()

            # Get appropriate patient_id for queries
            if self.current_role == 'patient':
                patient_id = self.current_user
            elif self.current_role == 'caregiver':
                cursor.execute("SELECT patient_id FROM caregivers WHERE id = %s", (self.current_user,))
                result = cursor.fetchone()
                patient_id = result[0] if result else None
            else:
                patient_id = None

            if patient_id:
                # Today's entries
                cursor.execute(
                    "SELECT COUNT(*) FROM entries WHERE patient_id = %s AND entry_date = CURDATE()",
                    (patient_id,)
                )
                today_count = cursor.fetchone()[0]

                # Active reminders
                cursor.execute(
                    "SELECT COUNT(*) FROM reminders WHERE patient_id = %s AND is_active = TRUE AND is_completed = FALSE",
                    (patient_id,)
                )
                reminder_count = cursor.fetchone()[0]

                # Display stats
                self.create_stat_card(stats_frame, "Today's Entries", today_count, "#10b981", 0)
                self.create_stat_card(stats_frame, "Active Reminders", reminder_count, "#f59e0b", 1)

            cursor.close()
        except Error as e:
            print(f"Error loading stats: {e}")

    def create_stat_card(self, parent, title, value, color, column):
        """Create a statistics card"""
        card = tk.Frame(parent, bg=color, padx=30, pady=20)
        card.grid(row=0, column=column, padx=15)

        tk.Label(card, text=str(value), font=("Arial", 36, "bold"),
                 bg=color, fg="white").pack()
        tk.Label(card, text=title, font=self.normal_font,
                 bg=color, fg="white").pack()

    def show_entries(self):
        """Show add entry form - supports free text entry"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        form_frame = tk.Frame(self.content_frame, bg="white", padx=30, pady=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(form_frame, text="Add New Entry", font=self.header_font,
                 bg="white", fg="#1e293b").grid(row=0, column=0, columnspan=2, pady=20, sticky="w")

        # Entry type
        tk.Label(form_frame, text="Type:", font=self.normal_font, bg="white").grid(row=1, column=0, sticky="w", pady=10)
        entry_type = ttk.Combobox(form_frame, font=self.normal_font, width=28, state="readonly")

        if self.current_role == 'patient':
            entry_type['values'] = ('meal', 'medication', 'appointment', 'social', 'note', 'activity')
        elif self.current_role == 'caregiver':
            entry_type['values'] = ('meal', 'medication', 'appointment', 'social', 'note', 'activity', 'observation')
        else:  # doctor
            entry_type['values'] = ('appointment', 'note', 'observation', 'medication')

        entry_type.current(0)
        entry_type.grid(row=1, column=1, pady=10, sticky="w")

        # Title
        tk.Label(form_frame, text="Title:", font=self.normal_font, bg="white").grid(row=2, column=0, sticky="w", pady=10)
        title_entry = tk.Entry(form_frame, font=self.normal_font, width=30)
        title_entry.grid(row=2, column=1, pady=10, sticky="w")

        # Description - FREE TEXT ENTRY
        tk.Label(form_frame, text="Description:", font=self.normal_font, bg="white").grid(row=3, column=0, sticky="nw", pady=10)
        desc_text = scrolledtext.ScrolledText(form_frame, font=self.normal_font, width=40, height=8, wrap=tk.WORD)
        desc_text.grid(row=3, column=1, pady=10, sticky="w")

        # Date
        tk.Label(form_frame, text="Date:", font=self.normal_font, bg="white").grid(row=4, column=0, sticky="w", pady=10)
        date_entry = tk.Entry(form_frame, font=self.normal_font, width=30)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        date_entry.grid(row=4, column=1, pady=10, sticky="w")

        # Time
        tk.Label(form_frame, text="Time:", font=self.normal_font, bg="white").grid(row=5, column=0, sticky="w", pady=10)
        time_entry = tk.Entry(form_frame, font=self.normal_font, width=30)
        time_entry.insert(0, datetime.now().strftime('%H:%M'))
        time_entry.grid(row=5, column=1, pady=10, sticky="w")

        # Helper text
        helper_frame = tk.Frame(form_frame, bg="#eff6ff", padx=15, pady=10)
        helper_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

        tk.Label(helper_frame, text="💡 Tip: Write freely in the description - include as much detail as you'd like!",
                 font=("Arial", 9), bg="#eff6ff", fg="#1e40af", wraplength=500, justify=tk.LEFT).pack()

        # Save button
        save_btn = tk.Button(form_frame, text="Save Entry", font=self.normal_font,
                             bg="#10b981", fg="white", padx=30, pady=10,
                             command=lambda: self.save_entry(
                                 entry_type.get(), title_entry.get(),
                                 desc_text.get("1.0", tk.END).strip(),
                                 date_entry.get(), time_entry.get()
                             ))
        save_btn.grid(row=7, column=0, columnspan=2, pady=20)

    def save_entry(self, entry_type, title, description, date, time):
        """Save a new entry"""
        if not title or not date or not time:
            messagebox.showerror("Error", "Please fill in title, date, and time")
            return

        try:
            cursor = self.connection.cursor()

            # Determine patient_id based on user role
            if self.current_role == 'patient':
                patient_id = self.current_user
            elif self.current_role == 'caregiver':
                cursor.execute("SELECT patient_id FROM caregivers WHERE id = %s", (self.current_user,))
                patient_id = cursor.fetchone()[0]
            else:  # doctor
                # For doctors, let them select patient or use first patient for now
                cursor.execute("SELECT id FROM patients LIMIT 1")
                p = cursor.fetchone()
                patient_id = p[0] if p else None

            cursor.execute(
                """INSERT INTO entries (user_type, user_id, patient_id, entry_type, title, description, entry_date, entry_time)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (self.current_role, self.current_user, patient_id, entry_type, title, description, date, time)
            )
            self.connection.commit()
            cursor.close()

            self.log_action("ADD_ENTRY", f"Added {entry_type} entry: {title}")
            messagebox.showinfo("Success", "Entry saved successfully!")
            self.show_entries()  # Refresh form
        except Error as e:
            messagebox.showerror("Error", f"Failed to save entry: {e}")

    def show_reminders(self):
        """Show reminders interface"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.content_frame, bg="white", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with add button
        header_frame = tk.Frame(main_frame, bg="white")
        header_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(header_frame, text="Reminders", font=self.header_font,
                 bg="white", fg="#1e293b").pack(side=tk.LEFT)

        add_btn = tk.Button(header_frame, text="+ Add Reminder", font=self.normal_font,
                            bg="#2563eb", fg="white", padx=15, pady=5,
                            command=self.show_add_reminder)
        add_btn.pack(side=tk.RIGHT)

        # Reminders list
        list_frame = tk.Frame(main_frame, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Create scrollable canvas
        canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load reminders
        try:
            cursor = self.connection.cursor()

            # Get patient_id based on role
            if self.current_role == 'patient':
                patient_id = self.current_user
            elif self.current_role == 'caregiver':
                cursor.execute("SELECT patient_id FROM caregivers WHERE id = %s", (self.current_user,))
                result = cursor.fetchone()
                patient_id = result[0] if result else None
            else:
                patient_id = None

            if patient_id:
                cursor.execute(
                    """SELECT id, title, description, reminder_date, reminder_time, reminder_type, is_completed
                       FROM reminders WHERE patient_id = %s AND is_active = TRUE
                       ORDER BY reminder_date, reminder_time""",
                    (patient_id,)
                )
            else:
                cursor.execute(
                    """SELECT id, title, description, reminder_date, reminder_time, reminder_type, is_completed
                       FROM reminders WHERE user_type = %s AND user_id = %s AND is_active = TRUE
                       ORDER BY reminder_date, reminder_time""",
                    (self.current_role, self.current_user)
                )

            reminders = cursor.fetchall()
            cursor.close()

            if not reminders:
                tk.Label(scrollable_frame, text="No active reminders", font=self.normal_font,
                         bg="white", fg="#64748b").pack(pady=50)
            else:
                for reminder in reminders:
                    self.create_reminder_card(scrollable_frame, reminder)
        except Error as e:
            messagebox.showerror("Error", f"Failed to load reminders: {e}")

    def create_reminder_card(self, parent, reminder):
        """Create a reminder display card"""
        reminder_id, title, description, date, time, r_type, is_completed = reminder

        card = tk.Frame(parent, bg="#f8fafc", relief=tk.RAISED, borderwidth=1)
        card.pack(fill=tk.X, pady=5, padx=5)

        # Left side - content
        content_frame = tk.Frame(card, bg="#f8fafc")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Title and type
        title_frame = tk.Frame(content_frame, bg="#f8fafc")
        title_frame.pack(fill=tk.X)

        tk.Label(title_frame, text=title, font=("Arial", 12, "bold"),
                 bg="#f8fafc", fg="#1e293b").pack(side=tk.LEFT)

        type_colors = {
            'medication': '#3b82f6',
            'appointment': '#8b5cf6',
            'event': '#10b981',
            'other': '#64748b'
        }

        type_label = tk.Label(title_frame, text=r_type.upper(), font=("Arial", 8),
                              bg=type_colors.get(r_type, '#64748b'), fg="white", padx=8, pady=2)
        type_label.pack(side=tk.LEFT, padx=10)

        # Description
        if description:
            tk.Label(content_frame, text=description, font=("Arial", 10),
                     bg="#f8fafc", fg="#64748b", wraplength=400, justify=tk.LEFT).pack(anchor="w", pady=5)

        # Date and time
        datetime_text = f"📅 {date} ⏰ {time}"
        tk.Label(content_frame, text=datetime_text, font=("Arial", 10),
                 bg="#f8fafc", fg="#64748b").pack(anchor="w")

        # Right side - actions
        action_frame = tk.Frame(card, bg="#f8fafc")
        action_frame.pack(side=tk.RIGHT, padx=15, pady=10)

        if not is_completed:
            complete_btn = tk.Button(action_frame, text="✓ Complete", font=("Arial", 9),
                                     bg="#10b981", fg="white", padx=10, pady=5,
                                     command=lambda: self.complete_reminder(reminder_id))
            complete_btn.pack(pady=2)
        else:
            tk.Label(action_frame, text="✓ Completed", font=("Arial", 9),
                     bg="#10b981", fg="white", padx=10, pady=5).pack(pady=2)

        delete_btn = tk.Button(action_frame, text="✗ Delete", font=("Arial", 9),
                               bg="#ef4444", fg="white", padx=10, pady=5,
                               command=lambda: self.delete_reminder(reminder_id))
        delete_btn.pack(pady=2)

    def show_add_reminder(self):
        """Show add reminder dialog with free text"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Reminder")
        dialog.geometry("500x550")
        dialog.configure(bg="white")
        dialog.transient(self.root)
        dialog.grab_set()

        form_frame = tk.Frame(dialog, bg="white", padx=30, pady=20)
        form_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(form_frame, text="New Reminder", font=self.header_font,
                 bg="white", fg="#1e293b").grid(row=0, column=0, columnspan=2, pady=20, sticky="w")

        # Type
        tk.Label(form_frame, text="Type:", font=self.normal_font, bg="white").grid(row=1, column=0, sticky="w", pady=10)
        r_type = ttk.Combobox(form_frame, font=self.normal_font, width=28, state="readonly")
        r_type['values'] = ('medication', 'appointment', 'event', 'other')
        r_type.current(0)
        r_type.grid(row=1, column=1, pady=10, sticky="w")

        # Title
        tk.Label(form_frame, text="Title:", font=self.normal_font, bg="white").grid(row=2, column=0, sticky="w", pady=10)
        title_entry = tk.Entry(form_frame, font=self.normal_font, width=30)
        title_entry.grid(row=2, column=1, pady=10, sticky="w")

        # Description - FREE TEXT
        tk.Label(form_frame, text="Description:", font=self.normal_font, bg="white").grid(row=3, column=0, sticky="nw", pady=10)
        desc_text = scrolledtext.ScrolledText(form_frame, font=self.normal_font, width=30, height=6, wrap=tk.WORD)
        desc_text.grid(row=3, column=1, pady=10, sticky="w")

        # Date
        tk.Label(form_frame, text="Date:", font=self.normal_font, bg="white").grid(row=4, column=0, sticky="w", pady=10)
        date_entry = tk.Entry(form_frame, font=self.normal_font, width=30)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        date_entry.grid(row=4, column=1, pady=10, sticky="w")

        # Time
        tk.Label(form_frame, text="Time:", font=self.normal_font, bg="white").grid(row=5, column=0, sticky="w", pady=10)
        time_entry = tk.Entry(form_frame, font=self.normal_font, width=30)
        time_entry.insert(0, datetime.now().strftime('%H:%M'))
        time_entry.grid(row=5, column=1, pady=10, sticky="w")

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)

        save_btn = tk.Button(btn_frame, text="Save", font=self.normal_font,
                             bg="#10b981", fg="white", padx=30, pady=10,
                             command=lambda: self.save_reminder(
                                 r_type.get(), title_entry.get(),
                                 desc_text.get("1.0", tk.END).strip(),
                                 date_entry.get(), time_entry.get(), dialog
                             ))
        save_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(btn_frame, text="Cancel", font=self.normal_font,
                               bg="#64748b", fg="white", padx=30, pady=10,
                               command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def save_reminder(self, r_type, title, description, date, time, dialog):
        """Save a new reminder"""
        if not title or not date or not time:
            messagebox.showerror("Error", "Please fill in title, date, and time")
            return

        try:
            cursor = self.connection.cursor()

            # Determine patient_id based on role
            if self.current_role == 'patient':
                patient_id = self.current_user
            elif self.current_role == 'caregiver':
                cursor.execute("SELECT patient_id FROM caregivers WHERE id = %s", (self.current_user,))
                patient_id = cursor.fetchone()[0]
            else:  # doctor
                cursor.execute("SELECT id FROM patients LIMIT 1")
                p = cursor.fetchone()
                patient_id = p[0] if p else None

            cursor.execute(
                """INSERT INTO reminders (user_type, user_id, patient_id, title, description, reminder_date, reminder_time, reminder_type)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (self.current_role, self.current_user, patient_id, title, description, date, time, r_type)
            )
            self.connection.commit()
            cursor.close()

            self.log_action("ADD_REMINDER", f"Added {r_type} reminder: {title}")
            messagebox.showinfo("Success", "Reminder saved successfully!")
            dialog.destroy()
            self.show_reminders()
        except Error as e:
            messagebox.showerror("Error", f"Failed to save reminder: {e}")

    def complete_reminder(self, reminder_id):
        """Mark reminder as completed"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE reminders SET is_completed = TRUE WHERE id = %s",
                (reminder_id,)
            )
            self.connection.commit()
            cursor.close()

            self.log_action("COMPLETE_REMINDER", f"Completed reminder ID: {reminder_id}")
            self.show_reminders()
        except Error as e:
            messagebox.showerror("Error", f"Failed to complete reminder: {e}")

    def delete_reminder(self, reminder_id):
        """Delete a reminder"""
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this reminder?"):
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "UPDATE reminders SET is_active = FALSE WHERE id = %s",
                    (reminder_id,)
                )
                self.connection.commit()
                cursor.close()

                self.log_action("DELETE_REMINDER", f"Deleted reminder ID: {reminder_id}")
                self.show_reminders()
            except Error as e:
                messagebox.showerror("Error", f"Failed to delete reminder: {e}")

    def show_summaries(self):
        """Show summaries interface"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.content_frame, bg="white", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Activity Summaries", font=self.header_font,
                 bg="white", fg="#1e293b").pack(pady=(0, 20))

        # Period selector
        period_frame = tk.Frame(main_frame, bg="white")
        period_frame.pack(pady=10)

        tk.Label(period_frame, text="Select Period:", font=self.normal_font,
                 bg="white").pack(side=tk.LEFT, padx=10)

        period_var = tk.StringVar(value="daily")

        for text, value in [("Daily", "daily"), ("Weekly", "weekly"), ("Monthly", "monthly")]:
            rb = tk.Radiobutton(period_frame, text=text, variable=period_var, value=value,
                                font=self.normal_font, bg="white",
                                command=lambda: self.generate_summary(summary_frame, period_var.get()))
            rb.pack(side=tk.LEFT, padx=5)

        # Summary display area
        summary_frame = tk.Frame(main_frame, bg="white")
        summary_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        # Generate initial summary
        self.generate_summary(summary_frame, "daily")

    def generate_summary(self, parent, period):
        """Generate and display summary"""
        for widget in parent.winfo_children():
            widget.destroy()

        try:
            cursor = self.connection.cursor()

            # Get patient_id based on role
            if self.current_role == 'patient':
                patient_id = self.current_user
            elif self.current_role == 'caregiver':
                cursor.execute("SELECT patient_id FROM caregivers WHERE id = %s", (self.current_user,))
                result = cursor.fetchone()
                patient_id = result[0] if result else None
            else:
                cursor.execute("SELECT id FROM patients LIMIT 1")
                result = cursor.fetchone()
                patient_id = result[0] if result else None

            if not patient_id:
                tk.Label(parent, text="No patient data available", font=self.normal_font,
                         bg="white", fg="#64748b").pack(pady=50)
                cursor.close()
                return

            # Determine date range
            if period == 'daily':
                date_filter = datetime.now().date()
                query = """SELECT entry_type, COUNT(*) FROM entries
                           WHERE patient_id = %s AND entry_date = %s
                           GROUP BY entry_type"""
                cursor.execute(query, (patient_id, date_filter))
                time_label = f"Today ({date_filter})"
            elif period == 'weekly':
                date_filter = (datetime.now() - timedelta(days=7)).date()
                query = """SELECT entry_type, COUNT(*) FROM entries
                           WHERE patient_id = %s AND entry_date >= %s
                           GROUP BY entry_type"""
                cursor.execute(query, (patient_id, date_filter))
                time_label = "Last 7 Days"
            else:  # monthly
                date_filter = (datetime.now() - timedelta(days=30)).date()
                query = """SELECT entry_type, COUNT(*) FROM entries
                           WHERE patient_id = %s AND entry_date >= %s
                           GROUP BY entry_type"""
                cursor.execute(query, (patient_id, date_filter))
                time_label = "Last 30 Days"

            results = cursor.fetchall()

            # Display header
            tk.Label(parent, text=f"Summary for: {time_label}", font=("Arial", 14, "bold"),
                     bg="white", fg="#2563eb").pack(pady=20)

            if not results:
                tk.Label(parent, text="No entries found for this period", font=self.normal_font,
                         bg="white", fg="#64748b").pack(pady=50)
            else:
                # Statistics grid
                stats_frame = tk.Frame(parent, bg="white")
                stats_frame.pack(pady=20)

                total = sum(count for _, count in results)

                # Total entries card
                total_card = tk.Frame(stats_frame, bg="#3b82f6", padx=30, pady=20)
                total_card.grid(row=0, column=0, padx=10, pady=10)

                tk.Label(total_card, text=str(total), font=("Arial", 36, "bold"),
                         bg="#3b82f6", fg="white").pack()
                tk.Label(total_card, text="Total Entries", font=self.normal_font,
                         bg="#3b82f6", fg="white").pack()

                # Breakdown by type
                colors = {
                    'meal': '#10b981',
                    'medication': '#3b82f6',
                    'appointment': '#8b5cf6',
                    'social': '#f59e0b',
                    'note': '#64748b',
                    'activity': '#ec4899',
                    'observation': '#06b6d4'
                }

                col = 1
                for entry_type, count in results:
                    card = tk.Frame(stats_frame, bg=colors.get(entry_type, '#64748b'),
                                    padx=20, pady=15)
                    card.grid(row=0, column=col, padx=10, pady=10)

                    tk.Label(card, text=str(count), font=("Arial", 28, "bold"),
                             bg=colors.get(entry_type, '#64748b'), fg="white").pack()
                    tk.Label(card, text=entry_type.capitalize(), font=("Arial", 10),
                             bg=colors.get(entry_type, '#64748b'), fg="white").pack()
                    col += 1

                # Recent activities
                tk.Label(parent, text="Recent Activities", font=("Arial", 12, "bold"),
                         bg="white", fg="#1e293b").pack(pady=(30, 10))

                if period == 'daily':
                    cursor.execute(
                        """SELECT title, entry_type, entry_time, description FROM entries
                           WHERE patient_id = %s AND entry_date = %s
                           ORDER BY entry_time DESC LIMIT 5""",
                        (patient_id, date_filter)
                    )
                else:
                    cursor.execute(
                        """SELECT title, entry_type, entry_date, entry_time, description FROM entries
                           WHERE patient_id = %s AND entry_date >= %s
                           ORDER BY entry_date DESC, entry_time DESC LIMIT 5""",
                        (patient_id, date_filter)
                    )

                recent = cursor.fetchall()

                if recent:
                    recent_frame = tk.Frame(parent, bg="#f8fafc", relief=tk.RAISED, borderwidth=1)
                    recent_frame.pack(fill=tk.BOTH, padx=20, pady=10)

                    for item in recent:
                        item_frame = tk.Frame(recent_frame, bg="white", pady=8)
                        item_frame.pack(fill=tk.X, padx=10, pady=3)

                        if len(item) == 4:  # daily
                            title, entry_type, entry_time, description = item
                            text = f"• {title} ({entry_type}) - {entry_time}"
                        else:  # weekly/monthly
                            title, entry_type, entry_date, entry_time, description = item
                            text = f"• {title} ({entry_type}) - {entry_date} {entry_time}"

                        tk.Label(item_frame, text=text, font=("Arial", 10, "bold"),
                                 bg="white", fg="#1e293b", anchor="w").pack(fill=tk.X, padx=10)

                        if description and len(description) > 0:
                            desc_preview = description[:100] + "..." if len(description) > 100 else description
                            tk.Label(item_frame, text=desc_preview, font=("Arial", 9),
                                     bg="white", fg="#64748b", anchor="w", wraplength=500, justify=tk.LEFT).pack(fill=tk.X, padx=25)

                # AI Summary
                tk.Label(parent, text="AI Summary", font=("Arial", 12, "bold"),
                         bg="white", fg="#1e293b").pack(pady=(30, 10))

                ai_frame = tk.Frame(parent, bg="#eff6ff", relief=tk.RAISED, borderwidth=1)
                ai_frame.pack(fill=tk.BOTH, padx=20, pady=10)

                summary_text = self.generate_ai_summary(results, total, period)
                tk.Label(ai_frame, text=summary_text, font=("Arial", 10),
                         bg="#eff6ff", fg="#1e40af", wraplength=600, justify=tk.LEFT).pack(padx=20, pady=20)

            cursor.close()
        except Error as e:
            messagebox.showerror("Error", f"Failed to generate summary: {e}")

    def generate_ai_summary(self, results, total, period):
        """Generate AI-like summary text"""
        period_text = {"daily": "today", "weekly": "this week", "monthly": "this month"}[period]

        summary = f"You had {total} activities logged {period_text}. "

        if results:
            type_dict = {entry_type: count for entry_type, count in results}

            if 'medication' in type_dict:
                summary += f"Great job tracking {type_dict['medication']} medication entries! "

            if 'social' in type_dict:
                summary += f"You engaged in {type_dict['social']} social activities, which is excellent for cognitive health. "

            if 'activity' in type_dict or 'meal' in type_dict:
                summary += "Maintaining daily routines is important for memory care. "

            if 'observation' in type_dict:
                summary += f"Caregivers logged {type_dict['observation']} observations, showing active monitoring. "

            summary += "Keep up the consistent logging!"
        else:
            summary = f"No activities were logged {period_text}. Try to log daily activities to track progress."

        return summary

    def view_all_entries(self):
        """View all entries in a scrollable list"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.content_frame, bg="white", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="All Entries", font=self.header_font,
                 bg="white", fg="#1e293b").pack(pady=(0, 20))

        # Search/Filter frame
        filter_frame = tk.Frame(main_frame, bg="white")
        filter_frame.pack(fill=tk.X, pady=10)

        tk.Label(filter_frame, text="Filter by type:", font=self.normal_font,
                 bg="white").pack(side=tk.LEFT, padx=10)

        filter_var = tk.StringVar(value="all")

        filter_combo = ttk.Combobox(filter_frame, textvariable=filter_var,
                                   font=self.normal_font, width=15, state="readonly")
        filter_combo['values'] = ('all', 'meal', 'medication', 'appointment', 'social', 'note', 'activity', 'observation')
        filter_combo.pack(side=tk.LEFT, padx=5)

        refresh_btn = tk.Button(filter_frame, text="🔄 Refresh", font=self.normal_font,
                               bg="#2563eb", fg="white", padx=15, pady=5,
                               command=lambda: self.load_entries(list_frame, filter_var.get()))
        refresh_btn.pack(side=tk.LEFT, padx=10)

        # Entries list with scrollbar
        list_container = tk.Frame(main_frame, bg="white")
        list_container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        list_frame = tk.Frame(canvas, bg="white")

        list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load entries
        self.load_entries(list_frame, "all")

        # Bind filter change
        filter_combo.bind('<<ComboboxSelected>>',
                          lambda e: self.load_entries(list_frame, filter_var.get()))

    def load_entries(self, parent, filter_type):
        """Load and display entries"""
        for widget in parent.winfo_children():
            widget.destroy()

        try:
            cursor = self.connection.cursor()

            # Get patient_id based on role
            if self.current_role == 'patient':
                patient_id = self.current_user
            elif self.current_role == 'caregiver':
                cursor.execute("SELECT patient_id FROM caregivers WHERE id = %s", (self.current_user,))
                result = cursor.fetchone()
                patient_id = result[0] if result else None
            else:  # doctor - show all patients
                patient_id = None

            if patient_id:
                if filter_type == 'all':
                    cursor.execute(
                        """SELECT id, entry_type, title, description, entry_date, entry_time, user_type
                           FROM entries WHERE patient_id = %s
                           ORDER BY entry_date DESC, entry_time DESC""",
                        (patient_id,)
                    )
                else:
                    cursor.execute(
                        """SELECT id, entry_type, title, description, entry_date, entry_time, user_type
                           FROM entries WHERE patient_id = %s AND entry_type = %s
                           ORDER BY entry_date DESC, entry_time DESC""",
                        (patient_id, filter_type)
                    )
            else:
                # Doctor view - show recent entries from all patients
                if filter_type == 'all':
                    cursor.execute(
                        """SELECT id, entry_type, title, description, entry_date, entry_time, user_type
                           FROM entries
                           ORDER BY entry_date DESC, entry_time DESC LIMIT 50"""
                    )
                else:
                    cursor.execute(
                        """SELECT id, entry_type, title, description, entry_date, entry_time, user_type
                           FROM entries WHERE entry_type = %s
                           ORDER BY entry_date DESC, entry_time DESC LIMIT 50""",
                        (filter_type,)
                    )

            entries = cursor.fetchall()
            cursor.close()

            if not entries:
                tk.Label(parent, text="No entries found", font=self.normal_font,
                         bg="white", fg="#64748b").pack(pady=50)
            else:
                for entry in entries:
                    self.create_entry_card(parent, entry)
        except Error as e:
            messagebox.showerror("Error", f"Failed to load entries: {e}")

    def create_entry_card(self, parent, entry):
        """Create an entry display card with free text visible"""
        entry_id, entry_type, title, description, date, time, user_type = entry

        card = tk.Frame(parent, bg="#f8fafc", relief=tk.RAISED, borderwidth=1)
        card.pack(fill=tk.X, pady=5, padx=5)

        content_frame = tk.Frame(card, bg="#f8fafc")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Title and type
        title_frame = tk.Frame(content_frame, bg="#f8fafc")
        title_frame.pack(fill=tk.X)

        tk.Label(title_frame, text=title, font=("Arial", 12, "bold"),
                 bg="#f8fafc", fg="#1e293b").pack(side=tk.LEFT)

        colors = {
            'meal': '#10b981', 'medication': '#3b82f6', 'appointment': '#8b5cf6',
            'social': '#f59e0b', 'note': '#64748b', 'activity': '#ec4899',
            'observation': '#06b6d4'
        }

        type_label = tk.Label(title_frame, text=entry_type.upper(), font=("Arial", 8),
                              bg=colors.get(entry_type, '#64748b'), fg="white", padx=8, pady=2)
        type_label.pack(side=tk.LEFT, padx=10)

        # User type badge
        user_badge = tk.Label(title_frame, text=f"by {user_type}", font=("Arial", 8),
                              bg="#e0e7ff", fg="#4338ca", padx=8, pady=2)
        user_badge.pack(side=tk.LEFT, padx=5)

        # Description - SHOW FULL FREE TEXT
        if description:
            desc_frame = tk.Frame(content_frame, bg="white", relief=tk.SOLID, borderwidth=1)
            desc_frame.pack(fill=tk.X, pady=8)

            tk.Label(desc_frame, text=description, font=("Arial", 10),
                     bg="white", fg="#1e293b", wraplength=600, justify=tk.LEFT,
                     anchor="w", padx=10, pady=8).pack(fill=tk.X)

        # Date and time
        datetime_text = f"📅 {date} ⏰ {time}"
        tk.Label(content_frame, text=datetime_text, font=("Arial", 10),
                 bg="#f8fafc", fg="#64748b").pack(anchor="w")

        # Delete button
        if self.current_role in ['patient', 'caregiver']:
            delete_btn = tk.Button(card, text="✗", font=("Arial", 12),
                                   bg="#ef4444", fg="white", padx=10, pady=5,
                                   command=lambda: self.delete_entry(entry_id, parent))
            delete_btn.pack(side=tk.RIGHT, padx=10)

    def delete_entry(self, entry_id, parent):
        """Delete an entry"""
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this entry?"):
            try:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
                self.connection.commit()
                cursor.close()

                self.log_action("DELETE_ENTRY", f"Deleted entry ID: {entry_id}")
                self.load_entries(parent, "all")
            except Error as e:
                messagebox.showerror("Error", f"Failed to delete entry: {e}")

    def show_patient_info(self):
        """Show patient information (caregiver/clinician only)"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.content_frame, bg="white", padx=30, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Patient Information", font=self.header_font,
                 bg="white", fg="#1e293b").pack(pady=(0, 20))

        try:
            cursor = self.connection.cursor()

            if self.current_role == 'caregiver':
                # Show only assigned patient
                cursor.execute("""
                    SELECT p.id, p.full_name, p.age, p.diagnosis, p.stage, p.emergency_contact
                    FROM patients p
                    JOIN caregivers c ON c.patient_id = p.id
                    WHERE c.id = %s
                """, (self.current_user,))
            else:  # doctor
                # Show all patients
                cursor.execute("""
                    SELECT id, full_name, age, diagnosis, stage, emergency_contact
                    FROM patients
                """)

            patients = cursor.fetchall()
            cursor.close()

            if not patients:
                tk.Label(main_frame, text="No patients found", font=self.normal_font,
                         bg="white", fg="#64748b").pack(pady=50)
            else:
                for patient in patients:
                    self.create_patient_card(main_frame, patient)
        except Error as e:
            messagebox.showerror("Error", f"Failed to load patient info: {e}")

    def create_patient_card(self, parent, patient):
        """Create patient information card"""
        patient_id, name, age, diagnosis, stage, emergency_contact = patient

        card = tk.Frame(parent, bg="#f8fafc", relief=tk.RAISED, borderwidth=2)
        card.pack(fill=tk.X, pady=10, padx=10)

        info_frame = tk.Frame(card, bg="#f8fafc")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(info_frame, text=name, font=("Arial", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(anchor="w")
        tk.Label(info_frame, text=f"Age: {age}   Diagnosis: {diagnosis}   Stage: {stage}",
                 font=("Arial", 10), bg="#f8fafc", fg="#64748b").pack(anchor="w", pady=5)
        tk.Label(info_frame, text=f"Emergency contact: {emergency_contact}", font=("Arial", 10),
                 bg="#f8fafc", fg="#64748b").pack(anchor="w")

    def add_user_form(self):
        """Doctor can add new patients, caregivers, or doctors (simple form in same window)"""
        for w in self.content_frame.winfo_children():
            w.destroy()

        frame = tk.Frame(self.content_frame, bg="white", padx=30, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Add New User", font=self.header_font, bg="white", fg="#1e293b").grid(row=0, column=0, columnspan=2, pady=20)

        tk.Label(frame, text="Role:", bg="white").grid(row=1, column=0, sticky="w", pady=10)
        role_box = ttk.Combobox(frame, values=["patient", "caregiver", "doctor"], state="readonly", width=28)
        role_box.grid(row=1, column=1, pady=10)
        role_box.current(0)

        tk.Label(frame, text="Username:", bg="white").grid(row=2, column=0, sticky="w", pady=10)
        uname = tk.Entry(frame, width=30); uname.grid(row=2, column=1, pady=10)

        tk.Label(frame, text="Password:", bg="white").grid(row=3, column=0, sticky="w", pady=10)
        pwd = tk.Entry(frame, width=30, show="*"); pwd.grid(row=3, column=1, pady=10)

        tk.Label(frame, text="Full Name:", bg="white").grid(row=4, column=0, sticky="w", pady=10)
        fname = tk.Entry(frame, width=30); fname.grid(row=4, column=1, pady=10)

        tk.Label(frame, text="Phone / Spec / Relation:", bg="white").grid(row=5, column=0, sticky="w", pady=10)
        extra = tk.Entry(frame, width=30); extra.grid(row=5, column=1, pady=10)

        tk.Label(frame, text="Patient (for caregiver) - ID (optional):", bg="white").grid(row=6, column=0, sticky="w", pady=10)
        patient_id_entry = tk.Entry(frame, width=30); patient_id_entry.grid(row=6, column=1, pady=10)

        def save_user():
            role = role_box.get()
            u = uname.get().strip()
            p = pwd.get().strip()
            n = fname.get().strip()
            ex = extra.get().strip()
            pid_text = patient_id_entry.get().strip()
            if not u or not p or not n:
                messagebox.showerror("Error", "Please fill username, password, and full name")
                return
            try:
                c = self.connection.cursor()
                if role == 'patient':
                    # Basic patient insertion; other fields defaulted
                    c.execute("""INSERT INTO patients (username,password,full_name,age,diagnosis,stage,emergency_contact)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                              (u, p, n, 65, 'Not Diagnosed', 'Early', ex if ex else 'N/A'))
                elif role == 'caregiver':
                    # caregiver needs patient_id — use given or fallback to first patient
                    if pid_text:
                        try:
                            pid_val = int(pid_text)
                        except:
                            messagebox.showerror("Error", "Patient ID must be numeric")
                            c.close()
                            return
                    else:
                        c.execute("SELECT id FROM patients LIMIT 1")
                        pr = c.fetchone()
                        pid_val = pr[0] if pr else None
                    c.execute("""INSERT INTO caregivers (username,password,full_name,phone,relationship,patient_id)
                                 VALUES (%s,%s,%s,%s,%s,%s)""",
                              (u, p, n, ex if ex else '+91-9000000000', 'Relative', pid_val))
                else:  # doctor
                    c.execute("""INSERT INTO doctors (username,password,full_name,specialization,license_number,hospital)
                                 VALUES (%s,%s,%s,%s,%s,%s)""",
                              (u, p, n, ex if ex else 'General', 'TEMP-LIC', 'Local Hospital'))
                self.connection.commit()
                c.close()
                messagebox.showinfo("Success", f"{role.capitalize()} added successfully!")
                self.log_action("ADD_USER", f"Added new {role}: {u}")
                # Clear fields
                uname.delete(0, tk.END); pwd.delete(0, tk.END); fname.delete(0, tk.END); extra.delete(0, tk.END); patient_id_entry.delete(0, tk.END)
            except Error as e:
                messagebox.showerror("Error", f"Failed to add user: {e}")

        tk.Button(frame, text="Save User", bg="#10b981", fg="white", padx=30, pady=10, command=save_user).grid(row=7, column=0, columnspan=2, pady=20)

    def show_audit_logs(self):
        """Show audit logs (doctor only)"""
        for w in self.content_frame.winfo_children():
            w.destroy()

        frame = tk.Frame(self.content_frame, bg="white", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Audit Logs", font=self.header_font, bg="white", fg="#1e293b").pack(pady=(0, 20))

        # Logs list
        text = scrolledtext.ScrolledText(frame, width=100, height=30)
        text.pack(fill=tk.BOTH, expand=True)

        try:
            c = self.connection.cursor()
            c.execute("SELECT action_date, user_type, user_id, action, details FROM audit_logs ORDER BY action_date DESC LIMIT 200")
            rows = c.fetchall()
            for r in rows:
                line = f"{r[0]} | {r[1]}#{r[2]} | {r[3]} | {r[4]}\n"
                text.insert(tk.END, line)
            c.close()
        except Error as e:
            messagebox.showerror("Error", f"Failed to load logs: {e}")

    def start_reminder_thread(self):
        """Start background thread that checks for reminders (simple notification)"""
        def checker():
            while self.running:
                try:
                    cursor = self.connection.cursor()
                    now = datetime.now()
                    today = now.strftime('%Y-%m-%d')
                    current_time = now.strftime('%H:%M:%S')
                    # Find reminders for current date and time within next minute
                    cursor.execute("""
                        SELECT id, user_type, user_id, patient_id, title, description, reminder_time
                        FROM reminders
                        WHERE reminder_date = %s AND is_active = TRUE AND is_completed = FALSE
                    """, (today,))
                    reminders = cursor.fetchall()
                    for r in reminders:
                        rid, utype, uid, pid, title, desc, rtime = r
                        # if reminder time equals current hour:minute (ignores seconds)
                        if isinstance(rtime, str):
                            time_str = rtime
                        else:
                            time_str = rtime.strftime('%H:%M:%S')
                        if time_str[:5] == current_time[:5]:
                            # If logged-in user is the target, show a popup (only if matches)
                            if self.current_role == utype and self.current_user == uid:
                                try:
                                    # Show a small popup in main thread
                                    self.root.after(0, lambda t=title, d=desc: messagebox.showinfo("Reminder", f"{t}\n\n{d}"))
                                    # Optionally mark as seen? Not marking automatically.
                                except Exception as e:
                                    print("Reminder popup failed:", e)
                    cursor.close()
                except Exception as e:
                    print("Reminder thread error:", e)
                time.sleep(30)  # check every 30 seconds
        self.reminder_thread = threading.Thread(target=checker, daemon=True)
        self.reminder_thread.start()

    def on_closing(self):
        """Clean up on close"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.running = False
            try:
                if self.connection:
                    self.connection.close()
            except:
                pass
            self.root.destroy()

    def logout(self):
        self.current_user = None
        self.current_role = None
        self.show_login()

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryCompanionApp(root)
    root.mainloop()
