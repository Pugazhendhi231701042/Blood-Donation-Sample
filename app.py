import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid

# --- Initialize Session State ---
def initialize_session_state():
    if 'donors' not in st.session_state:
        st.session_state.donors = {} # {email: {name, age, blood_group, health_status, city, password, donation_history: []}}
    if 'patients' not in st.session_state:
        st.session_state.patients = {} # {email: {name, age, medical_condition, blood_group_needed, city, password, received_donations: []}}
    if 'hospitals' not in st.session_state:
        st.session_state.hospitals = {} # {email: {name, city, password}}
    if 'blood_inventory' not in st.session_state:
        st.session_state.blood_inventory = {} # {hospital_email: {blood_group: quantity}}
    if 'blood_requests' not in st.session_state:
        st.session_state.blood_requests = [] # [{id, patient_email, hospital_email, blood_group, urgency, status, request_time}]
    if 'scheduled_donations' not in st.session_state:
        st.session_state.scheduled_donations = [] # [{id, donor_email, hospital_email, date, status}]
    if 'completed_donations' not in st.session_state:
        st.session_state.completed_donations = [] # [{id, donor_email, patient_email, hospital_email, blood_group, date, confirmed_by_hospital}]

    if 'current_user_email' not in st.session_state:
        st.session_state.current_user_email = None
    if 'logged_in_as' not in st.session_state:
        st.session_state.logged_in_as = None # 'donor', 'patient', 'hospital'

initialize_session_state()

# --- Utility Functions ---
BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
COMPATIBILITY = {
    'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'], # universal donor
    'O+': ['O+', 'A+', 'B+', 'AB+'],
    'A-': ['A-', 'A+', 'AB-', 'AB+'],
    'A+': ['A+', 'AB+'],
    'B-': ['B-', 'B+', 'AB-', 'AB+'],
    'B+': ['B+', 'AB+'],
    'AB-': ['AB-', 'AB+'],
    'AB+': ['AB+'] # universal recipient
}

def is_compatible_donor(donor_blood, patient_blood):
    """Checks if a donor's blood group is compatible with a patient's."""
    return patient_blood in COMPATIBILITY.get(donor_blood, [])

def get_recipient_compatible_blood_groups(patient_blood):
    """Returns blood groups that can donate to the given patient_blood group."""
    compatible_donors = []
    for donor_group, recipients in COMPATIBILITY.items():
        if patient_blood in recipients:
            compatible_donors.append(donor_group)
    return compatible_donors

# --- User Management ---
def register_user(user_type, details):
    email = details['email']
    password = details['password']
    if user_type == 'donor':
        if email in st.session_state.donors:
            return False, "Donor with this email already exists."
        st.session_state.donors[email] = {
            'name': details['name'],
            'age': details['age'],
            'blood_group': details['blood_group'],
            'health_status': details['health_status'],
            'city': details['city'],
            'password': password,
            'donation_history': [],
            'last_donation_date': None
        }
    elif user_type == 'patient':
        if email in st.session_state.patients:
            return False, "Patient with this email already exists."
        st.session_state.patients[email] = {
            'name': details['name'],
            'age': details['age'],
            'medical_condition': details['medical_condition'],
            'blood_group_needed': details['blood_group_needed'],
            'city': details['city'],
            'password': password,
            'received_donations': []
        }
    elif user_type == 'hospital':
        if email in st.session_state.hospitals:
            return False, "Hospital with this email already exists."
        st.session_state.hospitals[email] = {
            'name': details['name'],
            'city': details['city'],
            'password': password
        }
        st.session_state.blood_inventory[email] = {bg: 0 for bg in BLOOD_GROUPS} # Initialize inventory for new hospital
    return True, f"{user_type.capitalize()} registered successfully!"

def login_user(user_type, email, password):
    if user_type == 'donor' and email in st.session_state.donors and st.session_state.donors[email]['password'] == password:
        st.session_state.current_user_email = email
        st.session_state.logged_in_as = 'donor'
        return True
    elif user_type == 'patient' and email in st.session_state.patients and st.session_state.patients[email]['password'] == password:
        st.session_state.current_user_email = email
        st.session_state.logged_in_as = 'patient'
        return True
    elif user_type == 'hospital' and email in st.session_state.hospitals and st.session_state.hospitals[email]['password'] == password:
        st.session_state.current_user_email = email
        st.session_state.logged_in_as = 'hospital'
        return True
    return False

