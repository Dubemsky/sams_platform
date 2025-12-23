from flask import Flask, render_template, request, send_file
import json
import os
from datetime import datetime
import fitz 
import zipfile
import io
import sys    
import subprocess

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Form configurations
FORM_CONFIGS = {
    "ex15_alzira": {
        "template": os.path.join(BASE_DIR, "Autofill and manual documents", "{Birth names} {Last name} - EX15 ALZIRA.pdf"),
        "fields_json": os.path.join(BASE_DIR, "form_configs", "fields_ex15_alzira.json"),
        "output_name": "EX15_Alzira_{last_name}.pdf"
    },
    "ex15_valencia": {
        "template": os.path.join(BASE_DIR, "Autofill and manual documents", "{Birth names} {Last name} - EX15 VALENCIA.pdf"),
        "fields_json": os.path.join(BASE_DIR, "form_configs", "fields_ex15_valencia.json"),
        "output_name": "EX15_Valencia_{last_name}.pdf"
    },
    "poder_notarial": {
        "template": os.path.join(BASE_DIR, "Autofill and manual documents", "{Full name customer} - Poder Notarial.pdf"),
        "fields_json": os.path.join(BASE_DIR, "form_configs", "fields_poder_notarial.json"),
        "output_name": "Poder_Notarial_{last_name}.pdf"
    },
    "shipping_receipt": {
        "template": os.path.join(BASE_DIR, "Autofill and manual documents", "{Full name customer} - Shipping receipt.pdf"),
        "fields_json": os.path.join(BASE_DIR, "form_configs", "fields_shipping_receipt.json"),
        "output_name": "Shipping_Receipt_{last_name}.pdf"
    },
    "consent_agreement": {
        "template": os.path.join(BASE_DIR, "Autofill and manual documents", "{name of customer} - customer consent agreement.pdf"),
        "fields_json": os.path.join(BASE_DIR, "form_configs", "fields_consent_agreement.json"),
        "output_name": "Consent_Agreement_{last_name}.pdf"
    }
}


@app.route("/")
def index():
    return render_template("nie-eu-standard.html")


def remove_placeholders_from_pdf(pdf_path, replacements):
    """Remove placeholder text from PDF"""
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        for placeholder in replacements.keys():
            text_instances = page.search_for(placeholder)
            for inst in text_instances:
                page.add_redact_annot(inst, "")
        page.apply_redactions()
    
    temp_pdf_path = pdf_path.replace(".pdf", "_cleaned.pdf")
    doc.save(temp_pdf_path)
    doc.close()
    
    return temp_pdf_path


