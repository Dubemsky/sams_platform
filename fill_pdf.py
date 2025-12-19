import json
import sys
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText

def transform_coordinates(bbox, image_width, image_height, pdf_width, pdf_height):
    """
    Convert image coordinates (top-left origin)
    to PDF coordinates (bottom-left origin)
    """
    x_scale = pdf_width / image_width
    y_scale = pdf_height / image_height

    left = bbox[0] * x_scale
    right = bbox[2] * x_scale
    top = pdf_height - (bbox[1] * y_scale)
    bottom = pdf_height - (bbox[3] * y_scale)

    return left, bottom, right, top

def fill_pdf_form(input_pdf_path, fields_json_path, output_pdf_path):
    with open(fields_json_path, "r") as f:
        fields_data = json.load(f)

    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    writer.append(reader)

    # Cache PDF page sizes
    pdf_dimensions = {i + 1: (page.mediabox.width, page.mediabox.height) for i, page in enumerate(reader.pages)}

    for field in fields_data["form_fields"]:
        page_num = field["page_number"]
        page_info = next(p for p in fields_data["pages"] if p["page_number"] == page_num)
        pdf_width, pdf_height = pdf_dimensions[page_num]

        left, bottom, right, top = transform_coordinates(
            field["entry_bounding_box"],
            page_info["image_width"],
            page_info["image_height"],
            pdf_width,
            pdf_height,
        )

        if "entry_text" not in field:
            continue
        text = field["entry_text"].get("text", "").strip()
        if not text:
            continue

        font_name = field["entry_text"].get("font", "Helvetica")
        font_color = field["entry_text"].get("font_color", "000000")
        font_size = field["entry_text"].get("font_size", 11)

        # Smaller font for long fields
        if field["description"].lower() in ["full name and surname", "street and number"]:
            font_size = 10

        # -----------------------------
        # NEW: Automatically shrink font to fit box
        # -----------------------------
        box_width = right - left - 2  # subtract minimal padding
        if len(text) * font_size * 0.5 > box_width:  # rough estimate
            font_size = max(int(box_width / (len(text) * 0.5)), 6)

        # Padding inside the box
        padding_x = 1
        padding_y = 1

        rect = (
            left + padding_x,
            bottom + padding_y,
            right - padding_x,
            top - padding_y,
        )

        annotation = FreeText(
            text=text,
            rect=rect,
            font=font_name,
            font_size=f"{font_size}pt",
            font_color=font_color,
            border_color=None,
            background_color=None,
        )

        writer.add_annotation(page_number=page_num - 1, annotation=annotation)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)

    print(f"PDF generated: {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python fill_pdf.py <input.pdf> <fields.json> <output.pdf>")
        sys.exit(1)

    fill_pdf_form(sys.argv[1], sys.argv[2], sys.argv[3])