def logout_user():
    st.session_state.current_user_email = None
    st.session_state.logged_in_as = None
    st.info("You have been logged out.")

# --- UI Components ---
def show_login_register():
    st.sidebar.title("BloodConnect")
    st.sidebar.markdown("---")

    st.sidebar.header("Login / Register")
    choice = st.sidebar.radio("Select Action", ["Login", "Register"])
    user_type = st.sidebar.radio("I am a:", ["Donor", "Patient", "Hospital"])

    if choice == "Register":
        with st.sidebar.form(key=f'{user_type.lower()}_register_form'):
            st.subheader(f"Register as {user_type}")
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            city = st.text_input("City")

            if user_type == "Donor":
                age = st.number_input("Age", min_value=18, max_value=99, value=25)
                blood_group = st.selectbox("Blood Group", BLOOD_GROUPS)
                health_status = st.text_area("Health Status (e.g., No underlying conditions)")
                submit_button = st.form_submit_button("Register Donor")
                if submit_button:
                    success, message = register_user('donor', {'name': name, 'age': age, 'blood_group': blood_group, 'health_status': health_status, 'city': city, 'email': email, 'password': password})
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            elif user_type == "Patient":
                age = st.number_input("Age", min_value=0, max_value=99, value=30)
                medical_condition = st.text_area("Medical Condition (e.g., Anemia requiring transfusion)")
                blood_group_needed = st.selectbox("Blood Group Needed", BLOOD_GROUPS)
                submit_button = st.form_submit_button("Register Patient")
                if submit_button:
                    success, message = register_user('patient', {'name': name, 'age': age, 'medical_condition': medical_condition, 'blood_group_needed': blood_group_needed, 'city': city, 'email': email, 'password': password})
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            elif user_type == "Hospital":
                submit_button = st.form_submit_button("Register Hospital")
                if submit_button:
                    success, message = register_user('hospital', {'name': name, 'city': city, 'email': email, 'password': password})
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

    elif choice == "Login":
        with st.sidebar.form(key=f'{user_type.lower()}_login_form'):
            st.subheader(f"Login as {user_type}")
            email = st.text_input("Email", key=f'login_email_{user_type}')
            password = st.text_input("Password", type="password", key=f'login_password_{user_type}')
            submit_button = st.form_submit_button("Login")
            if submit_button:
                if login_user(user_type.lower(), email, password):
                    st.sidebar.success("Logged in successfully!")
                    st.experimental_rerun()
                else:
                    st.sidebar.error("Invalid email or password.")

    st.markdown("---")
    st.markdown("This is a demo. Data is stored in memory and resets on refresh.")


