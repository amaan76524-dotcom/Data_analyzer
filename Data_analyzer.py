import streamlit as st
from PyPDF2 import PdfReader
import sqlite3
import re
import os

DB_NAME = 'customers.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            order_no TEXT,
            order_date TEXT,
           
            product_description TEXT,
            price TEXT
        );
    ''')
    conn.commit()
    conn.close()

def extract_fields(text):
    # Extract Name
    name_match = re.search(r'Customer Address\s*\n([^\n]+)', text)
    name = name_match.group(1).strip() if name_match else ''

    # Extract Address block
    address_block = ''
    address_start = re.search(r'Customer Address\s*\n[^\n]+\n', text)
    if address_start:
        rest = text[address_start.end():]
        address_lines = []
        for line in rest.split('\n'):
            if 'If undelivered' in line:
                break
            address_lines.append(line.strip())
        address_block = ', '.join(address_lines)

    # Pincode
    pincode_match = re.search(r'(\d{6})', address_block)
    pincode = pincode_match.group(1) if pincode_match else ''

    # City & State
    city_state_match = re.search(r'([A-Za-z ]+), ([A-Za-z ]+), ' + pincode, address_block) if pincode else None
    if city_state_match:
        city = city_state_match.group(1).strip()
        state = city_state_match.group(2).strip()
    else:
        parts = address_block.split(',')
        city = parts[-3].strip() if len(parts) > 2 else ''
        state = parts[-2].strip() if len(parts) > 1 else ''

    # Order number
    order_match = re.search(r'Order No\.\s*([0-9A-Za-z_]+)', text)
    order_no = order_match.group(1) if order_match else ''

    # Order date
    date_match = re.search(r'Order Date\s*([0-9.]+)', text)
    order_date = date_match.group(1) if date_match else ''
    
    # Product description and price
    prod_desc = ""
    price = ""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Product Description
        if line.strip().lower().startswith("description") and i+1 < len(lines):
            prod_desc = lines[i+1].strip()
        # Price: look for Gross Amount or Total Amount
        if ("gross amount" in line.lower() or "total amount" in line.lower()) and price == "":
            j = i
            while j+1 < len(lines):
                j += 1
                next_line = lines[j].strip()
                if next_line and any(c.isdigit() for c in next_line):
                    price = next_line
                    break

    return {
        'name': name,
        'address': address_block,
        'city': city,
        'state': state,
        'pincode': pincode,
        'order_no': order_no,
        'order_date': order_date,
       
        'product_description': prod_desc,
        'price': price
    }

def insert_customer(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO customers (
        name, address, city, state, pincode, order_no, order_date, phone, product_description, price
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', (
        data['name'], data['address'], data['city'], data['state'],
        data['pincode'], data['order_no'], data['order_date'], 
        data['product_description'], data['price']
    ))
    conn.commit()
    conn.close()

def get_all_customers():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT name, address, city, state, pincode,
                        order_no, order_date, phone, product_description, price FROM customers
                 ORDER BY id DESC;''')
    rows = c.fetchall()
    conn.close()
    return rows

def main():
    st.set_page_config(page_title='Meesho Customer App', layout='wide')
    st.title('Meesho Customer Data Uploader')

    init_db()

    st.markdown('Upload a customer label PDF downloaded from Meesho (one at a time).')

    uploaded_file = st.file_uploader('Choose PDF', type='pdf')

    if uploaded_file is not None:
        reader = PdfReader(uploaded_file)
        full_text = ''
        for page in reader.pages:
            full_text += page.extract_text() + '\n'

        st.subheader('Extracted PDF Text')
        st.text_area('PDF Content', full_text, height=200)

        customer_data = extract_fields(full_text)

        st.subheader('Extracted Customer Data')
        st.write(customer_data)

        if st.button('Save Customer Data'):
            insert_customer(customer_data)
            st.success('Customer data saved to database!')

    st.write('---')
    st.subheader('Saved Customers')
    customers = get_all_customers()
    if customers:
        st.table([{
            'Name': x[0], 'Address': x[1], 'City': x[2], 'State': x[3], 'Pincode': x[4],
            'Order No': x[5], 'Order Date': x[6], 
            'Product Description': x[8], 'Price': x[9]
        } for x in customers])
    else:
        st.info('No customer data saved yet.')

if __name__ == '__main__':
    main()



