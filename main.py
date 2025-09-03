import os
import re
import time
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, send_file
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['MAX_FILE_AGE'] = 3600  # Tempo máximo de vida dos arquivos em segundos (1 hora)

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def cleanup_old_files():
    """Remove arquivos temporários mais antigos que MAX_FILE_AGE segundos"""
    now = time.time()
    cleanup_count = 0
    
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Pular se não for um arquivo
        if not os.path.isfile(filepath):
            continue
            
        # Se o arquivo for mais antigo que MAX_FILE_AGE, removê-lo
        file_age = now - os.path.getmtime(filepath)
        if file_age > app.config['MAX_FILE_AGE']:
            try:
                os.remove(filepath)
                cleanup_count += 1
            except (OSError, IOError) as e:
                app.logger.error(f"Erro ao remover arquivo {filepath}: {e}")
    
    if cleanup_count > 0:
        app.logger.info(f"Removidos {cleanup_count} arquivos temporários antigos")

def sanitize_cpf(cpf):
    """Remove caracteres não numéricos e adiciona zeros à esquerda se necessário"""
    if pd.isna(cpf):
        return None
    cpf = re.sub(r'\D', '', str(cpf))
    return cpf.zfill(11)

def identify_columns(df):
    """Identifica automaticamente as colunas do DataFrame"""
    columns_map = {}
    
    # Procurar por colunas com CPF (username)
    for col in df.columns:
        sample = df[col].astype(str).iloc[0:10]
        if any(re.search(r'\d{3}[.-]?\d{3}[.-]?\d{3}[-]?\d{2}', str(x)) for x in sample):
            columns_map['username'] = col
            break
    
    # Procurar por colunas com email
    email_pattern = r'[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}'
    for col in df.columns:
        sample = df[col].astype(str).iloc[0:10]
        if any(re.search(email_pattern, str(x).strip()) for x in sample):
            columns_map['email'] = col
            break
    
    # Procurar por nome e sobrenome
    name_cols = [col for col in df.columns if any(word in col.lower() for word in ['nome', 'name'])]
    if len(name_cols) >= 2:
        columns_map['firstname'] = name_cols[0]
        columns_map['lastname'] = name_cols[1]
    elif len(name_cols) == 1:
        # Se houver apenas uma coluna de nome, dividir em primeiro nome e sobrenome
        columns_map['fullname'] = name_cols[0]
    
    # Procurar por cursos
    course_cols = [col for col in df.columns if any(word in col.lower() for word in ['curso', 'disciplina', 'course'])]
    for i, col in enumerate(course_cols, 1):
        columns_map[f'course{i}'] = col
    
    # Procurar por grupos
    group_cols = [col for col in df.columns if any(word in col.lower() for word in ['grupo', 'group'])]
    for i, col in enumerate(group_cols, 1):
        columns_map[f'group{i}'] = col
    
    # Procurar por senha
    password_cols = [col for col in df.columns if any(word in col.lower() for word in ['senha', 'password'])]
    if password_cols:
        columns_map['password'] = password_cols[0]
    
    return columns_map

def validate_email(email):
    """Valida um endereço de e-mail usando uma expressão regular"""
    if pd.isna(email):
        return False
    email = str(email).strip()  # Remove espaços em branco extras
    if not email:  # Se estiver vazio após strip
        return False
    # Padrão mais flexível para emails
    pattern = r'[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}'
    return bool(re.search(pattern, email))