def donor_dashboard():
    st.title(f"Donor Dashboard - Welcome, {st.session_state.donors[st.session_state.current_user_email]['name']}!")
    st.subheader("Your Profile")
    donor_data = st.session_state.donors[st.session_state.current_user_email]
    st.write(f"**Name:** {donor_data['name']}")
    st.write(f"**Blood Group:** {donor_data['blood_group']}")
    st.write(f"**City:** {donor_data['city']}")
    st.write(f"**Last Donation:** {donor_data['last_donation_date'] if donor_data['last_donation_date'] else 'Never'}")
    next_due_date = None
    if donor_data['last_donation_date']:
        next_due_date = donor_data['last_donation_date'] + timedelta(days=90) # Approx 3 months
        st.write(f"**Next Donation Due (approx):** {next_due_date.strftime('%Y-%m-%d')}")
        if next_due_date > datetime.now().date():
            st.info("You are currently not eligible to donate. Please wait until your next donation due date.")
    st.markdown("---")

    if next_due_date and next_due_date > datetime.now().date():
        st.subheader("Upcoming Donation Opportunities")
        st.warning("You are not currently eligible to donate. Please check back later.")
    else:
        st.subheader("Upcoming Donation Opportunities")
        eligible_requests = []
        for req in st.session_state.blood_requests:
            patient_data = st.session_state.patients.get(req['patient_email'])
            if patient_data and is_compatible_donor(donor_data['blood_group'], req['blood_group']) and \
               patient_data['city'] == donor_data['city'] and req['status'] == 'pending':
                eligible_requests.append(req)

        if eligible_requests:
            st.write("Here are blood requests matching your blood type and city:")
            for req in eligible_requests:
                patient_data = st.session_state.patients[req['patient_email']]
                hospital_data = st.session_state.hospitals[req['hospital_email']]
                with st.expander(f"Urgent {req['blood_group']} needed for {patient_data['name']} at {hospital_data['name']}"):
                    st.write(f"**Patient Name:** {patient_data['name']}")
                    st.write(f"**Blood Group Needed:** {req['blood_group']}")
                    st.write(f"**Urgency:** {req['urgency']}")
                    st.write(f"**Hospital:** {hospital_data['name']} ({hospital_data['city']})")
                    st.write(f"**Medical Condition:** {patient_data['medical_condition']}")
                    st.write(f"**Requested On:** {req['request_time'].strftime('%Y-%m-%d %H:%M')}")

                    st.subheader("Schedule Your Donation")
                    hospitals_in_city = {h_email: h_data['name'] for h_email, h_data in st.session_state.hospitals.items() if h_data['city'] == donor_data['city']}
                    selected_hospital_name = st.selectbox("Select Hospital for Donation", list(hospitals_in_city.values()), key=f'schedule_hospital_{req["id"]}')
                    selected_hospital_email = [email for email, name in hospitals_in_city.items() if name == selected_hospital_name][0]
                    donation_date = st.date_input("Preferred Donation Date", min_value=datetime.now().date(), key=f'schedule_date_{req["id"]}')

                    if st.button(f"Schedule Donation for {req['blood_group']}", key=f'schedule_btn_{req["id"]}'):
                        scheduled_donation = {
                            'id': str(uuid.uuid4()),
                            'donor_email': st.session_state.current_user_email,
                            'patient_email': req['patient_email'], # Link to the request's patient
                            'hospital_email': selected_hospital_email,
                            'blood_group': req['blood_group'],
                            'date': donation_date,
                            'status': 'scheduled'
                        }
                        st.session_state.scheduled_donations.append(scheduled_donation)
                        st.success(f"Donation scheduled for {donation_date} at {selected_hospital_name}. Hospital will confirm.")
                        # Optionally mark request as 'matched' or 'in progress'
                        req['status'] = 'matched'
                        st.experimental_rerun()
        else:
            st.info("No matching urgent blood requests in your city at this moment. Thank you for your willingness to donate!")

    st.markdown("---")
    st.subheader("Your Donation History")
    donor_history_df = pd.DataFrame(donor_data['donation_history'])
    if not donor_history_df.empty:
        st.table(donor_history_df)
    else:
        st.info("You haven't made any confirmed donations yet.")

