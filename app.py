import os
import json
import logging
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from datetime import datetime

ALLOWED_EXTENSIONS = {'json'}
UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Função para carregar a chave de criptografia
def load_key():
    try:
        key = open("secret.key", "rb").read()
        logging.debug("Chave carregada com sucesso.")
        return key
    except FileNotFoundError:
        logging.error("O arquivo secret.key não foi encontrado.")
        flash('O arquivo secret.key não foi encontrado. Por favor, crie a chave de criptografia primeiro.')
        return None

# Função para descriptografar os registros do arquivo JSON
def decrypt_records(filepath, password):
    key = load_key()
    if key is None:
        logging.debug("Chave de criptografia não encontrada.")
        return None
    
    cipher = Fernet(key)
    
    try:
        with open(filepath, 'rb') as file:
            encrypted_data = file.read()
            logging.debug("Dados criptografados lidos com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo criptografado: {e}")
        flash('Erro ao ler o arquivo criptografado.')
        return None
    
    try:
        decrypted_data = cipher.decrypt(encrypted_data)
        logging.debug("Dados descriptografados com sucesso.")
        records = json.loads(decrypted_data.decode())
        logging.debug("Dados JSON carregados com sucesso.")
        return records
    except Exception as e:
        logging.error(f"Erro ao descriptografar ou carregar JSON: {e}")
        flash(f'Falha ao descriptografar o arquivo: {e}')
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_hours(start, end):
    fmt = '%d/%m/%Y %H:%M:%S'
    tdelta = datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
    return tdelta.total_seconds() / 3600

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado')
            return redirect(request.url)
        file = request.files['file']
        password = request.form.get('password')

        if file.filename == '':
            flash('Nenhum arquivo selecionado')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            if password != 'keystar1320':
                flash('Senha incorreta')
                return redirect(request.url)

            records = decrypt_records(filepath, password)
            if records is None:
                logging.debug("Descriptografia falhou, retornando erro.")
                return redirect(request.url)

            total_hours = 0
            for record in records:
                if 'saida' in record:
                    record['hours'] = calculate_hours(record['entrada'], record['saida'])
                    total_hours += record['hours']
                else:
                    record['hours'] = 0
            
            total_payment = total_hours * 7.78

            return render_template('index.html', records=records, total_hours=total_hours, total_payment=total_payment)
    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
