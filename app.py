from flask import Flask, render_template, request, send_file
import json
import os
from datetime import datetime
import fitz  # PyMuPDF

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PDF_TEMPLATE = os.path.join(
    BASE_DIR,
    "Autofill and manual documents",
    "{Birth names} {Last name} - EX15 ALZIRA.pdf"
)

OUTPUT_PDF = os.path.join(
    BASE_DIR,
    "pdfs_output",
    "filled_EX15.pdf"
)

FIELDS_JSON = os.path.join(BASE_DIR, "fields.json")


@app.route("/")
def index():
    return render_template("nie-eu-standard.html")


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    form_data = request.form
    
    # Parse date of birth
    dob = form_data.get("dob", "")
    dob_day = ""
    dob_month = ""
    dob_year = ""
    if dob:
        try:
            date_obj = datetime.strptime(dob, "%Y-%m-%d")
            dob_day = date_obj.strftime("%d")
            dob_month = date_obj.strftime("%m")
            dob_year = date_obj.strftime("%Y")
        except ValueError:
            pass
    
    # Get sex checkboxes
    sex = form_data.get("sex", "").upper()
    sex_h = "X" if sex == "H" or sex == "MALE" else ""
    sex_m = "X" if sex == "M" or sex == "F" or sex == "FEMALE" else ""
    
    # Get marital status
    marital_status = form_data.get("marital_status", "").upper()
    civil_s = "X" if marital_status == "S" or marital_status == "SINGLE" else ""
    civil_c = "X" if marital_status == "C" or marital_status == "MARRIED" else ""
    civil_v = "X" if marital_status == "V" or marital_status == "WIDOWED" else ""
    civil_d = "X" if marital_status == "D" or marital_status == "DIVORCED" else ""
    civil_sp = "X" if marital_status == "SP" or marital_status == "SEPARATED" else ""
    
    # Section 4.1 - Document type
    doc_type = form_data.get("doc_type", "").upper()
    doc_nie = "☑" if doc_type == "NIE" else ""
    doc_cert = "☑" if doc_type == "CERT" else ""
    
    cert_type = form_data.get("cert_type", "").upper()
    cert_residente = "☑" if cert_type == "RESIDENTE" else ""
    cert_no_residente = "☑" if cert_type == "NO_RESIDENTE" else ""
    
    # Section 4.2 - Motivos
    motivo_economico = "☑" if form_data.get("motivo_economico") == "on" else ""
    motivo_profesional = "☑" if form_data.get("motivo_profesional") == "on" else ""
    motivo_social = "☑" if form_data.get("motivo_social") == "on" else ""
    
    # Section 4.3 - Lugar de presentación
    lugar = form_data.get("lugar", "").upper()
    lugar_extranjeria = "☑" if lugar == "EXTRANJERIA" else ""
    lugar_policia = "☑" if lugar == "POLICIA" else ""
    lugar_consular = "☑" if lugar == "CONSULAR" else ""
    
    # Section 4.4 - Situación en España
    situacion = form_data.get("situacion", "").upper()
    situacion_estancia = "☑" if situacion == "ESTANCIA" else ""
    situacion_residencia = "☑" if situacion == "RESIDENCIA" else ""
    
    # Full name for page 2
    full_name = f"{form_data.get('birth_names', '')} {form_data.get('last_name', '')}"
    
    # Map placeholders to actual user values (for removal from template)
    replacements = {
        "{Passport number}": form_data.get("passport_number", ""),
        "{passport_number}": form_data.get("passport_number", ""),
        "{Last name}": form_data.get("last_name", ""),
        "{last_name}": form_data.get("last_name", ""),
        "{Birth Names}": form_data.get("birth_names", ""),
        "{Birth names}": form_data.get("birth_names", ""),
        "{birth_names}": form_data.get("birth_names", ""),
        "{City of birth}": form_data.get("birth_city", ""),
        "{birth_city}": form_data.get("birth_city", ""),
        "{Country of birth}": form_data.get("birth_country", ""),
        "{birth_country}": form_data.get("birth_country", ""),
        "{Nationality}": form_data.get("nationality", ""),
        "{nationality}": form_data.get("nationality", ""),
        "{First Name Father}": form_data.get("father_name", ""),
        "{father_name}": form_data.get("father_name", ""),
        "{First Name Mother}": form_data.get("mother_name", ""),
        "{mother_name}": form_data.get("mother_name", ""),
        "{Street}": form_data.get("street", ""),
        "{street}": form_data.get("street", ""),
        "{NR}": form_data.get("street_number", ""),
        "{street_number}": form_data.get("street_number", ""),
        "{City / town}": form_data.get("town", ""),
        "{town}": form_data.get("town", ""),
        "{Postal code}": form_data.get("postcode", ""),
        "{postcode}": form_data.get("postcode", ""),
        "{Province}": form_data.get("province", ""),
        "{province}": form_data.get("province", ""),
        "{Phone number}": form_data.get("phone", ""),
        "{phone}": form_data.get("phone", ""),
        "{Email}": form_data.get("email", ""),
        "{email}": form_data.get("email", ""),
        "dd": "",  # Remove date placeholders
        "mm": "",
        "jjjj": "",
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
    
    # Open the PDF
    doc = fitz.open(PDF_TEMPLATE)
    
    # First pass: Remove all placeholders from the PDF
    for page_num in range(len(doc)):
        page = doc[page_num]
        for placeholder in replacements.keys():
            # Find all instances of this placeholder
            text_instances = page.search_for(placeholder)
            for inst in text_instances:
                # Remove the placeholder by redacting it with empty string
                page.add_redact_annot(inst, "")
        # Apply all redactions on this page
        page.apply_redactions()
    
    # Save the intermediate PDF (with placeholders removed)
    temp_pdf_path = os.path.join(BASE_DIR, "temp_cleaned.pdf")
    doc.save(temp_pdf_path)
    doc.close()
    
    # Now add the user data using the annotation method
    field_values = {
        "{passport_number}": form_data.get("passport_number", ""),
        "{last_name}": form_data.get("last_name", ""),
        "{birth_names}": form_data.get("birth_names", ""),
        "{sex_h}": sex_h,
        "{sex_m}": sex_m,
        "{dob_day}": dob_day,
        "{dob_month}": dob_month,
        "{dob_year}": dob_year,
        "{birth_city}": form_data.get("birth_city", ""),
        "{birth_country}": form_data.get("birth_country", ""),
        "{nationality}": form_data.get("nationality", ""),
        "{civil_s}": civil_s,
        "{civil_c}": civil_c,
        "{civil_v}": civil_v,
        "{civil_d}": civil_d,
        "{civil_sp}": civil_sp,
        "{father_name}": form_data.get("father_name", ""),
        "{mother_name}": form_data.get("mother_name", ""),
        "{street}": form_data.get("street", ""),
        "{street_number}": form_data.get("street_number", ""),
        "{town}": form_data.get("town", ""),
        "{postcode}": form_data.get("postcode", ""),
        "{province}": form_data.get("province", ""),
        "{phone}": form_data.get("phone", ""),
        "{email}": form_data.get("email", ""),
        "{full_name}": full_name.strip(),
        # Section 4 fields
        "{doc_nie}": doc_nie,
        "{doc_cert}": doc_cert,
        "{cert_residente}": cert_residente,
        "{cert_no_residente}": cert_no_residente,
        "{motivo_economico}": motivo_economico,
        "{motivo_profesional}": motivo_profesional,
        "{motivo_social}": motivo_social,
        "{lugar_extranjeria}": lugar_extranjeria,
        "{lugar_policia}": lugar_policia,
        "{lugar_consular}": lugar_consular,
        "{situacion_estancia}": situacion_estancia,
        "{situacion_residencia}": situacion_residencia
    }
    
    # Load fields.json
    with open(FIELDS_JSON, 'r') as f:
        fields_data = json.load(f)
    
    # Update the entry_text values with actual form data
    for field in fields_data['form_fields']:
        placeholder = field['entry_text']['text']
        if placeholder in field_values:
            field['entry_text']['text'] = field_values[placeholder]
    
    # Create a temporary fields file with actual values
    temp_fields = os.path.join(BASE_DIR, "temp_fields.json")
    with open(temp_fields, 'w') as f:
        json.dump(fields_data, f, indent=2)
    
    # Call the PDF filling script on the cleaned PDF
    import sys
    import subprocess

    venv_python = sys.executable

    result = subprocess.run([
        venv_python,
        'fill_pdf.py',
        temp_pdf_path,  # Use the cleaned PDF, not the original
        temp_fields,
        OUTPUT_PDF
    ], capture_output=True, text=True)

    # Clean up temp files
    if os.path.exists(temp_fields):
        os.remove(temp_fields)
    if os.path.exists(temp_pdf_path):
        os.remove(temp_pdf_path)
    
    if result.returncode != 0:
        return f"Error filling PDF: {result.stderr}", 500
    
    return send_file(OUTPUT_PDF, as_attachment=True)


if __name__ == "__main__":
    os.makedirs("pdfs_output", exist_ok=True)
    app.run(debug=True)