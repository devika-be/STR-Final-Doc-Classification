import os
import tempfile
import pandas as pd
import streamlit as st
from pdf2image import convert_from_path
from PIL import Image
import re
from fuzzywuzzy import process
import pytesseract
import concurrent.futures
from streamlit_lottie import st_lottie  # Lottie import
import base64

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Define document types and their associated keywords
document_keywords = {
    "E-Stamp": ["Certificate No", "Certificate Issue Date", "Unique Document Reference", "Purchased By", "Property Description", "First Party", "Second Party"],
    "Agreement to Flat (Kararnama)": ["Dated", "Between", "AND", "Certificate No", "Flat No", "Sale Agreement", "Sale Deed", "Agreement Date", "Kararnama"],
    "Commencement Certificate": ["Application No", "Dated", "Plot No", "Situated at", "Building Commencement", "Commencement Certificate"],
    "CIDCO Certificate": ["CIDCO No", "Date", "Tenement Number", "Tenement Transfer Order", "Challan No", "House No", "Name"],
    "Sale Deed": ["Dated", "Between", "AND", "Certificate No", "File No", "Day Book No", "Schedule C", "Schedule D", "Sale Deed No", "Sale Deed Date"],
    "Agreement to Sale": ["Dated", "Certificate No", "File No", "Day Book No", "Schedule C", "Schedule D", "Sale Deed No", "Sale Deed Date", "BETWEEN", "SPECIFICATIONS", "VENDOR", "PURCHASER"]
}

# Function to convert PDF to images
def pdf_to_images(pdf_path, dpi=300):
    images = convert_from_path(pdf_path, dpi=dpi)
    return images

# OCR function to extract text from images
def ocr_image(image):
    return pytesseract.image_to_string(image)

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    images = pdf_to_images(pdf_path)
    extracted_text = ""
    for image in images:
        page_text = ocr_image(image)
        extracted_text += page_text + "\n\n"
    return extracted_text.strip()

# Function to classify document based on text content
def classify_document(text, document_keywords, min_keyword_matches=2):
    text_lower = text.lower()
    doc_matches = {}
    for doc_type, keywords in document_keywords.items():
        match_count = sum(1 for keyword in keywords if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower))
        if match_count >= min_keyword_matches:
            doc_matches[doc_type] = match_count
    return max(doc_matches, key=doc_matches.get) if doc_matches else "Unknown"
# Function to extract keywords based on document type
# Function to extract keywords based on document type
def extract_keywords_based_on_document(text, document_type):
    """Extract key values from the document based on its classified type."""
    keyword_patterns = {}

    # Define keyword patterns based on the document type
    if document_type == "E-Stamp":
        keyword_patterns = {
            "Certificate No.": r"certificate\s*no\.?\s*[:\-]?\s*([^\n]+)",
            "Certificate Issued Date": r"certificate\s*issued\s*date\s*[:\-]?\s*([^\n]+)",
            "Unique Doc Reference": r"unique\s*document\s*reference\s*[:\-]?\s*([^\n]+)",
            "Purchased By": r"purchased\s*by\s*[:\-]?\s*([^\n]+)",
            "Property Description": r"property\s*description\s*[:\-]?\s*([^\n]+)",
            "First Party": r"first\s*party\s*[:\-]?\s*([^\n]+)",
            "Second Party": r"second\s*party\s*[:\-]?\s*([^\n]+)",
        }
    elif document_type == "Agreement to Flat (Kararnama)":
        keyword_patterns = {
            "SELLER": r"seller[:\s]*([^\n]+)",
            "BUYER": r"buyer[:\s]*([^\n]+)",
            "Flat No": r"flat no[:\s]*([^\n]+)",
            "Address": r"address[:\s]*([^\n]+)",
            "Area": r"area[:\s]*([^\n]+)",
            "North": r"description\s*of\s*property[\s\S]?north:[:\s]([^\n]+)",
            "South": r"description\s*of\s*property[\s\S]?south:[:\s]([^\n]+)",
            "East": r"description\s*of\s*property[\s\S]?east:[:\s]([^\n]+)",
            "West": r"description\s*of\s*property[\s\S]?west:[:\s]([^\n]+)"

        }
    elif document_type == "CIDCO Certificate":
        keyword_patterns = {
            "Mr./Mrs.": r"(?:mr\.|mrs\.)\s*[:\-]?\s*([^\n]+)",
            "CIDCO No": r"cidco\s*no\s*[:\-]?\s*([^\n]+)",
            "Date": r"date\s*[:\-]?\s*([^\n]+)",
            "Shri/Smt.": r"(?:shri|smt)\.\s*[:\-]?\s*([^\n]+)",
            "House No": r"house\s*no\s*[:\-]?\s*([^\n]+)",
            "Letter No.": r"letter\s*no\.\s*[:\-]?\s*([^\n]+)",
            "Challan No.": r"challan\s*no\s*[:\-]?\s*([^\n]+)"
        }
    elif document_type in ["Sale Deed", "Agreement to Sale"]:
        keyword_patterns = {
            "Dated": r"dated[\.:,-]?\s*([^\n,]+)",
            "Between": r"between[\.:,-]?\s*([^\n,]+)\s*and",
            "AND": r"and[\.:,-]?\s*([^\n,]+)",
            "Certificate No": r"certificate\s*no[\.:,-]?\s*([^\n,]+)",
            "File No": r"file\s*no[\.:,-]?\s*([^\n,]+)",
            "Day Book No": r"day\s*book\s*no[\.:,-]?\s*([^\n,]+)",
            "Schedule C": r"schedule\s*c[\.:,-]?\s*([^\n,]+)",
            "Schedule D": r"schedule\s*d[\.:,-]?\s*([^\n,]+)",
            "Sale Deed No": r"sale\s*deed\s*no[\.:,-]?\s*([^\n,]+)",
            "Sale Deed Date": r"sale\s*deed\s*date[\.:,-]?\s*([^\n,]+)"
        }
    elif document_type == "Commencement Certificate":
        keyword_patterns = {
            "Application No.": r"application\s*no[\.:,-]?\s*([^\n,]+)",
            "Dated": r"dated[\.:,-]?\s*([^\n,]+)",
            "Plot No.": r"plot\s*no[\.:,-]?\s*([^\n,]+)",
            "Situated at": r"situated\s*at[\.:,-]?\s*([^\n,]+)"
        }

    # General extraction for other document types
    extracted_data = {}
    for keyword, pattern in keyword_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        extracted_data[keyword] = matches[0].strip() if matches else "Not Found"
    
    return extracted_data

