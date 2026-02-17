from flask import Flask, render_template_string, request, abort
import os
import re
import csv

app = Flask(__name__)

# =============================================
# ВРЕМЕННО ОТКЛЮЧИЛИ БОЛЬШОЙ ФАЙЛ ДЛЯ ДЕПЛОЯ
# =============================================
VERTICAL_FILE = 'full_vertical_max.txt'   # файл не загружен на GitHub
documents = []                            # ← пустой корпус, чтобы не падало

# =============================================
# Метаданные из CSV
# =============================================
metadata_dict = {}
if os.path.exists('metadata.csv'):
    with open('metadata.csv', 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            filename = row.get('filename', '').strip()
            if filename:
                metadata_dict[filename] = {
                    'text_type': row.get('text_type', 'Не указано').strip(),
                    'level': row.get('level', 'Не указано').strip(),
                    'gender': row.get('gender', 'Не указано').strip(),
                    'publish_period': row.get('publish_period', 'Не указано').strip(),
                    'collect_date': row.get('collect_date', 'Не указано').strip(),
                    'word_count': row.get('word_count', 'Не указано').strip(),
                    'title': row.get('title', 'Не указано').strip()
                }

POS_KAZ = {
    'NOUN': 'Зат есім', 'VERB': 'Етістік', 'ADJ': 'Сын есім', 'ADV': 'Үстеу',
    'PRON': 'Есімдік', 'PROPN': 'Атаулы зат есім', 'NUM': 'Сан есім',
    'DET': 'Анықтауыш', 'ADP': 'Септік жалғауы', 'CONJ': 'Жалғаулық',
    'PART': 'Шылау', 'INTJ': 'Одағай', 'PUNCT': 'Тыныс белгісі',
    'X': 'Басқа', '?': 'Белгісіз'
}

HTML_INDEX = """ 
<!doctype html>
<html lang="kk">
<head>
  <meta charset="utf-8">
  <title>Қазақ корпусы</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <style>
    body { background: #f8f9f9; }
    .header { background: #2c3e50; color: white; padding: 40px 0; text-align: center; }
    .header h1 { margin: 0; font-size: 36px; }
    .search-bar { max-width: 800px; margin: 30px auto; }
    .result-item { background: white; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 30px; padding: 20px; }
    .sentence { font-size: 18px; line-height: 1.8; margin-bottom: 15px; padding: 10px; background: #fff; border-radius: 6px; }
    .sentence mark { background: #ffeb3b; padding: 2px 5px; border-radius: 3px; }
    .meta { background: #e9ecef; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; }
    .doc-link { font-weight: bold; color: #007bff; text-decoration: none; }
    .doc-link:hover { text-decoration: underline; }
    .no-results { text-align: center; color: #6c757d; font-size: 18px; margin: 50px 0; }
    .mini-table { font-size: 14px; }
    .mini-table th, .mini-table td { padding: 8px 10px; vertical-align: middle; }
    .highlight-row { background-color: #fff3cd !important; font-weight: 600; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Қазақ корпусы</h1>
  </div>

  <div class="search-bar">
    <form method="GET" class="d-flex">
      <input type="text" name="query" class="form-control me-2" placeholder="Сөз немесе түбірлер (мыс: дегеннен арба)" value="{{ request.args.get('query', '') }}">
      <button type="submit" class="btn btn-primary">Іздеу</button>
    </form>
  </div>

  <div class="container">
    <h2 class="my-4">Нәтижелер</h2>
    {% if results %}
      {% for result in results %}
        <div class="result-item">
          <div class="doc-name mb-2">
            Мәтін: <a class="doc-link" href="/doc/{{ result.filename }}?query={{ request.args.get('query', '') }}">{{ result.filename }}</a>
          </div>
          <div class="meta">
            <b>Түр:</b> {{ result.text_type }} | 
            <b>Деңгей:</b> {{ result.level }} | 
            <b>Жынысы:</b> {{ result.gender }} | 
            <b>Кезең:</b> {{ result.publish_period }} | 
            <b>Жинақ күні:</b> {{ result.collect_date }} | 
            <b>Сөз саны:</b> {{ result.word_count }}
          </div>
          
          <div class="sentence mb-3">
            {{ result.sentence | safe }}
          </div>
          
          <h6 class="mb-2">Талдау (табылған сөз(дер) үшін):</h6>
          <div class="table-responsive">
            <table class="table table-bordered table-sm mini-table">
              <thead class="table-light">
                <tr>
                  <th>№</th>
                  <th>Сөз</th>
                  <th>Түбірі</th>
                  <th>UPOS</th>
                  <th>Толық морфология</th>
                  <th>Рөлі</th>
                </tr>
              </thead>
              <tbody>
                {% for row in result.table_rows %}
                <tr class="highlight-row">
                  <td>{{ row.id }}</td>
                  <td>{{ row.word }}</td>
                  <td>{{ row.lemma }}</td>
                  <td>{{ row.upos }}</td>
                  <td>{{ row.feats_kaz | safe }}</td>
                  <td>{{ row.deprel_kaz }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      {% endfor %}
    {% else %}
      <p class="no-results">Нәтиже жоқ. Басқа сөздер енгізіп көріңіз.</p>
    {% endif %}
  </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    query = request.args.get('query', '').strip()
    results = []

    if query:
        query_words = [w.strip().lower() for w in re.split(r'\s+', query) if w.strip()]

        for doc in documents:   # пока documents пустой — результатов не будет
            filename = doc['attrs'].get('filename', '—')
            meta = metadata_dict.get(filename, {})

            for sent in doc['sentences']:
                # ... (пока пусто)

    return render_template_string(HTML_INDEX, results=results, request=request, POS_KAZ=POS_KAZ)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def translate_feats(feats, lemma=''):
    if feats == '—':
        return '— (қосымша белгілер көрсетілмеген)'
    # ... (твоя функция без изменений)
    return '<br>• ' + '<br>• '.join(kaz) if kaz else feats

def translate_deprel(deprel):
    mapping = { ... }  # твоя функция без изменений
    return mapping.get(deprel, deprel or '—')

@app.route('/doc/<filename>')
def show_doc(filename):
    # Пока документов нет — просто 404
    abort(404, f"Документ '{filename}' табылмады.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)   # порт 9000, как ты уже менял
