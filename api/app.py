from flask import Flask, request, jsonify, send_file, render_template
import pytesseract
from PIL import Image
import os
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='../templates')  # Point to templates folder outside api/
UPLOAD_FOLDER = '/tmp/uploads'  # Use /tmp for serverless (ephemeral storage)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Ensure upload folder exists (temporary in serverless)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ocr_scan(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return str(e)

def save_as_txt(text, filename):
    txt_path = os.path.join(UPLOAD_FOLDER, f"{filename}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return txt_path

def save_as_docx(text, filename):
    docx_path = os.path.join(UPLOAD_FOLDER, f"{filename}.docx")
    doc = Document()
    doc.add_paragraph(text)
    doc.save(docx_path)
    return docx_path

def save_as_pdf(text, filename):
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{filename}.pdf")
    pdf = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(text, styles["Normal"])]
    pdf.build(story)
    return pdf_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', error='No file part')
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error='No selected file')
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            extracted_text = ocr_scan(file_path)
            if not extracted_text:
                return render_template('index.html', error='Failed to extract text')
            
            return render_template('index.html', text=extracted_text, filename=filename)
    
    return render_template('index.html')

@app.route('/convert/<filename>/<format_type>')
def convert_file(filename, format_type):
    text = request.args.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    base_filename = os.path.splitext(filename)[0]
    
    if format_type == 'txt':
        output_path = save_as_txt(text, base_filename)
    elif format_type == 'docx':
        output_path = save_as_docx(text, base_filename)
    elif format_type == 'pdf':
        output_path = save_as_pdf(text, base_filename)
    else:
        return jsonify({'error': 'Unsupported format'}), 400
    
    return send_file(output_path, as_attachment=True)

# Vercel requires this for serverless deployment
if __name__ == '__main__':
    app.run()