#!/usr/bin/env python3
"""
CRM Feature Extensions for Streamlit Dashboard
Lead management, call tracking, and email integration
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import sendgrid
from sendgrid.helpers.mail import Mail
import os
from typing import Dict, List, Optional

class CRMManager:
    def __init__(self):
        self.activity_file = "crm_data/crm_activities.json"
        self.assignments_file = "crm_data/lead_assignments.json"
        self.init_data_files()
    
    def init_data_files(self):
        """Initialize CRM data files if they don't exist"""
        # Create directory if it doesn't exist
        os.makedirs("crm_data", exist_ok=True)
        
        if not os.path.exists(self.activity_file):
            with open(self.activity_file, 'w') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.assignments_file):
            with open(self.assignments_file, 'w') as f:
                json.dump({}, f)
    
    def load_activities(self) -> Dict:
        """Load contact activities from file"""
        try:
            with open(self.activity_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_activities(self, activities: Dict):
        """Save activities to file"""
        with open(self.activity_file, 'w') as f:
            json.dump(activities, f, indent=2)
    
    def load_assignments(self) -> Dict:
        """Load lead assignments"""
        try:
            with open(self.assignments_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_assignments(self, assignments: Dict):
        """Save lead assignments"""
        with open(self.assignments_file, 'w') as f:
            json.dump(assignments, f, indent=2)

def render_sales_rep_selector():
    """Multi-user system for sales reps"""
    st.sidebar.markdown("### 👥 Sales Rep Login")
    
    sales_reps = {
        "rep3": "Julian",
        "rep2": "Jason", 
        "rep1": "Noah",
    }
    
    selected_rep = st.sidebar.selectbox(
        "Select Your Profile:",
        options=list(sales_reps.keys()),
        format_func=lambda x: sales_reps[x],
        key="selected_rep"
    )
    
    st.sidebar.success(f"Logged in as: {sales_reps[selected_rep]}")
    return selected_rep, sales_reps[selected_rep]

def render_territory_assignment(df: pd.DataFrame):
    """Territory-based lead assignment with unique phone numbers"""
    st.subheader("🗺️ Territory & Lead Assignment")
    
    crm = CRMManager()
    assignments = crm.load_assignments()
    current_rep = st.session_state.get('selected_rep', 'rep1')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Territory filter - handle both unique_phones and contacts data
        state_column = 'state' if 'state' in df.columns else 'primary_location'
        if state_column == 'primary_location':
            # Extract state from location for contacts table
            df['state'] = df['primary_location'].apply(lambda x: x.split(',')[-1].strip() if ',' in str(x) else 'Unknown')
        
        states = df['state'].unique() if 'state' in df.columns else ['All States']
        selected_states = st.multiselect(
            "Your Territory (States):",
            options=states,
            default=states[:3] if len(states) > 3 else states
        )
        
        # Filter unassigned leads in territory
        if 'state' in df.columns:
            territory_df = df[df['state'].isin(selected_states)]
        else:
            territory_df = df
        
        unassigned_df = territory_df[~territory_df.index.isin(assignments.keys())]
        
        # Handle both dialer and contacts data structures
        company_column = 'company_name' if 'company_name' in df.columns else 'seller_company'
        phone_column = 'phone_number' if 'phone_number' in df.columns else 'primary_phone'
        
        st.metric("Available Leads in Territory", len(unassigned_df))
        st.metric("Your Assigned Leads", sum(1 for rep in assignments.values() if rep == current_rep))
    
    with col2:
        st.markdown("### Quick Actions")
        if st.button("📋 Claim Next 10 Leads", type="primary"):
            # Assign next 10 leads to current rep
            next_leads = unassigned_df.head(10)
            for idx in next_leads.index:
                assignments[str(idx)] = current_rep
            crm.save_assignments(assignments)
            st.success(f"Claimed {len(next_leads)} new leads!")
            st.rerun()
    
    # Show assigned leads
    st.markdown("---")
    st.subheader("📋 Your Assigned Leads")
    
    # Get assigned leads for current rep
    my_leads = [int(lead_id) for lead_id, rep in assignments.items() if rep == current_rep]
    my_leads_df = df[df.index.isin(my_leads)]
    
    if my_leads_df.empty:
        st.info("No leads assigned yet. Use the 'Claim Next 10 Leads' button above to get started!")
    else:
        # Display assigned leads in a nice format
        st.markdown(f"**You have {len(my_leads_df)} assigned leads:**")
        
        # Add tabs for different views  
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary View", "📞 Call List", "📧 Email Database", "📋 Full Details"])
        
        with tab1:
            # Summary cards
            crm = CRMManager()
            activities = crm.load_activities()
            
            for idx, contact in my_leads_df.head(5).iterrows():  # Show first 5 as cards
                contact_key = f"contact_{idx}"
                activity = activities.get(contact_key, {})
                user_email = activity.get('email', 'No email added yet')
                call_status = activity.get('status', 'Not Called')
                
                with st.expander(f"🏢 {contact['seller_company']} - {contact['primary_location']} | Status: {call_status}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**📞 Phone:** {contact['primary_phone']}")
                        st.write(f"**📧 Email:** {user_email}")
                    with col2:
                        st.write(f"**📦 Listings:** {contact.get('total_listings', 'N/A')}")
                        st.write(f"**⭐ Priority:** {contact.get('priority_level', 'Medium')}")
                    
                    # Show notes if any
                    if activity.get('notes'):
                        st.write(f"**📝 Notes:** {activity['notes']}")
            
            if len(my_leads_df) > 5:
                st.info(f"Showing first 5 leads. See 'Full Details' tab for all {len(my_leads_df)} leads.")
        
        with tab2:
            # Clean table format for call list
            st.markdown("**Call List Table:**")
            crm = CRMManager()
            activities = crm.load_activities()
            
            # Prepare table data
            table_data = []
            for idx, contact in my_leads_df.iterrows():
                contact_key = f"contact_{idx}"
                activity = activities.get(contact_key, {})
                user_email = activity.get('email', '')
                call_status = activity.get('status', 'Not Called')
                notes = activity.get('notes', '')
                
                table_data.append({
                    'Company': contact['seller_company'],
                    'Phone': contact['primary_phone'],
                    'Location': contact['primary_location'],
                    'Email': user_email if user_email else '',
                    'Status': call_status,
                    'Listings': contact.get('total_listings', 'N/A'),
                    'Notes': notes[:50] + '...' if len(notes) > 50 else notes,  # Truncate long notes
                    'Research': idx  # Store index for research button
                })
            
            if table_data:
                # Create DataFrame for display
                call_df = pd.DataFrame(table_data)
                
                # Display table with smaller text
                st.markdown("""
                <style>
                .small-font {
                    font-size: 12px !important;
                }
                div[data-testid="stDataFrame"] {
                    font-size: 12px;
                }
                div[data-testid="stDataFrame"] table {
                    font-size: 12px !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Create columns for table and research panel
                table_col, research_col = st.columns([3, 1])
                
                with table_col:
                    # Use AgGrid or native dataframe with selection
                    st.dataframe(
                        call_df[['Company', 'Phone', 'Location', 'Email', 'Status', 'Listings', 'Notes']],
                        use_container_width=True,
                        height=400,
                        hide_index=True,
                        column_config={
                            'Company': st.column_config.TextColumn('Company', width='large'),
                            'Phone': st.column_config.TextColumn('Phone', width='medium'),
                            'Location': st.column_config.TextColumn('Location', width='medium'),
                            'Email': st.column_config.TextColumn('Email', width='medium'),
                            'Status': st.column_config.SelectboxColumn('Status', width='small'),
                            'Listings': st.column_config.NumberColumn('Listings', width='small'),
                            'Notes': st.column_config.TextColumn('Notes', width='large')
                        }
                    )
                
                with research_col:
                    st.markdown("### Company Research")
                    
                    # Company selection for research
                    company_options = [f"{row['Company']}" for row in table_data]
                    selected_company = st.selectbox(
                        "Select Company:",
                        options=company_options,
                        key="research_company"
                    )
                    
                    if st.button("🔍 Research Company", type="primary"):
                        if selected_company:
                            # Find the selected company data
                            selected_data = next(row for row in table_data if row['Company'] == selected_company)
                            # Set research data in session state for fixed panel
                            st.session_state.research_panel_data = selected_data
                            st.session_state.research_panel_open = True
                            st.rerun()
            else:
                st.info("No leads assigned yet.")
        
        with tab3:
            # Email database - contacts where we've collected emails
            st.markdown("**📧 Contacts with Emails Collected:**")
            crm = CRMManager()
            activities = crm.load_activities()
            
            contacts_with_emails = []
            for idx, contact in my_leads_df.iterrows():
                contact_key = f"contact_{idx}"
                activity = activities.get(contact_key, {})
                if activity.get('email') and activity['email'].strip() and activity['email'] != 'No email':
                    contacts_with_emails.append({
                        'company': contact['seller_company'],
                        'phone': contact['primary_phone'],
                        'email': activity['email'],
                        'status': activity.get('status', 'Not Called'),
                        'notes': activity.get('notes', ''),
                        'last_updated': activity.get('last_updated', '')
                    })
            
            if contacts_with_emails:
                st.success(f"📧 {len(contacts_with_emails)} contacts have email addresses!")
                
                # Display emails in a nice format
                for contact in contacts_with_emails:
                    with st.expander(f"📧 {contact['company']} - {contact['email']}", expanded=False):
                        st.write(f"**Phone:** {contact['phone']}")
                        st.write(f"**Status:** {contact['status']}")
                        if contact['notes']:
                            st.write(f"**Notes:** {contact['notes']}")
                        if contact['last_updated']:
                            st.write(f"**Last Updated:** {contact['last_updated']}")
                
                # Export emails for marketing
                email_csv = pd.DataFrame(contacts_with_emails).to_csv(index=False)
                st.download_button(
                    label="📧 Download Email List CSV",
                    data=email_csv,
                    file_name=f"email_database_{current_rep}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📧 No emails collected yet. Add emails during your phone calls in the Call Campaign section!")
        
        with tab4:
            # Full dataframe with enhanced data including user-collected emails
            st.markdown("**Complete Lead Database:**")
            
            # Merge scraped data with user-collected data
            enhanced_data = []
            crm = CRMManager()
            activities = crm.load_activities()
            
            for idx, contact in my_leads_df.iterrows():
                contact_key = f"contact_{idx}"
                activity = activities.get(contact_key, {})
                
                enhanced_contact = {
                    'Company': contact['seller_company'],
                    'Phone': contact['primary_phone'],
                    'Location': contact['primary_location'],
                    'Listings': contact.get('total_listings', 'N/A'),
                    'Priority': contact.get('priority_level', 'Medium'),
                    'Email': activity.get('email', 'Not collected'),
                    'Call_Status': activity.get('status', 'Not Called'),
                    'Notes': activity.get('notes', ''),
                    'Last_Updated': activity.get('last_updated', '')
                }
                enhanced_data.append(enhanced_contact)
            
            enhanced_df = pd.DataFrame(enhanced_data)
            
            # Display with better formatting
            st.dataframe(
                enhanced_df,
                use_container_width=True,
                height=400
            )
            
            # Enhanced export with all data
            csv = enhanced_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Complete Database CSV",
                data=csv,
                file_name=f"complete_leads_{current_rep}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                help="Includes scraped data + emails/notes you've collected"
            )
    
    # Render fixed research panel if data exists
    render_fixed_research_panel()

def render_call_campaign_manager(df: pd.DataFrame):
    """Call campaign and activity tracking with email input"""
    st.subheader("📞 Call Campaign Manager")
    
    crm = CRMManager()
    assignments = crm.load_assignments()
    activities = crm.load_activities()
    current_rep = st.session_state.get('selected_rep', 'rep1')
    
    # Get assigned leads for current rep
    my_leads = [int(lead_id) for lead_id, rep in assignments.items() if rep == current_rep]
    my_leads_df = df[df.index.isin(my_leads)]
    
    if my_leads_df.empty:
        st.warning("No assigned leads. Please claim some leads from the Territory section.")
        return
    
    # Call status options
    call_statuses = ["Not Called", "Called - Interested", "Called - Not Interested", 
                    "Callback Scheduled", "Voicemail Left", "Do Not Call"]
    
    # Daily call list
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Today's Call List")
        
        # Priority filter
        priority_filter = st.selectbox(
            "Priority Filter:",
            ["All", "High Value (Major Brands)", "Quick Wins (Good Phone/Email)", "Follow-ups"]
        )
        
        # Display call list with actions
        for idx, contact in my_leads_df.iterrows():
            contact_key = f"contact_{idx}"
            activity = activities.get(contact_key, {})
            
            with st.expander(f"📞 {contact['seller_company']} - {contact['primary_phone']}", 
                           expanded=activity.get('status') in ['Not Called', None]):
                
                # Add research button at the top
                if st.button(f"🔍 Research {contact['seller_company']}", key=f"research_{idx}"):
                    company_data = {
                        'Company': contact['seller_company'],
                        'Phone': contact['primary_phone'],
                        'Location': contact.get('primary_location', 'Unknown'),
                        'Email': activity.get('email', ''),
                        'Status': activity.get('status', 'Not Called'),
                        'Listings': contact.get('total_listings', 'N/A'),
                        'Notes': activity.get('notes', '')
                    }
                    # Set research data in session state for fixed panel
                    st.session_state.research_panel_data = company_data
                    st.session_state.research_panel_open = True
                    st.rerun()
                
                contact_col1, contact_col2 = st.columns([2, 1])
                
                with contact_col1:
                    st.write(f"**Company:** {contact['seller_company']}")
                    st.write(f"**Phone:** {contact['primary_phone']}")
                    st.write(f"**Location:** {contact.get('primary_location', 'Unknown')}")
                    st.write(f"**Equipment:** {contact.get('equipment_type', 'Unknown')}")
                    
                    # Email input field (since scraped data doesn't have emails)
                    current_email = activity.get('email', '')
                    email_input = st.text_input(
                        "📧 Email (add during/after call):",
                        value=current_email,
                        key=f"email_{idx}",
                        placeholder="Enter email if provided during call",
                        help="Scraped data doesn't include emails - add them here!"
                    )
                    
                    # Call notes
                    notes = st.text_area(
                        "📝 Call Notes:",
                        value=activity.get('notes', ''),
                        key=f"notes_{idx}",
                        height=120,
                        placeholder="Record conversation details, needs, follow-up items..."
                    )
                
                with contact_col2:
                    # Call status
                    current_status = activity.get('status', 'Not Called')
                    new_status = st.selectbox(
                        "Call Status:",
                        call_statuses,
                        index=call_statuses.index(current_status) if current_status in call_statuses else 0,
                        key=f"status_{idx}"
                    )
                    
                    # Follow-up date
                    follow_up_date = st.date_input(
                        "Follow-up Date:",
                        value=datetime.now().date() + timedelta(days=1),
                        key=f"followup_{idx}"
                    )
                    
                    # Update button
                    if st.button("💾 Update Contact", key=f"update_{idx}"):
                        activities[contact_key] = {
                            'status': new_status,
                            'notes': notes,
                            'email': email_input,  # Save the email from user input
                            'follow_up_date': follow_up_date.isoformat(),
                            'last_updated': datetime.now().isoformat(),
                            'rep': current_rep,
                            'company': contact['seller_company'],
                            'phone': contact['primary_phone']
                        }
                        crm.save_activities(activities)
                        st.success(f"✅ {contact['seller_company']} updated!")
                        st.rerun()
    
    with col2:
        st.markdown("### 📊 Call Metrics")
        
        # Calculate metrics
        total_assigned = len(my_leads_df)
        called_today = sum(1 for activity in activities.values() 
                          if activity.get('rep') == current_rep and 
                             activity.get('last_updated', '').startswith(datetime.now().date().isoformat()))
        
        interested_leads = sum(1 for activity in activities.values()
                              if activity.get('rep') == current_rep and
                                 'Interested' in activity.get('status', ''))
        
        emails_collected = sum(1 for activity in activities.values()
                              if activity.get('rep') == current_rep and
                                 activity.get('email') and activity['email'].strip() and activity['email'] != 'No email')
        
        st.metric("Total Assigned", total_assigned)
        st.metric("Calls Made Today", called_today)
        st.metric("Interested Leads", interested_leads)
        st.metric("Emails Collected", emails_collected)
        st.metric("Conversion Rate", f"{(interested_leads/max(called_today,1)*100):.1f}%")
    
    # Render fixed research panel if data exists
    render_fixed_research_panel()

def render_email_integration():
    """SendGrid email integration for collected emails"""
    st.subheader("📧 Email Campaign Manager")
    
    # SendGrid API key check
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    if not sendgrid_key:
        st.warning("⚠️ SendGrid API key not configured. Add SENDGRID_API_KEY to your environment.")
        st.info("Get your API key from: https://app.sendgrid.com/settings/api_keys")
    
    # Load collected emails from CRM activities
    crm = CRMManager()
    activities = crm.load_activities()
    current_rep = st.session_state.get('selected_rep', 'rep1')
    
    # Get contacts with emails for this rep
    email_contacts = []
    for contact_key, activity in activities.items():
        if (activity.get('rep') == current_rep and 
            activity.get('email') and 
            activity['email'].strip() and 
            activity['email'] != 'No email'):
            email_contacts.append({
                'contact_key': contact_key,
                'company': activity.get('company', 'Unknown'),
                'email': activity['email'],
                'phone': activity.get('phone', ''),
                'status': activity.get('status', 'Not Called'),
                'notes': activity.get('notes', '')
            })
    
    if not email_contacts:
        st.info("📧 No emails collected yet. Add emails during your phone calls in the Call Campaign section!")
        return
    
    st.success(f"📧 You have {len(email_contacts)} contacts with email addresses!")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📝 Email Templates")
        
        templates = {
            "Initial Outreach": """
Subject: Equipment Transportation Services - {company_name}

Hi there,

I noticed your company, {company_name}, has equipment listings. We're Heavy Haulers Equipment Logistics, and we specialize in equipment transportation nationwide.

Would you be interested in discussing how we can help transport your equipment to buyers across the country?

Best regards,
{rep_name}
Heavy Haulers Equipment Logistics
""",
            "Follow-up": """
Subject: Following up - Equipment Transportation Services

Hi,

I wanted to follow up on my previous message about transportation services for {company_name}.

Many equipment dealers find that offering nationwide delivery significantly increases their sales potential. 

Would you have 5 minutes for a quick call this week?

Best,
{rep_name}
""",
            "Callback Confirmation": """
Subject: Confirming our call - {callback_date}

Hi,

Thanks for your interest! I'm confirming our call scheduled for {callback_date}.

I'll share how Heavy Haulers can help expand your equipment sales territory and provide competitive shipping rates.

Looking forward to speaking with you.

{rep_name}
Heavy Haulers Equipment Logistics
"""
        }
        
        selected_template = st.selectbox("Choose Template:", list(templates.keys()))
        
        # Template editor
        template_content = st.text_area(
            "Email Content:",
            value=templates[selected_template],
            height=300
        )
        
        # Email recipient selection
        st.markdown("### 📧 Send Email")
        selected_contact = st.selectbox(
            "Select Recipient:",
            options=[f"{contact['company']} - {contact['email']}" for contact in email_contacts]
        )
        
        if selected_contact and sendgrid_key:
            contact = email_contacts[[f"{c['company']} - {c['email']}" for c in email_contacts].index(selected_contact)]
            
            if st.button("📧 Send Email"):
                personalized_content = template_content.replace("{company_name}", contact['company'])
                personalized_content = personalized_content.replace("{rep_name}", st.session_state.get('rep_name', 'Sales Rep'))
                personalized_content = personalized_content.replace("{callback_date}", datetime.now().strftime('%B %d, %Y'))
                
                send_email_via_sendgrid(
                    to_email=contact['email'],
                    subject=f"Heavy Haulers - {contact['company']}",
                    content=personalized_content
                )
    
    with col2:
        st.markdown("### 📈 Email Database")
        
        # Display collected emails
        for contact in email_contacts:
            with st.expander(f"📧 {contact['company']}", expanded=False):
                st.write(f"**Email:** {contact['email']}")
                st.write(f"**Phone:** {contact['phone']}")
                st.write(f"**Status:** {contact['status']}")
                if contact['notes']:
                    st.write(f"**Notes:** {contact['notes']}")
        
        # Export button
        if email_contacts:
            email_df = pd.DataFrame(email_contacts)
            csv = email_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Email List",
                data=csv,
                file_name=f"collected_emails_{current_rep}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

def send_email_via_sendgrid(to_email: str, subject: str, content: str):
    """Send email using SendGrid API"""
    try:
        sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
        
        message = Mail(
            from_email='sales@heavyhaulerslogistics.com',  # Your verified sender
            to_emails=to_email,
            subject=subject,
            plain_text_content=content
        )
        
        response = sg.send(message)
        
        if response.status_code == 202:
            st.success(f"✅ Email sent successfully to {to_email}")
        else:
            st.error(f"❌ Failed to send email. Status: {response.status_code}")
            
    except Exception as e:
        st.error(f"❌ Email error: {str(e)}")

def render_contact_timeline(df: pd.DataFrame, contact_idx: int):
    """Individual contact interaction timeline"""
    st.subheader(f"📅 Contact Timeline")
    
    crm = CRMManager()
    activities = crm.load_activities()
    contact_key = f"contact_{contact_idx}"
    
    contact_activities = activities.get(contact_key, {})
    
    if not contact_activities:
        st.info("No activity recorded for this contact yet.")
        return
    
    # Timeline visualization
    timeline_data = []
    for activity_type, details in contact_activities.items():
        if isinstance(details, dict) and 'timestamp' in details:
            timeline_data.append({
                'date': details['timestamp'],
                'activity': activity_type,
                'details': details.get('notes', ''),
                'rep': details.get('rep', 'Unknown')
            })
    
    if timeline_data:
        timeline_df = pd.DataFrame(timeline_data)
        timeline_df['date'] = pd.to_datetime(timeline_df['date'])
        timeline_df = timeline_df.sort_values('date', ascending=False)
        
        for _, activity in timeline_df.iterrows():
            st.markdown(f"""
            **{activity['date'].strftime('%Y-%m-%d %H:%M')}** - {activity['activity']}  
            *Rep: {activity['rep']}*  
            {activity['details']}
            ---
            """)

# Add CRM navigation to main dashboard
def show_company_research(company_data, df):
    """Display company research panel"""
    company_name = company_data['Company']
    
    with st.expander(f"Research: {company_name}", expanded=True):
        # Basic company info
        st.subheader(f"Company Profile: {company_name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Phone:** {company_data['Phone']}")
            st.write(f"**Location:** {company_data['Location']}")
            st.write(f"**Current Status:** {company_data['Status']}")
        
        with col2:
            st.write(f"**Email:** {company_data.get('Email', 'Not provided')}")
            st.write(f"**Listings:** {company_data['Listings']}")
            if company_data.get('Notes'):
                st.write(f"**Notes:** {company_data['Notes']}")
        
        # Quick insights based on available data
        st.markdown("### Quick Insights")
        
        # Analyze company name for industry keywords
        company_lower = company_name.lower()
        insights = []
        
        if any(word in company_lower for word in ['cat', 'caterpillar']):
            insights.append("🏗️ Caterpillar dealer - likely high-value equipment")
        
        if any(word in company_lower for word in ['john deere', 'deere']):
            insights.append("🚜 John Deere dealer - agricultural/construction focus")
        
        if any(word in company_lower for word in ['equipment', 'machinery']):
            insights.append("🔧 Equipment dealer - primary business focus")
        
        if any(word in company_lower for word in ['rental', 'rent']):
            insights.append("📅 Rental company - may have regular equipment turnover")
        
        if 'wheeler' in company_lower:
            insights.append("🏢 Wheeler Machinery - major dealer network")
        
        # Listing volume insights
        try:
            listings = int(company_data['Listings']) if company_data['Listings'] != 'N/A' else 0
            if listings > 50:
                insights.append(f"📈 High volume dealer ({listings} listings) - excellent prospect")
            elif listings > 20:
                insights.append(f"📊 Medium volume dealer ({listings} listings) - good prospect")
            elif listings > 5:
                insights.append(f"📋 Small dealer ({listings} listings) - potential for growth")
        except:
            pass
        
        if insights:
            for insight in insights:
                st.write(f"• {insight}")
        else:
            st.write("• Standard equipment dealer profile")
        
        # AI-powered research (if OpenAI key available)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            st.markdown("### AI Research")
            
            if st.button("🤖 Get AI Insights", key=f"ai_research_{company_name}"):
                with st.spinner("Analyzing company..."):
                    try:
                        import openai
                        client = openai.OpenAI(api_key=openai_key)
                        
                        prompt = f"""
                        Analyze this equipment dealer for sales prospecting:
                        
                        Company: {company_name}
                        Location: {company_data['Location']}
                        Equipment Listings: {company_data['Listings']}
                        
                        Provide brief insights for a Heavy Haulers Equipment Logistics sales rep about:
                        1. Company size and type
                        2. Potential transportation needs
                        3. Best approach for initial contact
                        4. Key talking points
                        
                        Keep response concise (max 150 words).
                        """
                        
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=200,
                            temperature=0.7
                        )
                        
                        ai_insights = response.choices[0].message.content
                        st.write(ai_insights)
                        
                    except Exception as e:
                        st.error(f"AI research failed: {str(e)}")
        else:
            st.info("💡 Add OpenAI API key for AI-powered company research")
        
        # Call preparation checklist
        st.markdown("### Call Preparation")
        st.write("**Key talking points:**")
        st.write("• Heavy Haulers specializes in nationwide equipment transport")
        st.write("• Expand sales territory beyond local market")
        st.write("• Competitive rates for equipment dealers")
        st.write("• Professional handling of valuable machinery")
        
        # Quick actions
        st.markdown("### Quick Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📞 Mark as Called", key=f"mark_called_{company_name}"):
                st.success("Status updated - go to Call Campaign to add details")
        
        with col2:
            if st.button("📧 Add to Email List", key=f"add_email_{company_name}"):
                st.info("Add email address in Call Campaign section")

def add_crm_navigation():
    """Add CRM menu to sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 CRM Features")
    
    crm_mode = st.sidebar.radio(
        "CRM Mode:",
        ["Dashboard View", "Territory Management", "Call Campaign", "Email Marketing", "Analytics"]
    )
    
    return crm_mode

def render_fixed_research_panel():
    """Render company research inline below main content - no fixed positioning"""
    
    # Check if we have research data to display
    if 'research_panel_data' not in st.session_state:
        return
    
    company_data = st.session_state.get('research_panel_data', {})
    if not company_data:
        return
        
    company_name = company_data.get('Company', 'Unknown Company')
    
    # Simple inline display using Streamlit components
    st.markdown("---")
    st.markdown(f"### 🔍 Company Research: {company_name}")
    
    with st.expander("Company Details & Analysis", expanded=True):
        render_research_content_simple(company_data)
        
        # Simple close button
        if st.button("✅ Close Research", key="close_research_inline", type="secondary"):
            del st.session_state['research_panel_data']
            st.rerun()

def render_research_content_simple(company_data):
    """Simplified content renderer for inline display"""
    
    if not company_data:
        st.info("No company selected for research")
        return
        
    company_name = company_data.get('Company', 'Unknown')
    
    # Company Profile Header - using Streamlit components
    st.subheader(f"🏢 {company_name}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**📞 Phone:** {company_data.get('Phone', 'N/A')}")
        st.write(f"**📍 Location:** {company_data.get('Location', 'N/A')}")
        st.write(f"**📧 Email:** {company_data.get('Email', 'Not provided')}")
    
    with col2:
        st.write(f"**📦 Listings:** {company_data.get('Listings', 'N/A')}")
        st.write(f"**📊 Status:** {company_data.get('Status', 'N/A')}")
    
    st.markdown("---")
    
    # AI Insights Section
    st.subheader("🤖 AI Insights")
    
    company_lower = company_name.lower()
    insights = []
    
    # Industry analysis
    if any(word in company_lower for word in ['cat', 'caterpillar']):
        insights.append("🏗️ Caterpillar dealer - high-value equipment specialist")
    
    if any(word in company_lower for word in ['john deere', 'deere']):
        insights.append("🚜 John Deere dealer - agricultural/construction focus")
    
    if any(word in company_lower for word in ['equipment', 'machinery']):
        insights.append("🔧 Primary equipment dealer")
    
    if any(word in company_lower for word in ['rental', 'rent']):
        insights.append("📅 Rental company - regular equipment turnover")
    
    if 'wheeler' in company_lower:
        insights.append("🏢 Wheeler Machinery - major dealer network")
    
    # Volume analysis
    try:
        listings = int(company_data.get('Listings', 0)) if company_data.get('Listings', 'N/A') != 'N/A' else 0
        if listings > 50:
            insights.append(f"📈 High volume ({listings} listings) - excellent prospect")
        elif listings > 20:
            insights.append(f"📊 Medium volume ({listings} listings) - good prospect")
        elif listings > 5:
            insights.append(f"📋 Small dealer ({listings} listings) - growth potential")
    except:
        insights.append("📋 Listing data available for analysis")
    
    if not insights:
        insights.append("🔍 Standard equipment dealer profile")
    
    # Display insights as info boxes
    for insight in insights:
        st.info(insight)
    
    st.markdown("---")
    
    # Call Preparation Section
    st.subheader("📞 Call Preparation")
    
    st.markdown("""
    **Key Talking Points:**
    • Heavy Haulers specializes in nationwide equipment transport  
    • Expand sales territory beyond local market  
    • Competitive rates for equipment dealers  
    • Professional handling of valuable machinery  
    
    **Questions to Ask:**  
    • What's your current shipping solution?  
    • Do you have out-of-state buyers?  
    • What's your typical equipment value range?  
    """)
    
    st.markdown("---")
    
    # Quick Actions Section
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown("#### ⚡ Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📞 Mark Called", key="panel_mark_called_simple"):
            st.success("✅ Marked as called!")
            # Close panel after action
            st.session_state.research_panel_open = False
            st.rerun()
    
    with col2:
        if st.button("� Add Email", key="panel_add_email_simple"):
            st.info("📧 Added to email list!")
    
    # Notes section
    notes_input = st.text_area(
        "📝 Quick Notes:",
        height=80,
        placeholder="Add notes about this company...",
        key=f"simple_notes_{company_name}"
    )
    
    if st.button("💾 Save Notes", key="panel_save_notes_simple"):
        if notes_input.strip():
            st.success("Notes saved!")
        else:
            st.warning("Please enter some notes first.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Final close button
    if st.button("✕ Close Research Panel", key="final_close_button", type="primary"):
        st.session_state.research_panel_open = False
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