# Function to process individual PDF
def process_pdf(pdf_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_file.read())
        temp_pdf_path = temp_pdf.name

    extracted_text = extract_text_from_pdf(temp_pdf_path)
    document_type = classify_document(extracted_text, document_keywords)
    keyword_data = extract_keywords_based_on_document(extracted_text, document_type)

    os.remove(temp_pdf_path)
    return document_type, keyword_data, keyword_data.get("Property Description", "Not Found")

# Search Excel for the Property Description
def search_excel_for_property(excels, property_description):
    results = []
    for excel_file in excels:
        df = pd.read_excel(excel_file)
        matching_rows = df[df.apply(lambda row: row.astype(str).str.contains(property_description, case=False, na=False).any(), axis=1)]
        if not matching_rows.empty:
            results.append(matching_rows)
    return results

# Function to write output to a text file
def write_results_to_file(pdf_results, excel_results):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as output_file:
        for doc_type, keywords, property_desc in pdf_results:
            output_file.write(f"Document Type: {doc_type}\n")
            for key, value in keywords.items():
                output_file.write(f"{key}: {value}\n")
            output_file.write(f"Property Description: {property_desc}\n")
            output_file.write("\n\n")

        output_file.write(f"Excel Results:\n")
        for excel_result in excel_results:
            # Format the DataFrame to show in a vertical format
            for index, row in excel_result.iterrows():
                for col_name, value in row.items():
                    output_file.write(f"{col_name}: {value}\n")
                output_file.write("\n")  # Newline after each row for spacing

    return output_file.name

# Function to load image and convert it to base64 (not needed for URLs, but kept for future reference)
def get_base64_image(image_url):
    return image_url  # Directly return the URL for now

# GitHub raw image URLs
main_background_image = "https://raw.githubusercontent.com/Prarth2002/Final-STR-DOC.github.io/main/background%20img.png"
sidebar_image_url = "https://raw.githubusercontent.com/Prarth2002/Final-STR-DOC.github.io/main/logo.png"

# Streamlit Interface
# Sidebar Styling
st.markdown(f"""
    <style>
        .sidebar .sidebar-content {{
            background-image: url('{sidebar_image_url}'); /* Sidebar background */
            background-size: cover; /* Cover the entire area */
            color: white;          /* White text */
        }}
        .sidebar .sidebar-content h1 {{
            color: white;
        }}
        .sidebar .sidebar-content h2 {{
            color: white;
        }}
        .sidebar .sidebar-content h3 {{
            color: white;
        }}
        /* Full-screen background image for the main content area */
        .main {{
            background-image: url('{main_background_image}'); /* Main background */
            background-size: cover; /* Cover the entire area */
            background-position: center; /* Center the image */
            background-repeat: no-repeat; /* Prevent image tiling */
            background-attachment: fixed; /* Keep the image fixed */
            min-height: 100vh; /* Ensure it covers the full viewport height */
            color: black; /* Text color */
        }}
    </style>
""", unsafe_allow_html=True)

# Create a 2-column layout
col1, col2 = st.columns([3, 1])

# The main content goes into the first column
with col1:
    st.sidebar.title("Smart Search Title Report Generator!")
    
    # Add the "Generate STR" text
    st.markdown("<h2 style='font-weight: bold;'>Generate STR</h2>", unsafe_allow_html=True)

    uploaded_pdfs = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    uploaded_excels = st.file_uploader("Upload Excel Files", type=["xlsx"], accept_multiple_files=True)

    if st.button("Process Files"):
        if uploaded_pdfs and uploaded_excels:
            pdf_results = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(process_pdf, pdf) for pdf in uploaded_pdfs]
                for future in concurrent.futures.as_completed(futures):
                    pdf_results.append(future.result())
            
            # Search property descriptions in Excel files
            excel_results = []
            for _, _, property_desc in pdf_results:
                excel_matches = search_excel_for_property(uploaded_excels, property_desc)
                excel_results.extend(excel_matches)
            
            # Display results in the interface
            st.subheader("PDF Results")
            for doc_type, keywords, property_desc in pdf_results:
                st.write(f"Document Type: {doc_type}")
                for key, value in keywords.items():
                    st.write(f"{key}: {value}")
                st.write(f"Property Description: {property_desc}")
                st.write("\n\n")
            
            st.subheader("Excel Results")
            for result in excel_results:
                st.write(result)
            
            # Write results to file and provide download link
            output_file_path = write_results_to_file(pdf_results, excel_results)
            st.download_button("Download Results", data=open(output_file_path, "rb"), file_name="str_results.txt")
        else:
            st.error("Please upload both PDF and Excel files.")

# Add a separator line for visual appeal
st.sidebar.markdown("---")

# Add vertical space using HTML
st.sidebar.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)

# Display the sidebar image at the bottom of the sidebar
st.sidebar.image(sidebar_image_url, use_column_width=True)