def patient_dashboard():
    st.title(f"Patient Dashboard - Welcome, {st.session_state.patients[st.session_state.current_user_email]['name']}!")
    patient_data = st.session_state.patients[st.session_state.current_user_email]

    st.subheader("Your Blood Request")
    current_request = next((req for req in st.session_state.blood_requests if req['patient_email'] == st.session_state.current_user_email and req['status'] == 'pending'), None)

    if current_request:
        st.warning(f"You have an active request for {current_request['blood_group']} (Urgency: {current_request['urgency']}).")
        st.write(f"Requested at: {st.session_state.hospitals[current_request['hospital_email']]['name']} ({st.session_state.hospitals[current_request['hospital_email']]['city']})")
        st.write(f"Status: {current_request['status'].capitalize()}")

        compatible_donors_found = False
        potential_donors = []
        for donor_email, donor_info in st.session_state.donors.items():
            if is_compatible_donor(donor_info['blood_group'], current_request['blood_group']) and \
               donor_info['city'] == patient_data['city'] and \
               (donor_info['last_donation_date'] is None or (datetime.now().date() - donor_info['last_donation_date']).days >= 90):
                potential_donors.append(donor_info['name'])
                compatible_donors_found = True

        if compatible_donors_found:
            st.success(f"Potential compatible donors found in your city: {', '.join(potential_donors)}")
            st.info("Hospitals will reach out to schedule donations with compatible donors.")
        else:
            st.info("No immediate compatible donors found in your city. Expanding search...")

        if st.button("Cancel Blood Request", key="cancel_patient_request"):
            # A more robust system would update this request's status and notify linked donors/hospitals
            st.session_state.blood_requests = [req for req in st.session_state.blood_requests if req['id'] != current_request['id']]
            st.success("Your blood request has been cancelled.")
            st.experimental_rerun()

    else:
        st.subheader("Post a New Blood Request")
        with st.form(key="post_request_form"):
            blood_group_needed = st.selectbox("Blood Group Needed", BLOOD_GROUPS, index=BLOOD_GROUPS.index(patient_data['blood_group_needed']))
            urgency = st.selectbox("Urgency", ["Normal", "Urgent", "Critical"])
            hospitals_in_city = {h_email: h_data['name'] for h_email, h_data in st.session_state.hospitals.items() if h_data['city'] == patient_data['city']}
            if hospitals_in_city:
                selected_hospital_name = st.selectbox("Request from which Hospital?", list(hospitals_in_city.values()))
                selected_hospital_email = [email for email, name in hospitals_in_city.items() if name == selected_hospital_name][0]
                submit_button = st.form_submit_button("Post Request")

                if submit_button:
                    new_request = {
                        'id': str(uuid.uuid4()),
                        'patient_email': st.session_state.current_user_email,
                        'hospital_email': selected_hospital_email,
                        'blood_group': blood_group_needed,
                        'urgency': urgency,
                        'status': 'pending',
                        'request_time': datetime.now()
                    }
                    st.session_state.blood_requests.append(new_request)
                    st.success(f"Your request for {blood_group_needed} has been posted at {selected_hospital_name}.")
                    st.experimental_rerun()
            else:
                st.warning("No hospitals registered in your city. Cannot post a request.")

    st.markdown("---")
    st.subheader("Your Received Donations")
    received_donations_df = pd.DataFrame(patient_data['received_donations'])
    if not received_donations_df.empty:
        st.table(received_donations_df)
    else:
        st.info("You haven't received any confirmed donations yet.")


