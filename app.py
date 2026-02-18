from flask import Flask, render_template_string, request, abort
import os
import re
import csv
import requests

app = Flask(__name__)

# =============================================
# Скачивание корпуса из Google Drive
# =============================================
documents = []
current_doc = None
current_sent = None

url = "https://drive.google.com/uc?export=download&id=1balDNY-B63tlG5pN6L5y0TfgpNTR7BtX"

try:
    response = requests.get(url, timeout=300)  # 5 минут таймаут
    response.raise_for_status()
    text = response.text
    lines = text.splitlines()
except Exception as e:
    print(f"Ошибка скачивания корпуса: {e}")
    lines = []

# Парсинг из lines (твой оригинальный код)
for line in lines:
    line = line.strip()
    if line.startswith('<doc '):
        if current_doc:
            documents.append(current_doc)
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', line))
        current_doc = {'attrs': attrs, 'sentences': []}
    elif line.startswith('<s>'):
        current_sent = []
    elif line == '</s>':
        if current_doc and current_sent is not None:
            current_doc['sentences'].append(current_sent)
            current_sent = None
    elif line == '</doc>':
        if current_doc:
            documents.append(current_doc)
            current_doc = None
    elif '\t' in line and current_sent is not None:
        parts = line.split('\t')
        if len(parts) >= 6:
            word = parts[0]
            lemma = parts[1] if len(parts) > 1 else '—'
            pos = parts[2] if len(parts) > 2 else '—'
            feats = parts[3] if len(parts) > 3 and parts[3] != '—' else '—'
            head = parts[4] if len(parts) > 4 and parts[4] != '—' else '—'
            deprel = parts[5] if len(parts) > 5 and parts[5] != '—' else '—'
            current_sent.append({'word': word, 'lemma': lemma, 'pos': pos, 'feats': feats, 'head': head, 'deprel': deprel})

if current_doc:
    documents.append(current_doc)

print(f"Загружено документов: {len(documents)}")  # для логов Render

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

        if not query_words:
            return render_template_string(HTML_INDEX, results=[], request=request, POS_KAZ=POS_KAZ)

        for doc in documents:
            filename = doc['attrs'].get('filename', '—')
            meta = metadata_dict.get(filename, {})

            for sent in doc['sentences']:
                sentence_words = [w['word'] for w in sent]
                sentence_text = ' '.join(sentence_words)
                sentence_lemmas_lower = [w['lemma'].lower() for w in sent]

                # Проверяем наличие всех слов из запроса
                all_present = True
                for qw in query_words:
                    found = False
                    for lemma in sentence_lemmas_lower:
                        if qw == lemma:
                            found = True
                            break
                    if not found:
                        all_present = False
                        break

                if all_present:
                    # Подсветка
                    highlighted_sent = sentence_text
                    for ww in sent:
                        if ww['lemma'].lower() in query_words:
                            highlighted_sent = re.sub(
                                r'\b' + re.escape(ww['word']) + r'\b',
                                f'<mark>{ww['word']}</mark>',
                                highlighted_sent,
                                flags=re.IGNORECASE
                            )

                    # Таблица только для найденных слов
                    table_rows = []
                    for token_idx, ww in enumerate(sent, 1):
                        if ww['lemma'].lower() in query_words:
                            feats_kaz = translate_feats(ww['feats'], ww['lemma'])
                            deprel_kaz = translate_deprel(ww['deprel'])

                            table_rows.append({
                                'id': token_idx,
                                'word': ww['word'],
                                'lemma': ww['lemma'],
                                'upos': ww['pos'],
                                'feats_kaz': feats_kaz,
                                'deprel_kaz': deprel_kaz
                            })

                    if table_rows:
                        results.append({
                            'filename': filename,
                            'text_type': meta.get('text_type', 'Не указано'),
                            'level': meta.get('level', 'Не указано'),
                            'gender': meta.get('gender', 'Не указано'),
                            'publish_period': meta.get('publish_period', 'Не указано'),
                            'collect_date': meta.get('collect_date', 'Не указано'),
                            'word_count': meta.get('word_count', 'Не указано'),
                            'sentence': highlighted_sent,
                            'table_rows': table_rows
                        })

    return render_template_string(HTML_INDEX, results=results, request=request, POS_KAZ=POS_KAZ)

