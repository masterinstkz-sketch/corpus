from flask import Flask, render_template_string, request, abort
import os
import re
import csv

app = Flask(__name__)

VERTICAL_FILE = 'full_vertical_max.txt'
documents = []
current_doc = None
current_sent = None

with open(VERTICAL_FILE, 'r', encoding='utf-8') as f:
    for line in f:
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

# Метаданные из CSV
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
    'NOUN': 'Зат есім',
    'VERB': 'Етістік',
    'ADJ': 'Сын есім',
    'ADV': 'Үстеу',
    'PRON': 'Есімдік',
    'PROPN': 'Атаулы зат есім',
    'NUM': 'Сан есім',
    'DET': 'Анықтауыш',
    'ADP': 'Септік жалғауы',
    'CONJ': 'Жалғаулық',
    'PART': 'Шылау',
    'INTJ': 'Одағай',
    'PUNCT': 'Тыныс белгісі',
    'X': 'Басқа',
    '?': 'Белгісіз'
}

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
                sentence_words_lower = [w['word'].lower() for w in sent]

                all_present = True
                for qw in query_words:
                    found = False
                    for lemma, word in zip(sentence_lemmas_lower, sentence_words_lower):
                        if len(qw) <= 4:
                            # Короткие — точное совпадение
                            if qw == lemma or qw == word:
                                found = True
                                break
                        else:
                            # Длинные — подстрока
                            if qw in lemma or qw in word:
                                found = True
                                break
                    if not found:
                        all_present = False
                        break

                if all_present:
                    highlighted_sent = sentence_text
                    for ww in sent:
                        word_lower = ww['word'].lower()
                        lemma_lower = ww['lemma'].lower()
                        if any((len(qw) <= 4 and (qw == lemma_lower or qw == word_lower)) or (len(qw) > 4 and (qw in lemma_lower or qw in word_lower)) for qw in query_words):
                            highlighted_sent = re.sub(
                                r'\b' + re.escape(ww['word']) + r'\b',
                                f'<mark>{ww['word']}</mark>',
                                highlighted_sent,
                                flags=re.IGNORECASE
                            )

                    table_rows = []
                    for token_idx, ww in enumerate(sent, 1):
                        word_lower = ww['word'].lower()
                        lemma_lower = ww['lemma'].lower()
                        if any((len(qw) <= 4 and (qw == lemma_lower or qw == word_lower)) or (len(qw) > 4 and (qw in lemma_lower or qw in word_lower)) for qw in query_words):
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
            if val == 'Hab': kaz.append('Әдеттегі іс-әрекет')
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