def process_dataframe(df, columns_map, default_course=None, default_password=None):
    """Processa o DataFrame e retorna um novo DataFrame no formato Moodle"""
    output_df = pd.DataFrame()
    invalid_emails = set()
    duplicate_users = {}
    
    # Lista para manter a ordem das colunas
    column_order = []
    
    # Processar username (CPF)
    if 'username' in columns_map:
        output_df['username'] = df[columns_map['username']].apply(sanitize_cpf)
        column_order.append('username')
        
        # Identificar usernames duplicados
        duplicates = df[df[columns_map['username']].duplicated(keep=False)]
        if not duplicates.empty:
            for idx in duplicates.index:
                username = sanitize_cpf(df.at[idx, columns_map['username']])
                if username not in duplicate_users:
                    duplicate_users[username] = []
                
                record = {'username': username}
                
                # Adicionar outros campos disponíveis
                if 'firstname' in columns_map:
                    record['firstname'] = df.at[idx, columns_map['firstname']]
                elif 'fullname' in columns_map:
                    record['firstname'] = df.at[idx, columns_map['fullname']].split()[0]
                
                if 'lastname' in columns_map:
                    record['lastname'] = df.at[idx, columns_map['lastname']]
                elif 'fullname' in columns_map:
                    record['lastname'] = ' '.join(df.at[idx, columns_map['fullname']].split()[1:])
                
                if 'email' in columns_map:
                    record['email'] = df.at[idx, columns_map['email']]
                
                for i in range(1, 10):  # Verificar até course9
                    course_key = f'course{i}'
                    if course_key in columns_map:
                        record[course_key] = df.at[idx, columns_map[course_key]]
                    elif i == 1 and default_course:
                        record[course_key] = default_course
                
                duplicate_users[username].append(record)
    
    # Processar senha (logo após username)
    if 'password' in columns_map:
        output_df['password'] = df[columns_map['password']]
    elif default_password:
        output_df['password'] = default_password
    if 'password' in output_df:
        column_order.append('password')
    
    # Processar nome e sobrenome
    if 'fullname' in columns_map:
        # Dividir nome completo em primeiro nome e sobrenome
        names = df[columns_map['fullname']].str.split(expand=True)
        output_df['firstname'] = names[0]
        output_df['lastname'] = names.iloc[:, 1:].fillna('').apply(lambda x: ' '.join(x[x != '']), axis=1)
    else:
        if 'firstname' in columns_map:
            output_df['firstname'] = df[columns_map['firstname']]
        if 'lastname' in columns_map:
            output_df['lastname'] = df[columns_map['lastname']]
    
    if 'firstname' in output_df:
        column_order.append('firstname')
    if 'lastname' in output_df:
        column_order.append('lastname')
    
    # Processar email
    if 'email' in columns_map:
        # Limpar e processar emails
        output_df['email'] = df[columns_map['email']].astype(str).apply(lambda x: x.strip())
        # Validar emails
        invalid_emails.update(
            email for email in output_df['email']
            if not validate_email(email) and not pd.isna(email)
        )
    if 'email' in output_df:
        column_order.append('email')
    
    # Processar cursos e grupos alternadamente
    course_cols = sorted([k for k in columns_map.keys() if k.startswith('course')])
    group_cols = sorted([k for k in columns_map.keys() if k.startswith('group')])
    
    # Adicionar curso padrão se necessário
    if not course_cols and default_course:
        course_cols = ['course1']
        output_df['course1'] = default_course
    
    # Combinar cursos e grupos
    max_courses = len(course_cols)
    for i in range(max_courses):
        course_col = course_cols[i]
        if course_col in columns_map:
            output_df[course_col] = df[columns_map[course_col]]
        elif course_col == 'course1' and default_course:
            output_df[course_col] = default_course
        if course_col in output_df:
            column_order.append(course_col)
            
        # Adicionar o grupo correspondente logo após o curso, se existir
        group_col = f'group{i+1}'
        if group_col in columns_map:
            output_df[group_col] = df[columns_map[group_col]]
            if group_col in output_df:
                column_order.append(group_col)
    
    # Remover duplicatas apenas por username
    if 'username' in output_df.columns:
        output_df = output_df.drop_duplicates(subset=['username'])
    
    # Reordenar as colunas conforme foram adicionadas
    output_df = output_df[column_order]
    
    return output_df, list(invalid_emails), duplicate_users

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'ods'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Importador CSV para Moodle</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; }
        input[type="file"] { margin-bottom: 10px; }
        input[type="text"], input[type="password"] { padding: 5px; width: 300px; }
        button { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #45a049; }
        .error-message { color: red; margin-top: 20px; }
        .warning-message { color: #ff8c00; margin-top: 20px; }
        .password-group { margin-top: 10px; }
        .password-group.hidden { display: none; }
        .checkbox-label { display: inline-block; }
        .duplicate-table { 
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .duplicate-table th, .duplicate-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .duplicate-table th {
            background-color: #f2f2f2;
        }
        .duplicate-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    </style>
    <script>
        function togglePasswordField() {
            var checkbox = document.getElementById('use_default_password');
            var passwordGroup = document.getElementById('password_group');
            var passwordInput = document.getElementById('default_password');
            
            passwordGroup.className = checkbox.checked ? 'password-group' : 'password-group hidden';
            passwordInput.required = checkbox.checked;
            if (!checkbox.checked) {
                passwordInput.value = '';
            }
        }
    </script>
</head>
<body>
    <h1>Importador CSV para Moodle</h1>
    {% if invalid_emails %}
    <div class="error-message">
        <h3>⚠️ Atenção: Os seguintes endereços de e-mail são inválidos:</h3>
        <ul>
        {% for email in invalid_emails %}
            <li>{{ email }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
    {% if duplicate_users %}
    <div class="warning-message">
        <h3>⚠️ Atenção: Foram encontrados os seguintes CPFs (usernames) duplicados:</h3>
        {% for username, records in duplicate_users.items() %}
        <h4>CPF: {{ username }}</h4>
        <table class="duplicate-table">
            <tr>
                <th>Nome</th>
                <th>Sobrenome</th>
                <th>E-mail</th>
                <th>Curso</th>
            </tr>
            {% for record in records %}
            <tr>
                <td>{{ record.firstname }}</td>
                <td>{{ record.lastname }}</td>
                <td>{{ record.email }}</td>
                <td>{{ record.course1 }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endfor %}
    </div>
    {% endif %}
    <form method="post" enctype="multipart/form-data">
        <div class="form-group">
            <label for="file">Selecione o arquivo (xlsx, xls, csv, ods):</label>
            <input type="file" id="file" name="file" required>
        </div>
        <div class="form-group">
            <label for="default_course">Curso padrão (opcional):</label>
            <input type="text" id="default_course" name="default_course">
        </div>
        <div class="form-group">
            <label class="checkbox-label">
                <input type="checkbox" id="use_default_password" name="use_default_password" onchange="togglePasswordField()">
                Usar senha padrão
            </label>
            <div id="password_group" class="password-group hidden">
                <label for="default_password">Senha padrão:</label>
                <input type="text" id="default_password" name="default_password" value="trocar@1234">
            </div>
        </div>
        <button type="submit">Enviar</button>
    </form>
</body>
</html>
'''

from flask import render_template_string as render_template

@app.route("/", methods=['GET', 'POST'])
def home():
    # Limpar arquivos antigos antes de cada operação
    cleanup_old_files()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'Nenhum arquivo enviado', 400
        
        file = request.files['file']
        if file.filename == '':
            return 'Nenhum arquivo selecionado', 400
        
        if not allowed_file(file.filename):
            return 'Tipo de arquivo não permitido', 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        default_course = request.form.get('default_course')
        use_default_password = 'use_default_password' in request.form
        default_password = request.form.get('default_password') if use_default_password else None
        
        # Determinar o tipo de arquivo e ler apropriadamente
        if filename.endswith('.csv'):
            dfs = [pd.read_csv(filepath, encoding='utf-8', sep=None, engine='python')]
        elif filename.endswith('.ods'):
            dfs = pd.read_excel(filepath, engine='odf', sheet_name=None).values()
        else:  # xlsx ou xls
            dfs = pd.read_excel(filepath, sheet_name=None).values()
        
        # Processar cada planilha
        output_files = []
        all_invalid_emails = set()
        all_duplicate_users = {}
        
        for i, df in enumerate(dfs):
            columns_map = identify_columns(df)
            processed_df, invalid_emails, duplicate_users = process_dataframe(df, columns_map, default_course, default_password)
            all_invalid_emails.update(invalid_emails)
            all_duplicate_users.update(duplicate_users)
            
            # Salvar arquivo CSV processado
            output_filename = f'processado_{os.path.splitext(filename)[0]}_{i+1}.csv'
            output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            processed_df.to_csv(output_filepath, sep=';', index=False, encoding='utf-8')
            output_files.append(output_filepath)
        
        # Se houver e-mails inválidos ou duplicatas, mostrar na interface
        if all_invalid_emails or all_duplicate_users:
            return render_template(HTML_TEMPLATE, 
                                invalid_emails=sorted(all_invalid_emails) if all_invalid_emails else None,
                                duplicate_users=all_duplicate_users if all_duplicate_users else None)
        
        # Se houver apenas um arquivo, retornar ele diretamente
        if len(output_files) == 1:
            response = send_file(output_files[0], as_attachment=True)
            # Forçar limpeza imediata após o download
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(output_files[0])
                except (OSError, IOError):
                    pass
            return response
        
        # Se houver múltiplos arquivos, criar um arquivo zip
        import zipfile
        zip_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'arquivos_processados.zip')
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in output_files:
                zipf.write(file, os.path.basename(file))
        
        response = send_file(zip_filename, as_attachment=True)
        # Forçar limpeza imediata após o download
        @response.call_on_close
        def cleanup():
            try:
                # Remover arquivo ZIP
                os.remove(zip_filename)
                # Remover arquivos CSV individuais
                for file in output_files:
                    os.remove(file)
            except (OSError, IOError):
                pass
        return response
    
    return render_template(HTML_TEMPLATE, invalid_emails=None, duplicate_users=None)

if __name__ == "__main__":
    app.run(debug=True)