def hospital_dashboard():
    st.title(f"Hospital Dashboard - Welcome, {st.session_state.hospitals[st.session_state.current_user_email]['name']}!")
    hospital_data = st.session_state.hospitals[st.session_state.current_user_email]
    hospital_email = st.session_state.current_user_email

    st.subheader("Blood Inventory Management")
    if hospital_email not in st.session_state.blood_inventory:
        st.session_state.blood_inventory[hospital_email] = {bg: 0 for bg in BLOOD_GROUPS}

    current_inventory = st.session_state.blood_inventory[hospital_email]
    st.write("Current Stock:")
    inventory_data = [{'Blood Group': bg, 'Units': qty} for bg, qty in current_inventory.items()]
    inventory_df = pd.DataFrame(inventory_data)
    st.table(inventory_df)

    with st.form(key="update_inventory_form"):
        st.subheader("Add/Update Blood Units")
        blood_group = st.selectbox("Blood Group", BLOOD_GROUPS, key='add_bg')
        units_to_add = st.number_input("Units to Add/Set", min_value=0, value=0, key='add_units')
        submit_button = st.form_submit_button("Update Inventory")
        if submit_button:
            st.session_state.blood_inventory[hospital_email][blood_group] += units_to_add
            st.success(f"Added {units_to_add} units of {blood_group}. Total: {st.session_state.blood_inventory[hospital_email][blood_group]}")
            st.experimental_rerun()

    st.markdown("---")
    st.subheader("Pending Blood Requests for Your Hospital")
    my_hospital_requests = [req for req in st.session_state.blood_requests if req['hospital_email'] == hospital_email and req['status'] in ['pending', 'matched']]
    if my_hospital_requests:
        for req in my_hospital_requests:
            patient_data = st.session_state.patients[req['patient_email']]
            with st.expander(f"Request for {req['blood_group']} from {patient_data['name']} (Urgency: {req['urgency']})"):
                st.write(f"**Patient Name:** {patient_data['name']}")
                st.write(f"**Blood Group Needed:** {req['blood_group']}")
                st.write(f"**Urgency:** {req['urgency']}")
                st.write(f"**Status:** {req['status'].capitalize()}")
                st.write(f"**Requested On:** {req['request_time'].strftime('%Y-%m-%d %H:%M')}")

                # Find scheduled donations for this request at this hospital
                scheduled_donations_for_request = [
                    sd for sd in st.session_state.scheduled_donations
                    if sd['patient_email'] == req['patient_email'] and sd['hospital_email'] == hospital_email
                    and sd['blood_group'] == req['blood_group'] and sd['status'] == 'scheduled'
                ]

                if scheduled_donations_for_request:
                    st.info(f"There are {len(scheduled_donations_for_request)} scheduled donations for this request.")
                    for sd in scheduled_donations_for_request:
                        donor_name = st.session_state.donors[sd['donor_email']]['name']
                        with st.expander(f"Scheduled by {donor_name} for {sd['date']}"):
                            st.write(f"**Donor:** {donor_name} ({sd['donor_email']})")
                            st.write(f"**Blood Group:** {sd['blood_group']}")
                            st.write(f"**Scheduled Date:** {sd['date']}")

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"Confirm Donation from {donor_name}", key=f'confirm_don_{sd["id"]}'):
                                    # Update donor's last donation date
                                    st.session_state.donors[sd['donor_email']]['last_donation_date'] = sd['date']
                                    st.session_state.donors[sd['donor_email']]['donation_history'].append({
                                        'id': sd['id'],
                                        'hospital': hospital_data['name'],
                                        'blood_group': sd['blood_group'],
                                        'date': sd['date']
                                    })
                                    # Update patient's received donations
                                    st.session_state.patients[req['patient_email']]['received_donations'].append({
                                        'id': sd['id'],
                                        'donor': donor_name,
                                        'blood_group': sd['blood_group'],
                                        'date': sd['date']
                                    })
                                    # Increment hospital inventory (if applicable)
                                    st.session_state.blood_inventory[hospital_email][sd['blood_group']] += 1
                                    # Update scheduled donation status
                                    sd['status'] = 'completed'
                                    # Mark the original blood request as fulfilled if this donation is sufficient
                                    req['status'] = 'fulfilled' # Simplified: assume one donation fulfills request for now

                                    st.success(f"Donation from {donor_name} confirmed! Inventory updated.")
                                    st.experimental_rerun()
                            with col2:
                                if st.button(f"Reject Donation from {donor_name}", key=f'reject_don_{sd["id"]}'):
                                    sd['status'] = 'rejected'
                                    st.warning(f"Donation from {donor_name} rejected.")
                                    st.experimental_rerun()
                else:
                    st.info("No donations scheduled for this request yet.")
        else:
            st.info("No pending blood requests for your hospital.")

    st.markdown("---")
    st.subheader("Your Hospital's Donations History")
    hospital_completed_donations = [
        d for d in st.session_state.scheduled_donations
        if d['hospital_email'] == hospital_email and d['status'] == 'completed'
    ]
    if hospital_completed_donations:
        donations_df = pd.DataFrame(hospital_completed_donations)
        donations_df['Donor Name'] = donations_df['donor_email'].apply(lambda email: st.session_state.donors[email]['name'])
        donations_df['Patient Name'] = donations_df['patient_email'].apply(lambda email: st.session_state.patients[email]['name'])
        st.table(donations_df[['Donor Name', 'Patient Name', 'blood_group', 'date', 'status']])
    else:
        st.info("No completed donations at your hospital yet.")


# --- Main App Logic ---
st.set_page_config(layout="wide", page_title="BloodConnect Demo")

if st.session_state.logged_in_as is None:
    show_login_register()
else:
    st.sidebar.title("BloodConnect")
    st.sidebar.markdown(f"Welcome, **{st.session_state.current_user_email}** ({st.session_state.logged_in_as.capitalize()})")
    st.sidebar.markdown("---")

    if st.session_state.logged_in_as == 'donor':
        donor_dashboard()
    elif st.session_state.logged_in_as == 'patient':
        patient_dashboard()
    elif st.session_state.logged_in_as == 'hospital':
        hospital_dashboard()

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        logout_user()
        st.experimental_rerun()