def fill_single_pdf(form_id, form_data):
    """Fill a single PDF form with user data"""
    config = FORM_CONFIGS[form_id]
    
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
    
    # Get today's date
    today = datetime.now()
    date_today = today.strftime("%d/%m/%Y")
    
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
    
    # Section 4 fields (for EX-15 forms)
    doc_type = form_data.get("doc_type", "").upper()
    doc_nie = "☑" if doc_type == "NIE" else ""
    doc_cert = "☑" if doc_type == "CERT" else ""
    
    cert_type = form_data.get("cert_type", "").upper()
    cert_residente = "☑" if cert_type == "RESIDENTE" else ""
    cert_no_residente = "☑" if cert_type == "NO_RESIDENTE" else ""
    
    motivo_economico = "☑" if form_data.get("motivo_economico") == "on" else ""
    motivo_profesional = "☑" if form_data.get("motivo_profesional") == "on" else ""
    motivo_social = "☑" if form_data.get("motivo_social") == "on" else ""
    
    lugar = form_data.get("lugar", "").upper()
    lugar_extranjeria = "☑" if lugar == "EXTRANJERIA" else ""
    lugar_policia = "☑" if lugar == "POLICIA" else ""
    lugar_consular = "☑" if lugar == "CONSULAR" else ""
    
    situacion = form_data.get("situacion", "").upper()
    situacion_estancia = "☑" if situacion == "ESTANCIA" else ""
    situacion_residencia = "☑" if situacion == "RESIDENCIA" else ""
    
    # Full name combinations
    full_name = f"{form_data.get('birth_names', '')} {form_data.get('last_name', '')}"
    street_and_number = f"{form_data.get('street', '')} {form_data.get('street_number', '')}"
    
    # Comprehensive field values mapping
    field_values = {
        # Basic info
        "{passport_number}": form_data.get("passport_number", ""),
        "{last_name}": form_data.get("last_name", ""),
        "{birth_names}": form_data.get("birth_names", ""),
        "{full_name}": full_name.strip(),
        "{Full name and surname}": full_name.strip(),
        "{full name and surname}": full_name.strip(),
        
        # Date fields
        "{sex_h}": sex_h,
        "{sex_m}": sex_m,
        "{dob_day}": dob_day,
        "{dob_month}": dob_month,
        "{dob_year}": dob_year,
        "{Date of birth}": dob,
        "{date of today}": date_today,
        "{dob}": dob,
        "{date_today}": date_today,

        
        # Place of birth
        "{birth_city}": form_data.get("birth_city", ""),
        "{City of birth}": form_data.get("birth_city", ""),
        "{birth_country}": form_data.get("birth_country", ""),
        "{Country of birth}": form_data.get("birth_country", ""),
        "{nationality}": form_data.get("nationality", ""),
        "{Nationality}": form_data.get("nationality", ""),
        
        # Marital status
        "{civil_s}": civil_s,
        "{civil_c}": civil_c,
        "{civil_v}": civil_v,
        "{civil_d}": civil_d,
        "{civil_sp}": civil_sp,
        
        # Parents
        "{father_name}": form_data.get("father_name", ""),
        "{mother_name}": form_data.get("mother_name", ""),
        
        # Address
        "{street}": form_data.get("street", ""),
        "{Street}": form_data.get("street", ""),
        "{street_number}": form_data.get("street_number", ""),
        "{street_and_number}": street_and_number.strip(),
        "{Street and number}": street_and_number.strip(),
        "{town}": form_data.get("town", ""),
        "{city}": form_data.get("town", ""),
        "{City}": form_data.get("town", ""),
        "{postcode}": form_data.get("postcode", ""),
        "{postalcode}": form_data.get("postcode", ""),
        "{province}": form_data.get("province", ""),
        "{Province}": form_data.get("province", ""),
        "{country}": form_data.get("birth_country", ""),
        
        # Contact
        "{phone}": form_data.get("phone", ""),
        "{email}": form_data.get("email", ""),
        
        # Section 4 (EX-15 specific)
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
    
    # Placeholders to remove from template
    placeholders_to_remove = {
        "{Passport number}": "",
        "{Last name}": "",
        "{Birth Names}": "",
        "{Birth names}": "",
        "{City of birth}": "",
        "{Country of birth}": "",
        "{Nationality}": "",
        "{First Name Father}": "",
        "{First Name Mother}": "",
        "{Street}": "",
        "{NR}": "",
        "{City / town}": "",
        "{Postal code}": "",
        "{Province}": "",
        "{Phone number}": "",
        "{Email}": "",
        "{Autofill}": "",
        "dd": "",
        "mm": "",
        "jjjj": "",
        "{passportnumber}": "",
        "{full name and surname}": "",
        "{Street and number}": "",
        "{postalcode}": "",
        "{City}": "",
        "{country}": "",
        "{Date of birth}": "",
        "{date of today}": "",
        "{Signature}": "",
        "{Full customer name}": "",
        "{Name of customer}": ""
    }
    
    # Remove placeholders from template
    temp_cleaned_pdf = remove_placeholders_from_pdf(config["template"], placeholders_to_remove)
    
    # Load fields JSON
    with open(config["fields_json"], 'r') as f:
        fields_data = json.load(f)
    
    # Update field values
    for field in fields_data['form_fields']:
        placeholder = field['entry_text']['text']
        if placeholder in field_values:
            field['entry_text']['text'] = field_values[placeholder]
    
    # Create temp fields file
    temp_fields = os.path.join(BASE_DIR, f"temp_fields_{form_id}.json")
    with open(temp_fields, 'w') as f:
        json.dump(fields_data, f, indent=2)
    
    # Generate output filename
    output_name = config["output_name"].format(last_name=form_data.get("last_name", "user"))
    output_path = os.path.join(BASE_DIR, "pdfs_output", output_name)
    
   
    venv_python = sys.executable
    
    result = subprocess.run([
        venv_python,
        'fill_pdf.py',
        temp_cleaned_pdf,
        temp_fields,
        output_path
    ], capture_output=True, text=True)
    
    # Clean up temp files
    if os.path.exists(temp_fields):
        os.remove(temp_fields)
    if os.path.exists(temp_cleaned_pdf):
        os.remove(temp_cleaned_pdf)
    
    if result.returncode != 0:
        raise Exception(f"Error filling {form_id}: {result.stderr}")
    
    return output_path


@app.route("/generate-pdfs", methods=["POST"])
def generate_pdfs():
    form_data = request.form

    # Instead of reading selected_forms, just use all FORM_CONFIGS
    selected_forms = list(FORM_CONFIGS.keys())

    # Ensure output directory exists
    os.makedirs(os.path.join(BASE_DIR, "pdfs_output"), exist_ok=True)

    # Generate each PDF
    generated_pdfs = []
    for form_id in selected_forms:
        try:
            pdf_path = fill_single_pdf(form_id, form_data)
            generated_pdfs.append(pdf_path)
        except Exception as e:
            return f"Error generating {form_id}: {str(e)}", 500

    # If only one PDF, send it directly
    if len(generated_pdfs) == 1:
        return send_file(generated_pdfs[0], as_attachment=True)

    # If multiple PDFs, create a ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for pdf_path in generated_pdfs:
            zip_file.write(pdf_path, os.path.basename(pdf_path))

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'documents_{form_data.get("last_name", "user")}.zip'
    )



if __name__ == "__main__":
    os.makedirs("pdfs_output", exist_ok=True)
    os.makedirs("form_configs", exist_ok=True)
    app.run(debug=True)