def translate_feats(feats, lemma=''):
    if feats == '—':
        return '— (қосымша белгілер көрсетілмеген)'
    
    kaz = []
    for p in feats.split('|'):
        if '=' not in p:
            kaz.append(p)
            continue
        key, val = p.split('=', 1)
        if key == 'Case':
            if val == 'Nom': kaz.append('Атау септік')
            elif val == 'Acc': kaz.append('Ілік септік')
            elif val == 'Dat': kaz.append('Барыс септік')
            elif val == 'Gen': kaz.append('Ілік септік')
            elif val == 'Loc': kaz.append('Жатыс септік')
            elif val == 'Abl': kaz.append('Шығыс септік')
            elif val == 'Ins': kaz.append('Құралдық септік')
        elif key == 'Number':
            if val == 'Plur': kaz.append('Көпше')
            elif val == 'Sing': kaz.append('Жекеше')
        elif key == 'Person':
            if val == '1': kaz.append('1-жақ')
            elif val == '2': kaz.append('2-жақ')
            elif val == '3': kaz.append('3-жақ')
        elif key == 'Person[psor]':
            if val == '1': kaz.append('1-жақ иесі')
            elif val == '2': kaz.append('2-жақ иесі')
            elif val == '3': kaz.append('3-жақ иесі')
        elif key == 'Number[psor]':
            if val == 'Plur,Sing': kaz.append('Иесінің саны: жекеше немесе көпше')
            elif val == 'Sing': kaz.append('Иесінің саны: жекеше')
            elif val == 'Plur': kaz.append('Иесінің саны: көпше')
        elif key == 'Mood':
            if val == 'Ind': kaz.append('Хабарлы рай')
            elif val == 'Imp': kaz.append('Бұйрық рай')
            elif val == 'Opt': kaz.append('Қалау рай')
        elif key == 'Tense':
            if val == 'Past': kaz.append('Өткен шақ')
            elif val == 'Pres': kaz.append('Осы шақ')
            elif val == 'Fut': kaz.append('Келер шақ')
        elif key == 'Aspect':
            if val == 'Hab': kaz.append('Әдеттегі іс-әрекет (habitual)')
        elif key == 'VerbForm':
            if val == 'Part': kaz.append('Есімше')
            elif val == 'Ger': kaz.append('Көсемше')
            elif val == 'Fin': kaz.append('Жіктік форма')
            elif val == 'Inf': kaz.append('Тұйық етістік')
        elif key == 'Voice':
            if val == 'Caus': kaz.append('Мәжбүр етіс')
            elif val == 'Pass': kaz.append('Ырықсыз етіс')
        elif key == 'vbType':
            if val == 'Adj': kaz.append('Есімше/Деепричастие')
        else:
            kaz.append(f"{key} = {val}")
    
    return '<br>• ' + '<br>• '.join(kaz) if kaz else feats

def translate_deprel(deprel):
    mapping = {
        'obj': 'Тікелей толықтауыш',
        'nsubj': 'Бастауыш',
        'advmod': 'Үстеулік толықтауыш',
        'nmod:poss': 'Иелік септіктегі толықтауыш',
        'root': 'Басты мүше',
        'acl': 'Анықтауыштық бағыныңқы',
        'acl:relcl': 'Қатыстық бағыныңқы сөйлем',
        'case': 'Септік жалғауы',
        'advcl': 'Үстеулік бағыныңқы сөйлем',
        'parataxis': 'Қатарлас сөйлем',
        'ccomp': 'Бағыныңқы сөйлем',
        'det': 'Анықтауыш',
        'amod': 'Сындық анықтауыш',
        'conj': 'Жалғаулық байланыс',
        'cc': 'Жалғаулық'
    }
    return mapping.get(deprel, deprel or '—')

@app.route('/doc/<filename>')
def show_doc(filename):
    abort(404, f"Документ '{filename}' табылмады.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
